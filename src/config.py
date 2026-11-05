"""Módulo de Configuração Central do Projeto (config.py)

-
Responsável por:
1. Carregar variáveis de ambiente a partir do arquivo .env local.
2. Mapear caminhos absolutos para diretórios do sistema (independente de onde o script é executado).
3. Validar a presença de credenciais obrigatórias antes da execução da aplicação (Fail-Fast).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 1. Carrega as configurações do arquivo .env para a memória do sistema operacional (os.environ)
load_dotenv()

# 2. Resolução de Caminhos do Projeto
# __file__: caminho relativo deste arquivo (src/config.py)
# .resolve(): converte para o caminho absoluto no sistema operacional
# .parent.parent: sobe dois níveis (de src/ para a pasta raiz do projeto)
BASE_DIR = Path(__file__).resolve().parent.parent

# Define o caminho fixo para a pasta onde estão os CSVs e o manual de políticas em PDF
DATA_DIR = BASE_DIR / "data"

# 3. Credenciais e Parâmetros da LLM (Google Gemini)
# Busca a chave de API configurada no .env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Define o identificador do modelo. Caso a variável não esteja declarada no .env,
# utiliza "gemini-2.0-flash" como valor padrão seguro (fallback)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

# 4. Validação Defensiva (Princípio Fail-Fast)
# Interrompe o programa logo no início caso a chave de API esteja ausente,
# fornecendo uma mensagem de erro clara em vez de falhar no meio de uma consulta.
if not GEMINI_API_KEY:
    raise ValueError(
        "A variável GEMINI_API_KEY não foi encontrada. "
        "Crie um arquivo .env na raiz do projeto com base no .env.example."
    )