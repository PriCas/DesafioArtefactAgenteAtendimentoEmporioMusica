# 🎸 Agente de Atendimento - Empório da Música (Desafio Artefact)

Bem-vindo ao repositório do Agente de Atendimento de Inteligência Artificial desenvolvido para a Empório da Música, como parte do desafio técnico para **AI Engineer** da Artefact.

Este projeto implementa um agente conversacional autônomo projetado para tirar dúvidas, consultar estoques, calcular prazos e interpretar políticas de loja, mantendo uma persona acolhedora e barrando perguntas fora de escopo.

---

## 🛠️ 1. Instruções de Configuração e Execução

Para facilitar a avaliação, o projeto foi desenhado para rodar nativamente em qualquer máquina com Python, sem a necessidade de levantar contêineres Docker pesados.

### Pré-requisitos
- **Python 3.10** ou superior.
- Conta no Google AI Studio (para chave do Gemini) ou OpenAI.

### Passo a Passo

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/seu_usuario/DesafioArtefactAgenteAtendimentoEmporioMusica.git
   cd emporio-musica-agent
   ```

2. **Crie e ative o ambiente virtual:**
   ```bash
   python -m venv venv
   # Linux/Mac
   source venv/bin/activate
   # Windows
   venv\Scripts\activate
   ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configuração de Variáveis de Ambiente:**
   Copie o arquivo de exemplo e insira sua chave de API:
   ```bash
   cp .env.example .env
   ```
   Edite o arquivo `.env`:
   ```env
   GEMINI_API_KEY=sua_chave_aqui
   # Variável essencial para testes temporais (Explicado na seção de EDA)
   REFERENCE_DATE=2026-03-23 
   ```

5. **Execute a Interface do Agente (CLI):**
   ```bash
   python src/main.py
   ```

6. **Execute os Cenários de Teste (Artefatos de Entrega):**
   ```bash
   python scripts/run_scenarios.py
   ```
   *(Os arquivos `.md` gerados estarão na pasta `examples/`)*

---

## 🧠 2. Justificativas das Decisões Técnicas

Como Engenheira de IA, minha prioridade é o **determinismo**, a **manutenibilidade** e a **prevenção contra alucinações**.

*   **Framework de Orquestração (Vanilla Python vs LangChain):** 
    Optei por **NÃO** utilizar LangChain. Implementei um *loop de Function Calling* nativo usando Python puro e chamadas diretas de API. 
    *Justificativa:* Frameworks adicionam camadas de abstração. Desenvolver o loop nativamente, facilita o *debugging* e melhora o tempo de inferência.
*   **LLM e Provedor:** 
    O provedor padrão escolhido é o **Google Gemini (gemini-1.5-flash)**.
    *Justificativa:* Possui uma janela de contexto massiva (permitindo *Context Stuffing* seguro de histórico) e chamadas de ferramenta extremamente rápidas. A arquitetura está desacoplada (usando `LiteLLM` ou interfaces abstratas), permitindo plugar a OpenAI (`gpt-4o-mini`) com facilidade, se desejado.
*   **Arquitetura de Recuperação (RAG) Minimalista:** 
    *Justificativa:* O manual de políticas possui apenas 8 páginas. Levantar um banco vetorial completo (Chroma/FAISS) seria um *over-engineering* que dificultaria a vida do avaliador. Optei por particionar o texto e usar um índice de recuperação em memória (*TF-IDF/BM25*) com *fallback* para a injeção via prompt, garantindo latência zero.
*   **Gestão de Regras de Negócio (Arquitetura):**
    O LLM **nunca** calcula juros, descontos (5% PIX) ou prazos de garantia.
    *Justificativa:* LLMs são péssimos calculadoras. Toda regra matemática descrita no PDF e validação de tempo (7 dias de arrependimento) foi extraída e isolada em funções determinísticas em Python (`calcular_pagamento()`, `avaliar_devolucao()`). O LLM apenas roteia as intenções para o código.
*   **Processamento de Dados (SQLite):** 
    Os arquivos `CSV` são convertidos dinamicamente no *startup* para um arquivo SQLite (`database.db`). 
    *Justificativa:* Permite junções complexas (JOINs entre pedidos e clientes) de forma transacional e exata, muito superior à busca semântica em tabelas. A coluna `specs` (JSON) foi achatada via código para buscas precisas de catálogo.

---

## 🔬 3. Diagnóstico de Dados e Resolução de Anomalias (EDA)

Durante a fase de planejamento, rodei uma Análise Exploratória de Dados (EDA) que guiou as regras do agente:
1. **Time Drift:** Os pedidos no dataset param em `22/03/2026`. Se rodássemos o teste em tempo real, todas as políticas de devolução (7/30 dias) falhariam por estarem expiradas. Criei a variável `REFERENCE_DATE="2026-03-23"` para o Agente simular a data de testes com precisão histórica.
2. **Divergência de Totais:** Encontrei divergências financeiras (pedidos #3 e #20 possuem totais diferentes da soma de seus itens). Instruí a *Tool* SQL a sempre confiar apenas no `total_brl` oficial para evitar conflitos fiscais com o cliente.
3. **Categorias Fantasmas:** Há categorias de *Sopros e Cordas Orquestrais* ativas, mas sem estoque. O *System Prompt* foi blindado para checar a tabela antes de prometer marcas não cadastradas.

---

## 🚧 4. Limitações Conhecidas e Próximos Passos (Backlog)

Se houvesse mais tempo de projeto, eu focaria em:
*   **Infraestrutura:** Adicionar suporte a Docker (`docker-compose`) e PostgreSQL para produção (substituindo o SQLite).
*   **Escalabilidade do RAG:** Caso o manual crescesse para 500+ páginas, a troca do TF-IDF por um cluster Qdrant/Pinecone com embeddings.
*   **Busca Semântica Híbrida (Produtos):** Hoje a busca no catálogo requer correspondências muito literais. Adicionaria o ElasticSearch para lidar com erros de digitação (*typos*) na busca por instrumentos.
*   **Tratamento Assíncrono:** Reescrever as funções de chamada de I/O em `asyncio` para suportar alta concorrência em uma API FastAPI.

---

## 🤖 5. Uso Transparente de Assistentes de IA

Acredito que engenheiros modernos devem usar IAs para amplificar a capacidade, e não terceirizar o raciocínio crítico. Minha *stack* de desenvolvimento e fluxo de trabalho incluíram:

*   **Gemini 3.1 Pro (Chat):** Utilizado massivamente na fase de "Quadro Branco" (*Whiteboarding*). Enviei os CSVs e o PDF para criar resumos estruturados e debater os *Trade-Offs* entre LangChain vs Native Python, além de mapear as "Categorias Fantasmas".
*   **Cursor IDE (Claude 3.5 Sonnet):** Usado para autocompletar *boilerplates*. Ele foi incrivelmente útil para redigir o bloco massivo do *System Prompt* da Persona e gerar as classes `Pydantic` utilizadas para padronizar o schema do *Function Calling*.
*   **A Regra de Ouro:** Nenhuma decisão arquitetural (como a abstração da matemática para fora do LLM ou o uso do SQLite) foi delegada às IAs. A estratégia e o raciocínio analítico foram meus; a IA funcionou como meu co-piloto de digitação e revisão sintática.

---
*Feito com rigor, Python e muito café. Desenvolvido para o Desafio Artefact.*