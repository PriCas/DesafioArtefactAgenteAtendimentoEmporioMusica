"""
Módulo: main.py
Projeto: Agente de Atendimento Inteligente - Empório da Música (Desafio Artefact)

OBJETIVO TÉCNICO NO DESAFIO:
-----------------------------
1. Interface de Interação Principal (CLI):
   O enunciado do desafio permite escolher entre CLI, notebook, API ou UI.
   A CLI interativa foi escolhida como ponto de entrada principal por oferecer:
   - Fricção zero para os avaliadores: não depende de portas de navegador, servidores
     web ou configurações complexas; basta clonar e executar 'python main.py'.
   - Alta reprodutibilidade em qualquer sistema operacional (Linux, macOS, Windows).

2. Experiência de Uso Aprimorada (Terminal UX com 'rich'):
   Modelos de linguagem respondem naturalmente em Markdown (com listas numeradas,
   tabelas, negritos e tópicos). O uso da biblioteca 'rich' garante que o Markdown
   seja parseado e estilizado diretamente no terminal, além de exibir um indicador visual
   de progresso (spinner) enquanto o agente executa tools no banco ou no RAG.

3. Ciclo de Vida da Sessão (REPL - Read-Eval-Print Loop):
   Mantém um loop contínuo de conversação que preserva o contexto na mesma instância de
   'EmporioAgent', possibilitando interações em múltiplos turnos e encerramento gracioso.
"""

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from src.agent import EmporioAgent

# Inicializa o console da biblioteca Rich para saída estilizada no terminal
console = Console()


def run_cli():
    """
    Executa o loop interativo (REPL) de atendimento ao cliente via linha de comando.
    """
    # Banner de boas-vindas destacando a identidade da loja 'Empório da Música'
    console.print(
        Panel.fit(
            "[bold green]Empório da Música - Assistente Virtual[/bold green]\n"
            "[dim]Sua música começa aqui | Digite 'sair' para encerrar.[/dim]",
            border_style="green",
        )
    )

    # Inicialização da instância do agente (carrega o banco em RAM e conecta à API)
    agent = EmporioAgent()

    # Loop de conversação contínua da sessão
    while True:
        try:
            # Captura a entrada do usuário com prompt formatado e remoção de espaços extras
            user_input = console.input("[bold blue]Você:[/bold blue] ").strip()
            
            # Ignora envios vazios (pressionar Enter sem texto)
            if not user_input:
                continue

            # Comandos de saída amigáveis
            if user_input.lower() in ["sair", "exit", "quit"]:
                console.print(
                    "\n[green]Atendente:[/green] Valeu por falar com o Empório da Música! "
                    "Qualquer dúvida, estamos por aqui. Até mais! 🎸\n"
                )
                break

            # Indicador de atividade visual (Spinner):
            # Dá feedback ao usuário enquanto o LLM decide o roteamento, consulta o banco
            # SQLite via function calling ou processa os chunks do RAG
            with console.status(
                "[dim yellow]Consultando informações no Empório...[/dim yellow]"
            ):
                response = agent.send_message(user_input)

            # Exibição da resposta do assistente
            console.print("\n[bold green]Empório da Música:[/bold green]")
            # Renderiza o texto Markdown retornado pelo modelo de forma elegante
            console.print(Markdown(response))
            # Linha divisória para separar claramente os turnos da conversa
            console.print("-" * 60)

        except KeyboardInterrupt:
            # Tratamento gracioso para caso o usuário finalize via Ctrl+C no terminal
            console.print("\n\nAtendimento finalizado com sucesso. Até logo! 🎸")
            break


# Garante que o script só seja executado se chamado diretamente como ponto de entrada
if __name__ == "__main__":
    run_cli()