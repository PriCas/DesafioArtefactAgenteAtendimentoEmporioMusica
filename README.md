# 🎸 Empório da Música — Agente Inteligente de Atendimento ao Cliente

> Protótipo de agente conversacional de mensagens de texto desenvolvido como solução para o Desafio Técnico de **AI Engineer** da **Artefact**.

O projeto automatiza o canal de suporte da **Empório da Música**, loja fictícia de instrumentos musicais sediada em Campo Grande/MS. O agente atua de forma híbrida: resolve dúvidas sobre o catálogo operacional (preços, estoque, pedidos e promoções) consultando dados relacionais determinísticos e interpreta políticas institucionais (trocas, CDC, garantias, frete e horários) a partir do manual interno da loja.

---

## 🏗️ Arquitetura do Sistema e Fluxo de Decisão

O agente adota uma abordagem modular baseada em **Native Tool Calling (Function Calling)**, garantindo que o modelo decida deterministicamente quando consultar bases estruturadas ou textuais, sem misturar responsabilidades:

[ Usuário / Cliente ]
│
▼
[ Interface: CLI (main.py) ou Streamlit (app.py) ]
│
▼
[ Core do Agente: Gemini LLM + Memória de Sessão (agent.py) ]
│
├──► 1. Dúvidas de Catálogo/Preço/Estoque/Pedidos
│ └──► Tool: SQLite In-Memory Engine (database.py)
│ (Calcula preços, valida promoções ativas e checa estoque)
│
├──► 2. Dúvidas Institucionais/Regras/Garantia/Trocas
│ └──► Tool: Lexical/Semantic RAG (rag_engine.py)
│ (Segmentação e busca no Manual de Políticas em PDF)
│
└──► 3. Saudações ou Solicitações Fora de Escopo (Acessórios)
└──► Resposta Direta com Guardrails do System Prompt (prompts.py)

---

## 🛠️ Justificativa das Decisões Técnicas

### 1. Provedor e Modelo de LLM
* **Escolha:** **Google Gemini (`gemini-2.0-flash` / `gemini-3.8-flash`)**
* **Justificativa:**
  * **Confiabilidade no Tool Calling:** Modelos da família Flash da Google possuem suporte nativo à execução de funções com latência extremamente reduzida e baixíssima taxa de alucinação de argumentos.
  * **Custo-Benefício:** Custo irrisório de inferência (ou gratuito no tier do Google AI Studio), com ampla janela de contexto.
  * **Reproducibilidade:** Permite que os avaliadores executem o teste rapidamente sem necessidade de placas de vídeo locais (GPUs) dedicadas.

### 2. Framework e Abordagem de Agente (*Framework-less vs. LangChain*)
* **Escolha:** **SDK Oficial com Function Calling Nativo + Camadas Modulares Próprias**
* **Justificativa:**
  * Frameworks pesados como LangChain tradicional frequentemente introduzem abstrações excessivas (*leaky abstractions*), dificultam o rastreamento de erros e inflam as dependências.
  * Construir a arquitetura desacoplada em módulos (`database.py`, `rag_engine.py`, `tools.py`) demonstra domínio dos fundamentos de IA generativa: controle do ciclo de vida da mensagem, definição de contratos de ferramentas e isolamento de contexto.

### 3. Tratamento de Dados Estruturados vs. Não-Estruturados
* **Dados Tabulares (`*.csv`): SQLite em Memória (`:memory:`)**
  * *Por que não colocar os CSVs no prompt ou em RAG vetorial?* Injetar tabelas textualmente em prompts causa erros severos de agregação matemática, alucinação de valores e falhas em filtros lógicos (como `preço <= R$ 1.000` ou `estoque > 0`). O SQLite permite consultas relacionais exatas com `JOIN` entre clientes, pedidos e produtos.
* **Manual de Políticas (`políticas_da_loja.pdf`): RAG Lexical Estruturado por Seções**
  * O manual interno de 8 páginas foi segmentado por tópicos normativos (Horários, Pagamento, Devoluções, Frete). O retriever extrai apenas as cláusulas relevantes para cada pergunta, evitando ruído na janela de contexto principal do modelo.

### 4. Engenharia de Prompt e Persona
* **Persona:** Atendente acolhedor, informal mas profissional ("um amigo que entende de música"), condizente com as diretrizes do manual de atendimento via WhatsApp.
* **Guardrails Estritos:**
  * *Negative Catalog Constraint:* A loja **não comercializa acessórios** (palhetas, cordas avulsas, cabos, pedais, cases, amplificadores). Tentativas de compra são educadamente barradas com sugestão de lojas parceiras.
  * *Truthfulness / Zero-Hallucination:* O agente está expressamente proibido de confirmar estoque ou prazos sem consultar as ferramentas.

### 5. Memória de Conversa e Simulação Temporal (*Time Drift*)
* **Memória:** Buffer contínuo via sessão de chat nativa, garantindo resolução anafórica (ex.: o cliente pergunta *"Quanto custa o Takamine GD20?"* e logo após *"Vocês parcelam ele em quantas vezes?"*).
* **Data de Referência (`REFERENCE_DATE=2026-03-23`):** Para respeitar o recorte temporal dos dados de pedidos (que possuem registros entre o fim de 2025 e março de 2026), o sistema aceita uma data de referência que ancora a lógica de prazos de entrega e rastreamento.

---

## 📋 Regras de Negócio Implementadas

