"""
Módulo: app.py
Projeto: Agente de Atendimento Inteligente - Empório da Música (Desafio Artefact)

OBJETIVO TÉCNICO NO DESAFIO:
-----------------------------
1. Interface Web Visual (UI Simples):
   O desafio prevê a escolha entre CLI, notebook, API ou UI. A inclusão deste app em Streamlit
   agrega alto valor à entrega por permitir:
   - Demonstrações visuais rápidas e interativas da experiência de atendimento;
   - Geração de prints de tela profissionais com formatação de balões de conversa (chat bubbles)
     para enriquecer os exemplos exigidos no 'README.md' e na pasta 'examples/'.

2. Gestão de Estado e Ciclo de Vida Reativo (Streamlit Session State):
   Por padrão, o Streamlit reexecuta todo o script a cada nova mensagem digitada pelo usuário.
   O uso de 'st.session_state' é fundamental para:
   - Manter a mesma instância de 'EmporioAgent' viva entre as interações, garantindo que
     o histórico de contexto do Gemini não seja reiniciado a cada turno;
   - Preservar o histórico visual de mensagens na tela do navegador.

3. Experiência de Atendimento Realista:
   Simula fielmente a experiência de um chat de suporte via web/WhatsApp, com saudação inicial,
   indicador de carregamento ('spinner') durante a execução das ferramentas e renderização nativa
   de markdown para tabelas de preços e especificações de instrumentos.
"""

import streamlit as st
from src.agent import EmporioAgent

# Configuração da página web (título da aba, favicon de guitarra e layout centralizado)
st.set_page_config(
    page_title="Empório da Música - Atendimento",
    page_icon="🎸",
    layout="centered",
)

# Identidade visual e cabeçalho alinhados com o manual da loja (Rua 14 de Maio - Campo Grande/MS)
st.title("🎸 Empório da Música")
st.caption("Assistente Virtual de Atendimento ao Cliente — Campo Grande/MS")

# GESTÃO DE ESTADO: Instanciação única do agente conversacional
# Evita recriar a conexão com o Gemini ou recarregar o banco SQLite em memória a cada mensagem
if "agent" not in st.session_state:
    st.session_state.agent = EmporioAgent()

# GESTÃO DE ESTADO: Histórico visual de mensagens da interface
# Inicia com uma saudação receptiva alinhada com a persona da loja
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Olá! Boas-vindas ao Empório da Música! 🎶 "
                "Sou seu assistente aqui da loja. Como posso ajudar você hoje?"
            ),
        }
    ]

# Renderização do histórico completo de mensagens na tela a cada ciclo do Streamlit
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Captura de nova entrada do usuário via barra de chat inferior (usando o walrus operator :=)
if prompt := st.chat_input("Digite sua mensagem..."):
    # 1. Registra e renderiza imediatamente a mensagem enviada pelo usuário
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Exibe balão do assistente com feedback visual durante o processamento
    with st.chat_message("assistant"):
        # Mostra indicador animado enquanto o modelo decide e executa as tools (SQL ou RAG)
        with st.spinner("Consultando dados da loja..."):
            reply = st.session_state.agent.send_message(prompt)
            st.markdown(reply)

    # 3. Persiste a resposta do agente no histórico para manter o chat na próxima reexecução
    st.session_state.messages.append({"role": "assistant", "content": reply})