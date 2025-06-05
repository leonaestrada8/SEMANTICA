# 0_config.py - VERSÃO COMPLETA CORRIGIDA
import os
from typing import Dict, Any
from pathlib import Path

class SerproConfig:
    """Configurações centralizadas para todo o sistema Serpro LLM"""
    
    def __init__(self):
        # ========== CREDENCIAIS SERPRO - CORRIGIDO ==========
        self.CLIENT_ID = "lS3LI_KbE2F9dLN1nvORdyl91tga"
        self.CLIENT_SECRET = "W0vfA0igvbkW4Gp3m1b3sIycJXYa"
        
        # ========== AMBIENTE E MODELO ==========
        self.AMBIENTE = os.getenv("SERPRO_AMBIENTE", "exp")  # 'exp' ou 'prod'
        self.MODEL_NAME = os.getenv("SERPRO_MODEL", "deepseek-r1-distill-qwen-14b")
        
        # ========== CONFIGURAÇÕES SSL ==========
        self.CERT_FILE = "ca-pro.pem"
        self.CERT_URL = "https://lcrspo.serpro.gov.br/ca/ca-pro.pem"
        
        # ========== TIMEOUTS E LIMITES ==========
        self.REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "60"))  # segundos
        self.CONNECTION_TIMEOUT = int(os.getenv("CONNECTION_TIMEOUT", "10"))  # segundos
        
        # ========== CONFIGURAÇÕES DE RETRY ==========
        self.RETRY_CONFIG = {
            "max_retries": int(os.getenv("MAX_RETRIES", "5")),
            "retry_delay": float(os.getenv("RETRY_DELAY", "1.0")),
            "backoff_multiplier": float(os.getenv("BACKOFF_MULTIPLIER", "1.5")),
            "max_delay": float(os.getenv("MAX_DELAY", "30.0")),
            "jitter": True
        }
        
        # ========== CONFIGURAÇÕES DO LLM ==========
        self.LLM_CONFIG = {
            "temperature": float(os.getenv("LLM_TEMPERATURE", "0.1")),
            "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "500")),
            "top_p": float(os.getenv("LLM_TOP_P", "0.9")),
            "frequency_penalty": float(os.getenv("LLM_FREQ_PENALTY", "0.0")),
            "presence_penalty": float(os.getenv("LLM_PRES_PENALTY", "0.0")),
        }
        
        # ========== PROCESSAMENTO DE ARQUIVOS ==========
        self.FILE_PROCESSING = {
            "input_folder": os.getenv("INPUT_FOLDER", "./justificativas"),
            "output_folder": os.getenv("OUTPUT_FOLDER", "./JSON"),
            "default_filename": os.getenv("DEFAULT_FILENAME", "5.txt"),
            "batch_size": int(os.getenv("BATCH_SIZE", "10")),
            "delay_between_requests": float(os.getenv("DELAY_BETWEEN_REQUESTS", "1.0")),
            "save_individual_files": bool(os.getenv("SAVE_INDIVIDUAL_FILES", "true").lower() == "true"),
            "save_summary_stats": bool(os.getenv("SAVE_SUMMARY_STATS", "true").lower() == "true"),
            "encoding": os.getenv("FILE_ENCODING", "utf-8"),
            "skip_header": bool(os.getenv("SKIP_HEADER", "true").lower() == "true")
        }
        
        # ========== CONFIGURAÇÕES DE SAÍDA JSON ==========
        self.JSON_CONFIG = {
            "indent": int(os.getenv("JSON_INDENT", "2")),
            "ensure_ascii": bool(os.getenv("JSON_ENSURE_ASCII", "false").lower() == "true"),
            "sort_keys": bool(os.getenv("JSON_SORT_KEYS", "true").lower() == "true"),
            "timestamp_format": os.getenv("TIMESTAMP_FORMAT", "%Y-%m-%dT%H:%M:%S.%f"),
            "include_metadata": bool(os.getenv("INCLUDE_METADATA", "true").lower() == "true")
        }
        
        # ========== LOGGING ==========
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FILE = os.getenv("LOG_FILE", "serpro_llm.log")
        self.LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        self.LOG_MAX_SIZE = int(os.getenv("LOG_MAX_SIZE", "10485760"))  # 10MB
        self.LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))
        
        # ========== ESTATÍSTICAS E MONITORAMENTO ==========
        self.STATS_CONFIG = {
            "save_stats": bool(os.getenv("SAVE_STATS", "true").lower() == "true"),
            "stats_file": os.getenv("STATS_FILE", "estatisticas.json"),
            "update_interval": int(os.getenv("STATS_UPDATE_INTERVAL", "10")),  # segundos
            "track_performance": bool(os.getenv("TRACK_PERFORMANCE", "true").lower() == "true")
        }
        
        # ========== API E WEBSERVER ==========
        self.API_CONFIG = {
            "host": os.getenv("API_HOST", "0.0.0.0"),
            "port": int(os.getenv("API_PORT", "8000")),
            "debug": bool(os.getenv("API_DEBUG", "false").lower() == "true"),
            "auto_reload": bool(os.getenv("API_AUTO_RELOAD", "false").lower() == "true")
        }
        
        # ========== VALIDAÇÃO DE ENTRADA ==========
        self.VALIDATION_CONFIG = {
            "required_fields": ["id_termo", "cpf", "pratica_vedada", "justificativa"],
            "min_justificativa_length": int(os.getenv("MIN_JUSTIFICATIVA_LENGTH", "10")),
            "max_justificativa_length": int(os.getenv("MAX_JUSTIFICATIVA_LENGTH", "5000")),
            "cpf_validation": bool(os.getenv("CPF_VALIDATION", "false").lower() == "true"),
            "sanitize_input": bool(os.getenv("SANITIZE_INPUT", "true").lower() == "true")
        }
        
        # ========== CONFIGURAÇÕES DE UI - ADICIONADO ==========
        self.UI_CONFIG = {
            "use_emojis": bool(os.getenv("USE_EMOJIS", "true").lower() == "true"),
            "show_progress": bool(os.getenv("SHOW_PROGRESS", "true").lower() == "true"),
            "colored_output": bool(os.getenv("COLORED_OUTPUT", "false").lower() == "true")
        }
        
    def get_urls(self) -> Dict[str, str]:
        """Retorna URLs baseadas no ambiente"""
        if self.AMBIENTE == "prod":
            base_url = "https://api-serprollm.ni.estaleiro.serpro.gov.br"
        elif self.AMBIENTE == "exp":
            base_url = "https://e-api-serprollm.ni.estaleiro.serpro.gov.br"
        else:
            raise ValueError(f"Ambiente inválido: {self.AMBIENTE}. Use 'exp' ou 'prod'.")
        
        return {
            "base": base_url,
            "token": f"{base_url}/oauth2/token",
            "api": f"{base_url}/gateway/v1"
        }
    
    def get_file_processing_paths(self) -> Dict[str, Path]:
        """Retorna paths para processamento de arquivos"""
        input_folder = Path(self.FILE_PROCESSING["input_folder"])
        output_folder = Path(self.FILE_PROCESSING["output_folder"])
        
        # Criar pastas se não existirem
        input_folder.mkdir(exist_ok=True)
        output_folder.mkdir(exist_ok=True)
        
        input_file = input_folder / self.FILE_PROCESSING["default_filename"]
        stats_file = output_folder / self.STATS_CONFIG["stats_file"]
        
        return {
            "input": input_folder,
            "output": output_folder,
            "input_file": input_file,
            "stats_file": stats_file
        }
    
    def get_prompt_template(self) -> str:
        """Retorna template do prompt para o LLM"""
        return """Você é um especialista em empréstimos consignados.
Sua tarefa é avaliar a justificativa enviada por um usuário com base em um ou mais dos seguintes critérios:
• Consignação em folha sem autorização prévia e formal do consignado;
• Consignação em folha sem o correspondente crédito do valor ao consignado;
• Manutenção de desconto em folha referente a contrato já liquidado;
Não faz parte do escopo e deve ser negado:
• rediscussão de contrato assinado (contrato indevido, taxas abusivas, etc.);
• requisições de boletos;
Instruções:
Verifique se a justificativa apresentada se enquadra em um ou mais dos critérios acima.
Ao final, produza única saída no formato JSON abaixo, preenchendo todos os campos:
{{
  "requestId": "<UUID>",
  "timestamp": "<ISO 8601 com fuso -03:00>",
  "diagnosticoLLM": "SIM" | "NÃO",
  "justificativaLLM": "<texto livre até 144 caracteres>",
  "confidence": <valor numérico entre 0.0 e 1.0>,
  "status": "success" | "error",
}}
• requestId: id da requisicao gerado aleatoriamente
• timestamp: hora da execução
• diagnosticoLLM: resposta sim ou não se o texto do usuário se encaixa nas categorias determinadas
• justificativaLLM: racional para a resposta acima
• confidence: confiança na resposta do LLM
• status: OK ou NOK
Abaixo, a justificativa enviada pelo usuário:

{justificativa}"""
    
    def create_sample_input_file(self):
        """Criar arquivo de exemplo para processamento"""
        paths = self.get_file_processing_paths()
        sample_file = paths["input_file"]
        
        sample_content = """IDTERMO#CPF#PRATICA VEDADA#JUSTIFICATIVA
TERMO001#12345678901#Desconto sem autorização#Estou sendo descontado na folha sem ter autorizado este empréstimo
TERMO002#98765432109#Contrato já liquidado#Continuam descontando valor de contrato que já foi quitado
TERMO003#11122233344#Crédito não recebido#Foi feito desconto mas nunca recebi o valor do empréstimo
TERMO004#55566677788#Taxa abusiva#Quero renegociar pois a taxa está muito alta
TERMO005#99988877766#Problema com boleto#Não consigo gerar o boleto de pagamento"""
        
        with open(sample_file, 'w', encoding='utf-8') as f:
            f.write(sample_content)
        
        print(f"📄 Arquivo de exemplo criado em: {sample_file}")
        return sample_file
    
    # Corrigir o método validate_config no 0_config.py

    def validate_config(self) -> bool:
        """Valida se todas as configurações necessárias estão presentes"""
        
        missing_fields = []
        
        # LÓGICA CORRIGIDA: verificar se são valores placeholder/padrão
        # Se as credenciais são os valores padrão/exemplo, então não estão configuradas
        if self.CLIENT_ID in ["seu_client_id_aqui", "", None]:
            missing_fields.append("CLIENT_ID")
            
        if self.CLIENT_SECRET in ["seu_client_secret_aqui", "", None]:
            missing_fields.append("CLIENT_SECRET")
        
        # Verificar ambiente
        if self.AMBIENTE not in ["exp", "prod"]:
            missing_fields.append("AMBIENTE")
            
        # Verificar modelo
        if not self.MODEL_NAME:
            missing_fields.append("MODEL_NAME")
            
        if missing_fields:
            print("⚠️  ATENÇÃO: Configure as seguintes variáveis:")
            for field in missing_fields:
                print(f"   - {field}")
            print("\nOpções:")
            print("1. Defina variáveis de ambiente")
            print("2. Ou edite diretamente o arquivo 0_config.py")
            return False
            
        return True
    
    def get_summary(self) -> Dict[str, Any]:
        """Retorna resumo das configurações (sem dados sensíveis)"""
        return {
            "ambiente": self.AMBIENTE,
            "model_name": self.MODEL_NAME,
            "request_timeout": self.REQUEST_TIMEOUT,
            "retry_config": self.RETRY_CONFIG,
            "llm_config": self.LLM_CONFIG,
            "urls": self.get_urls(),
            "client_id_configured": self.CLIENT_ID != "seu_client_id_aqui",
            "client_secret_configured": self.CLIENT_SECRET != "seu_client_secret_aqui"
        }

# Para testes - remova em produção
if __name__ == "__main__":
    config = SerproConfig()
    
    print("🔧 CONFIGURAÇÃO SERPRO LLM")
    print("=" * 40)
    
    summary = config.get_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")
    
    print("\n" + "=" * 40)
    
    if config.validate_config():
        print("✅ Configuração válida!")
    else:
        print("❌ Configuração incompleta!")