"""

OBJETIVO :
-----------------------------
1. Interface de Function Calling (Tool Calling):
    O LLM (Google Gemini) não executa Python diretamente; ele inspeciona as assinaturas das 
    funções, tipos primitivos (type hints) e docstrings para montar o JSON Schema das ferramentas.
    Docstrings bem descritivas e tipos explícitos reduzem a zero o acionamento incorreto de tools.

2. Execução Determinística de Regras de Negócio:
    Delegar cálculos de descontos ou checagens de regras financeiras ao LLM costuma gerar 
    erros de arredondamento e alucinações. Por isso, as regras críticas do manual da loja:
    - Desconto de 5% à vista no PIX;
    - Regra de Não-Cumulatividade (PIX não se aplica a itens em promoção ativa);
    são calculadas diretamente em código Python, garantindo 100% de precisão contábil.

3. Separação de Responsabilidades (Routing):
    - Dados transacionais/estruturados (estoque, preços, rastreamento) -> Consultas SQL;
    - Regras institucionais (CDC, prazos de devolução, frete, horários) -> RAG de Políticas.
"""

import json
from src.database import db
from src.rag_engine import policy_retriever


def buscar_produtos_no_catalogo(
    termo_busca: str = "",
    categoria: str = "",
    preco_maximo: float = None,
    apenas_disponiveis: bool = True,
) -> str:
    """
    Consulta instrumentos musicais no catálogo operacional da Empório da Música.

    Esta ferramenta deve ser acionada sempre que o cliente perguntar por instrumentos,
    recomendações de compra, valores, disponibilidade de estoque ou categorias.
    A ferramenta calcula automaticamente o valor com desconto de promoções ativas
    e o preço à vista no PIX conforme as políticas da loja.

    Args:
        termo_busca (str): Nome, modelo ou palavra-chave do instrumento (ex: 'Yamaha', 'Folk', 'C40').
        categoria (str): Nome da categoria (ex: 'Violões', 'Guitarras', 'Ukuleles', 'Baixos').
        preco_maximo (float): Teto orçamentário para filtrar itens (ex: 1000.0 para 'até R$1000').
        apenas_disponiveis (bool): Se True, filtra apenas itens ativos e com estoque > 0.
        Se False, inclui itens esgotados, em breve ou descontinuados.

    Returns:
        str: JSON serializado contendo lista de produtos com preços originais, promocionais e estoque.
    """
    # Consulta SQL relacional unindo produtos, categorias e campanhas de promoção
    sql = """
        SELECT
            p.product_id,
            p.name,
            c.name as categoria,
            p.price_brl,
            p.stock_quantity,
            p.status,
            p.description,
            prom.discount_percent,
            prom.is_active as promo_ativa,
            prom.description as promo_desc
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.category_id
        LEFT JOIN promotions prom ON p.product_id = prom.product_id
        WHERE 1=1
    """
    params = []

    # Filtro flexível por nome ou descrição do instrumento
    if termo_busca:
        sql += " AND (p.name LIKE ? OR p.description LIKE ?)"
        params.extend([f"%{termo_busca}%", f"%{termo_busca}%"])

    # Filtro por categoria cadastrada
    if categoria:
        sql += " AND c.name LIKE ?"
        params.append(f"%{categoria}%")

    # Filtro numérico determinístico de faixa de preço (requisito explícito do desafio)
    if preco_maximo is not None:
        sql += " AND p.price_brl <= ?"
        params.append(preco_maximo)

    # Tratamento de estoque: por padrão filtra apenas instrumentos aptos para venda imediata
    if apenas_disponiveis:
        sql += " AND p.stock_quantity > 0 AND p.status = 'active'"

    # Ordenação por menor preço e paginação de segurança para não inflar a janela de contexto
    sql += " ORDER BY p.price_brl ASC LIMIT 10;"

    resultados = db.query(sql, tuple(params))

    # Resposta estruturada caso a busca não retorne itens
    if not resultados:
        return json.dumps(
            {"mensagem": "Nenhum produto encontrado com os filtros informados."},
            ensure_ascii=False,
        )

    itens = []
    for row in resultados:
        preco_original = float(row["price_brl"])
        # Verifica se o produto tem promoção associada E se ela está ativa no sistema
        desconto_promo = (
            float(row["discount_percent"]) if row["promo_ativa"] == 1 else 0.0
        )

        # APLICAÇÃO DAS REGRAS DE NEGÓCIO DA EMPÓRIO DA MÚSICA (Página 6 do Manual):
        if desconto_promo > 0:
            preco_final = round(preco_original * (1 - (desconto_promo / 100)), 2)
            # Regra: O desconto de PIX (5%) NÃO é cumulativo com preços já promocionais
            preco_pix = preco_final
            status_promo = f"Ativa: {desconto_promo}% off ({row['promo_desc']})"
        else:
            preco_final = preco_original
            # Regra: PIX recebe 5% de desconto à vista sobre o preço de tabela regular
            preco_pix = round(preco_original * 0.95, 2)
            status_promo = "Sem promoção ativa"

        itens.append(
            {
                "id": row["product_id"],
                "nome": row["name"],
                "categoria": row["categoria"],
                "preco_tabela": preco_original,
                "preco_promocional": (
                    preco_final if desconto_promo > 0 else None
                ),
                "preco_a_vista_pix": preco_pix,
                "estoque": row["stock_quantity"],
                "status_catalogo": row["status"],
                "detalhes_promocao": status_promo,
                "descricao": row["description"],
            }
        )

    # ensure_ascii=False garante que acentos em português não gastem tokens desnecessários (\u00e3...)
    return json.dumps(itens, ensure_ascii=False, indent=2)


