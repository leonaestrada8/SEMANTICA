# config.py
import os

# Credenciais Serpro
CLIENT_ID = "lS3LI_KbE2F9dLN1nvORdyl91tga"
CLIENT_SECRET = "W0vfA0igvbkW4Gp3m1b3sIycJXYa"

# Configurações básicas
AMBIENTE = os.getenv("SERPRO_AMBIENTE", "exp")
MODEL_NAME = "deepseek-r1-distill-qwen-14b"
REQUEST_TIMEOUT = 60
MAX_RETRIES = 3
RETRY_DELAY = 1.0

# URLs baseadas no ambiente
def get_urls():
    base = "https://e-api-serprollm.ni.estaleiro.serpro.gov.br" if AMBIENTE == "exp" else \
           "https://api-serprollm.ni.estaleiro.serpro.gov.br"
    return {
        "token": f"{base}/oauth2/token",
        "api": f"{base}/gateway/v1"
    }

# Configuração LLM
LLM_CONFIG = {
    "temperature": 0.1,
    "max_tokens": 500,
    "top_p": 0.9
}

# Arquivos e pastas
CERT_FILE = "ca-pro.pem"
CERT_URL = "https://lcrspo.serpro.gov.br/ca/ca-pro.pem"
INPUT_FOLDER = "./justificativas"
OUTPUT_FOLDER = "./JSON"

# Thresholds de confiança
CONFIDENCE_HIGH = 0.7
CONFIDENCE_MEDIUM = 0.5

# Prompt template
PROMPT_TEMPLATE = """Você é um especialista em empréstimos consignados.
Analise se a justificativa se enquadra em:
• Consignação sem autorização prévia
• Consignação sem crédito do valor
• Desconto de contrato já liquidado

Não aceite:
• Rediscussão de contrato
• Requisições de boletos

Responda em JSON:
{{
  "diagnosticoLLM": "SIM" | "NÃO",
  "justificativaLLM": "explicação breve",
  "confidence": 0.0-1.0
}}

Justificativa: {justificativa}"""