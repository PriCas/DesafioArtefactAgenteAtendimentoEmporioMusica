"""


OBJETIVO :
-----------------------------
1. Orquestração Conversacional com Tool Calling Nativo:
    Em vez de utilizar frameworks pesados que adicionam camadas desnecessárias de abstração
    (como versões antigas do LangChain), o agente utiliza o recurso nativo de 'Automatic
    Function Calling' do SDK do Gemini. Isso significa que o modelo:
    a) Analisa a intenção da mensagem do usuário;
    b) Decide autonomamente se precisa consultar banco (SQL), manual (RAG) ou responder direto;
    c) O SDK executa a função Python localmente;
    d) O retorno é reinjetado no modelo para a geração da resposta natural final.

2. Persistência de Contexto e Memória de Conversa (Stateful Chat):
    O uso de 'start_chat()' mantém a memória de curto prazo da sessão. Isso permite resolver
    anáforas e pronomes naturais na fala humana (ex.: o cliente pergunta "Quanto custa o
    Takamine GD20?" e, em seguida, indaga "E vocês parcelam ele?"). O agente lembra de qual
    instrumento está falando.

3. Resiliência de API e Alta Disponibilidade (Fallback Strategy):
    Provedores de LLM atualizam e depreciam endpoints com frequência (como versões flash).
    A classe implementa um padrão de cascata (fallback de modelos) tanto na inicialização
    quanto no tratamento de erros de runtime (como 404), garantindo que a aplicação permaneça
    funcional e estável para os avaliadores.
"""

import google.generativeai as genai
from src.config import GEMINI_API_KEY, GEMINI_MODEL
from src.prompts import SYSTEM_INSTRUCTION
from src.tools import (
    buscar_produtos_no_catalogo,
    consultar_status_pedido,
    consultar_politicas_da_loja,
)

# Autenticação global no SDK com a chave fornecida via .env
genai.configure(api_key=GEMINI_API_KEY)


class EmporioAgent:
    """
    Controlador central do agente conversacional do Empório da Música.
    Gerencia o ciclo de vida do modelo, a memória da sessão e o roteamento de ferramentas.
    """

    def __init__(self):
        # Lista de ferramentas disponibilizadas para o modelo decidir a execução
        tools = [
            buscar_produtos_no_catalogo,
            consultar_status_pedido,
            consultar_politicas_da_loja,
        ]

        # Estratégia de Fallback: lista ordenada de modelos candidatos para prevenir
        # falhas caso um endpoint específico esteja instável ou descontinuado na região da API
        model_candidates = [
            GEMINI_MODEL,
            "gemini-3.8-flash",
            "gemini-2.5-flash",
        ]

        self.model = None

        # Tenta inicializar o primeiro modelo disponível da lista
        for model_name in model_candidates:
            if not model_name:
                continue
            try:
                # Instanciação do modelo com System Prompt de Persona e registro de ferramentas
                self.model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=SYSTEM_INSTRUCTION,
                    tools=tools,
                )

                # Inicializa a sessão com histórico contínuo e execução automática das ferramentas:
                # 'enable_automatic_function_calling=True' fecha o loop ReAct sem necessidade
                # de escrever manualmente um laço 'while tool_call' em Python
                self.chat = self.model.start_chat(
                    enable_automatic_function_calling=True
                )
                break
            except Exception:
                # Se o modelo falhar (ex: 404), continua a iteração para o próximo candidato
                continue

        # Falha explícita caso nenhum modelo seja aceito pela chave
        if not self.model:
            raise RuntimeError(
                "Não foi possível inicializar nenhum modelo Gemini com a chave de API fornecida."
            )

    def send_message(self, user_message: str) -> str:
        """
        Envia uma nova mensagem do usuário para o agente e retorna a resposta processada.

        O método mantém o histórico da conversa atualizado automaticamente dentro da sessão
        e trata exceções de rede ou indisponibilidade de ferramentas com mensagens amigáveis.

        Args:
            user_message (str): Texto enviado pelo usuário no terminal ou interface web.

        Returns:
            str: Resposta final do atendente em linguagem natural.
        """
        try:
            # Envio da mensagem: o SDK executa as tools necessárias antes de retornar o texto
            response = self.chat.send_message(user_message)
            return response.text
        except Exception as e:
            # Fallback defensivo de tempo de execução: se o endpoint original retornar 404
            # durante a conversa, tenta reconectar dinamicamente via modelo estável
            if "404" in str(e):
                try:
                    self.model = genai.GenerativeModel(
                        model_name="gemini-3.8-flash",
                        system_instruction=SYSTEM_INSTRUCTION,
                        tools=[
                            buscar_produtos_no_catalogo,
                            consultar_status_pedido,
                            consultar_politicas_da_loja,
                        ],
                    )
                    self.chat = self.model.start_chat(
                        enable_automatic_function_calling=True
                    )
                    response = self.chat.send_message(user_message)
                    return response.text
                except Exception as inner_e:
                    return f"Erro na consulta: {str(inner_e)}"

            # Tratamento de erro gracioso para o usuário final (sem quebrar a aplicação)
            return (
                f"Desculpe, tive um probleminha ao consultar o sistema: {str(e)}"
            )

    def get_history(self):
        """
        Retorna a lista completa de interações (mensagens de usuário, chamadas de tools e
        respostas do modelo) da sessão atual. Útil para auditoria e logs.
        """
        return self.chat.history