def consultar_status_pedido(order_id: int) -> str:
    """
    Consulta os detalhes, status operacional e rastreamento de um pedido específico.

    Deve ser acionada sempre que o cliente quiser saber sobre o andamento de uma compra,
    onde está o pacote, código de rastreio dos Correios/Jadlog ou motivos de cancelamento.

    Args:
        order_id (int): Identificador numérico único do pedido (ex: 8, 12, 17).

    Returns:
        str: JSON com dados do pedido, cliente associado, previsão de entrega e itens comprados.
    """
    # Consulta relacionando a tabela de pedidos com a tabela de clientes
    sql_order = """
        SELECT
            o.order_id,
            o.order_date,
            o.status,
            o.total_brl,
            o.payment_method,
            o.tracking_code,
            o.estimated_delivery,
            o.notes,
            c.name as cliente_nome,
            c.email as cliente_email
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE o.order_id = ?
    """
    pedido = db.query(sql_order, (order_id,))

    if not pedido:
        return json.dumps(
            {"erro": f"Pedido #{order_id} não foi encontrado no sistema da Empório da Música."},
            ensure_ascii=False,
        )

    # Consulta dos itens e produtos pertencentes a este pedido específico
    sql_items = """
        SELECT
            oi.quantity,
            p.name as produto_nome,
            p.price_brl
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        WHERE oi.order_id = ?
    """
    itens = db.query(sql_items, (order_id,))

    detalhes = dict(pedido[0])
    detalhes["itens"] = itens

    return json.dumps(detalhes, ensure_ascii=False, indent=2)


def consultar_politicas_da_loja(assunto_ou_duvida: str) -> str:
    """
    Consulta a base de conhecimento institucional do Manual de Políticas e Procedimentos.

    Deve ser acionada para responder dúvidas conceituais e operacionais que não estão
    no banco de dados, tais como:
    - Política de trocas e devoluções (7 dias arrependimento CDC, 30 dias defeito);
    - Regras de garantia legal e de fabricantes;
    - Prazos, taxas de entrega e frete grátis (Campo Grande vs interior);
    - Formas e regras de parcelamento no cartão de crédito;
    - Horário de atendimento e endereço físico da loja.

    Args:
        assunto_ou_duvida (str): Termo de consulta (ex: 'prazo arrependimento troca', 'horario sabado').

    Returns:
        str: Trechos originais do manual contendo as diretrizes oficiais da loja.
    """
    # Encaminha para o motor de RAG que realiza a busca semântica/lexical no documento
    return policy_retriever.retrieve(assunto_ou_duvida)