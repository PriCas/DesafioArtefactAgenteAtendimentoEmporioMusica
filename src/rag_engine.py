'''
 Lê o PDF das políticas e o divide em seções temáticas (Horários, Trocas, Pagamento, Frete, etc.).
 Quando o cliente pergunta sobre políticas, ele faz uma busca por palavras-chave com pontuação nos
 trechos mais relevantes.
'''
import re
from pypdf import PdfReader
from src.config import DATA_DIR


class PolicyRetriever:
    def __init__(self):
        self.chunks = []
        self._load_and_chunk_pdf()

    def _load_and_chunk_pdf(self):
        pdf_path = DATA_DIR / "políticas_da_loja.pdf"
        if not pdf_path.exists():
            matches = list(DATA_DIR.glob("*políticas*.pdf")) + list(DATA_DIR.glob("*politicas*.pdf"))
            if matches:
                pdf_path = matches[0]
            else:
                raise FileNotFoundError("Manual de políticas em PDF não encontrado em data/")

        reader = PdfReader(str(pdf_path))
        full_text = ""
        for page in reader.pages:
            text = page.extract_text() or ""
            full_text += "\n" + text

        # Separa o documento por seções numeradas (Ex: 1. Sobre, 2. Horário, 3. Formas de Pagamento...)
        raw_sections = re.split(r"\n(?=\d+\.\s+[A-ZÁÉÍÓÚÀÂÊÔÃÕÇ])", full_text)

        for sec in raw_sections:
            clean_sec = sec.strip()
            if len(clean_sec) > 30:
                self.chunks.append(clean_sec)

    def retrieve(self, query: str, top_k: int = 2) -> str:
        """Busca os trechos do manual com maior relevância lexical para a consulta."""
        tokens = set(re.findall(r"\w+", query.lower()))
        scored_chunks = []

        for chunk in self.chunks:
            chunk_tokens = set(re.findall(r"\w+", chunk.lower()))
            overlap = len(tokens.intersection(chunk_tokens))
            scored_chunks.append((overlap, chunk))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        top_results = [chunk for score, chunk in scored_chunks[:top_k] if score > 0]

        if not top_results:
            return "Nenhuma política específica encontrada para este termo."

        return "\n\n---\n\n".join(top_results)


policy_retriever = PolicyRetriever()

"""


OBJETIVO :
-----------------------------
1. Precisão Numérica e Determinismo:
    Injetar tabelas CSV brutas no contexto do LLM costuma causar alucinações em filtros 
    de preço (ex: "violões até R$ 1000"), contagem incorreta de estoque e erros em cálculos.
    Ao carregar os CSVs em um banco relacional SQLite em memória, garantimos que qualquer
    consulta de catálogo ou pedido seja executada via SQL estrito e 100% determinístico.

2. Eficiência de Tokens e Custo:
    Em vez de enviar centenas de linhas de CSVs a cada requisição para o LLM, o agente 
    utiliza 'Function Calling' e consulta apenas os dados estritamente necessários via SQL.

3. Relacionamento de Dados Operacionais:
    Permite realizar JOINs eficientes entre clientes, pedidos, itens de pedidos e promoções,
    resolvendo regras complexas de negócio (ex: verificar status de pedido e rastreio).
"""

import sqlite3
import pandas as pd
from src.config import DATA_DIR


class DatabaseManager:
    """
    Gerenciador do banco de dados relacional em memória (SQLite).
    Responsável por ingerir, tratar e indexar os dados dos arquivos CSV da operação.
    """

    def __init__(self):
        # Inicializa o SQLite em RAM (:memory:), garantindo altíssima velocidade de leitura
        # e eliminando a necessidade de gerenciar infraestrutura de banco externo para o protótipo.
        # check_same_thread=False permite compatibilidade com interfaces multi-thread (ex: Streamlit).
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)

        # Configura o retorno das linhas como objetos acessíveis por nome de coluna (dict-like)
        self.conn.row_factory = sqlite3.Row

        # Executa o pipeline de ingestão e preparação dos dados
        self._load_csvs()

    def _load_csvs(self):
        """
        Lê os arquivos CSV fornecidos pelo desafio, aplica sanitização básica
        e cria as tabelas relacionais correspondentes no SQLite.
        """
        # Mapeamento: Nome da tabela relacional -> Nome do arquivo CSV esperado
        csv_files = {
            "categories": "categories.csv",
            "customers": "customers.csv",
            "products": "products.csv",
            "promotions": "promotions.csv",
            "orders": "orders.csv",
            "order_items": "order_items.csv",
        }

        for table_name, file_name in csv_files.items():
            file_path = DATA_DIR / file_name

            # Tratamento de resiliência: caso os arquivos tenham prefixos no download
            # (ex: 'desafio_tecnico_ai_eng - products.csv'), localiza o arquivo correspondente.
            if not file_path.exists():
                matches = list(DATA_DIR.glob(f"*{file_name}"))
                if matches:
                    file_path = matches[0]
                else:
                    raise FileNotFoundError(
                        f"[Desafio Artefact] Arquivo obrigatório '{file_name}' não encontrado em {DATA_DIR}."
                    )

            # Carga via Pandas para parsing automático de tipos e formatação
            df = pd.read_csv(file_path)

            # Tratamento de Dados: Remoção de espaços em branco acidentais nos cabeçalhos das colunas
            df.columns = df.columns.str.strip()

            # Persiste os dados na tabela SQLite em memória
            df.to_sql(table_name, self.conn, index=False, if_exists="replace")

        # Cria índices para otimizar as buscas estruturadas do agente
        self._create_indexes()

    def _create_indexes(self):
        """
        Cria índices relacionais nas colunas mais consultadas pelas ferramentas do agente.
        Atende à exigência de desempenho e boas práticas de modelagem de dados:
        - category_id: Filtros frequentes por tipo de instrumento (Violões, Guitarras, etc.);
        - status: Filtros por produtos ativos, descontinuados ou em breve;
        - customer_id: Otimização de JOINs na consulta de pedidos e rastreio.
        """
        cursor = self.conn.cursor()
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prod_cat ON products(category_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prod_status ON products(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_cust ON orders(customer_id);")
        self.conn.commit()

    def query(self, sql: str, params: tuple = ()):
        """
        Executa consultas SQL parametrizadas de forma segura contra SQL Injection
        e retorna os registros em formato de lista de dicionários Python,
        facilitando a serialização em JSON para o Function Calling do LLM.
        """
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


# Instância única (Singleton) para ser compartilhada entre as ferramentas (tools) do agente
db = DatabaseManager()