1. **Desconto PIX e Não-Cumulatividade:**
   * O pagamento via PIX concede **5% de desconto** sobre o preço de tabela.
   * Por política interna, **esse desconto NÃO se acumula** com itens que já possuem promoção ativa em `promotions.csv`.
2. **Promoções Expiradas:**
   * O agente valida o campo `is_active`. Se uma promoção estiver inativa (`is_active = 0`), o assistente informa com transparência que a campanha expirou e apresenta o valor original.
3. **Controle de Estoque e Status Especial:**
   * **Sem estoque (`stock_quantity = 0`):** O agente informa a indisponibilidade imediata e sugere modelos similares em estoque (ex.: *Giannini GF-3D*).
   * **Descontinuado (`status = 'discontinued'`):** Informa que o instrumento saiu de linha e sugere alternativas equivalentes (ex.: *Shelby SN-7C*).
   * **Em Breve (`status = 'coming_soon'`):** Informa que o produto é um lançamento futuro (ex.: *Kala Barítono Cedar*).
4. **Políticas CDC e Exceções Sanitárias:**
   * Compras online: prazo de arrependimento de 7 dias corridos, produto intacto e frete pago pela loja.
   * Trocas por defeito: até 30 dias pela loja.
   * **Exceção de Higiene:** Boquilhas de instrumentos de sopro são explicitamente inelegíveis para devolução.
5. **Frete para Campo Grande e Região:**
   * Campo Grande: Frete grátis para compras acima de R$ 500,00; taxa de R$ 35,00 abaixo disso (prazo de 1 a 3 dias úteis).

---

## 🚀 Como Rodar o Projeto

### Pré-requisitos
* **Python 3.10 ou superior** instalado.
* Chave de API do Google Gemini ([Google AI Studio](https://aistudio.google.com/)).

### 1. Clonar e Acessar o Repositório
```bash
git clone https://github.com/PriCas/DesafioArtefactAgenteAtendimentoEmporioMusica.git
cd DesafioArtefactAgenteAtendimentoEmporioMusica

2. Configurar o Ambiente Virtual

No Windows (PowerShell):
python -m venv venv
.\venv\Scripts\Activate.ps1

(Se houver bloqueio de script no PowerShell, use: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass)
No Linux / macOS ou Git Bash:
python -m venv venv
source venv/Scripts/activate  # ou source venv/bin/activate no Linux/Mac

3. Instalar Dependências
pip install -r requirements.txt

4. Configurar Variáveis de Ambiente
Crie um arquivo .env na raiz do projeto (ou copie a partir do .env.example):
# Chave de API do Google Gemini (Obrigatório)
GEMINI_API_KEY=sua_chave_aqui_sem_aspas

# Modelo Gemini recomendado
GEMINI_MODEL=gemini-2.0-flash

# Data de referência simulada para coerência com os pedidos do dataset
REFERENCE_DATE=2026-03-23

5. Executar a Aplicação
Opção A: Terminal Interativo (CLI com formatação rica via rich):
python main.py

Opção B: Interface Web Interativa (Streamlit):
streamlit run app.py
```

### 💬 Exemplos de Interação Documentados
O repositório inclui registros completos de conversas cobrindo cenários simples e complexos dentro do arquivo:
📁 examples/conversas_exemplo.md
Cenário 1: Consulta com filtro numérico de preço e categoria ("Quais opções de violões disponíveis custando até R$ 1.000?").
Cenário 2: Informações institucionais, endereço físico e horário de funcionamento.
Cenário 3: Consulta de preço com promoção expirada e cálculo do desconto PIX (Takamine GD20).
Cenário 4: Aplicação das regras do Código de Defesa do Consumidor para devoluções online.
Cenário 5: Barramento de perguntas fora de escopo (tentativa de compra de palhetas e encordoamentos).

### ⚖️ Limitações Conhecidas e Evolução Futura
Se houvesse mais tempo de desenvolvimento, as seguintes melhorias seriam priorizadas:
Autenticação em Duas Etapas (LGPD / Segurança): Atualmente, a consulta de pedidos aceita o order_id. Em ambiente produtivo, seria exigida validação por confirmação de CPF/telefone para mitigar vazamento de dados de outros clientes.
Busca Híbrida Avançada (BM25 + Dense Embeddings): Substituir a segmentação puramente lexical do manual por uma base vetorial leve (ex.: ChromaDB ou Qdrant) combinada com busca semântica densa (all-MiniLM-L6-v2), permitindo consultas conceituais complexas.
Transbordo para Atendente Humano: Implementação de análise de sentimento em tempo real para detectar clientes insatisfeitos e acionar uma ferramenta de handoff para atendentes humanos via webhook.
Testes Automatizados de Regressão (Eval Framework): Criação de uma suíte de testes com pytest e métricas de fidelidade (RAG Triad) para garantir que alterações no prompt não quebrem regras de negócio.

### 🤖 Uso de Assistentes de Código (Workflow)
Em consonância com as orientações do desafio, foram utilizados assistentes de IA (Gemini3.8-flash e Claude ) com o seguinte fluxo de trabalho:
Arquitetura e Scaffolding: Estruturação inicial do banco de dados em memória e geração de templates de tipagem para as ferramentas de function calling.
Engenharia de Prompt: Refinamento iterativo das instruções de sistema para reforçar os guardrails negativos de catálogo (não vender acessórios).


*Feito com rigor, Python e muito café. Desenvolvido para o Desafio Artefact.*
