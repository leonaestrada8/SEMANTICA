# logger.py
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

class SemanticaLogger:
    def __init__(self):
        self.setup_logging()
    
    def setup_logging(self):
        """Configura sistema de logging"""
        # Criar pasta de logs
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Configurar formato
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Logger principal
        self.logger = logging.getLogger('semantica_api')
        self.logger.setLevel(logging.INFO)
        
        # Remover handlers existentes
        self.logger.handlers.clear()
        
        # Handler para arquivo principal (rotativo)
        main_handler = RotatingFileHandler(
            log_dir / "semantica_api.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        main_handler.setLevel(logging.INFO)
        main_handler.setFormatter(formatter)
        self.logger.addHandler(main_handler)
        
        # Handler para erros (separado)
        error_handler = RotatingFileHandler(
            log_dir / "errors.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)
        
        # Handler para console (opcional)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Logger específico para LLM calls
        self.llm_logger = logging.getLogger('serpro_llm')
        self.llm_logger.setLevel(logging.DEBUG)
        
        llm_handler = RotatingFileHandler(
            log_dir / "llm_calls.log",
            maxBytes=20*1024*1024,  # 20MB
            backupCount=3,
            encoding='utf-8'
        )
        llm_handler.setLevel(logging.DEBUG)
        llm_handler.setFormatter(formatter)
        self.llm_logger.addHandler(llm_handler)
        
        # Logger para WebSocket
        self.ws_logger = logging.getLogger('websocket')
        self.ws_logger.setLevel(logging.INFO)
        
        ws_handler = RotatingFileHandler(
            log_dir / "websocket.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=2,
            encoding='utf-8'
        )
        ws_handler.setLevel(logging.INFO)
        ws_handler.setFormatter(formatter)
        self.ws_logger.addHandler(ws_handler)
        
        # Log inicial
        self.logger.info("=== Sistema de Logging Iniciado ===")
        self.logger.info(f"Logs sendo salvos em: {log_dir.absolute()}")
    
    def log_api_request(self, endpoint, data=None, result=None, error=None, processing_time=None):
        """Log de requisições da API"""
        try:
            if error:
                self.logger.error(f"API {endpoint} | ERRO: {error}")
            else:
                status = result.get('status', 'UNKNOWN') if result else 'NO_RESULT'
                confidence = result.get('confidence', 0) if result else 0
                time_str = f" | {processing_time:.2f}s" if processing_time else ""
                
                self.logger.info(f"API {endpoint} | {status} | {confidence:.2f}{time_str}")
        except Exception as e:
            self.logger.error(f"Erro ao fazer log da requisição: {e}")
    
    def log_llm_call(self, prompt_preview, result=None, error=None, processing_time=None):
        """Log específico para chamadas LLM"""
        try:
            # Preview do prompt (primeiros 100 caracteres)
            prompt_short = prompt_preview[:100].replace('\n', ' ') + "..." if len(prompt_preview) > 100 else prompt_preview
            
            if error:
                self.llm_logger.error(f"LLM_CALL | ERRO: {error} | Prompt: {prompt_short}")
            else:
                diagnostico = result.get('diagnosticoLLM', 'N/A') if result else 'NO_RESULT'
                confidence = result.get('confidence', 0) if result else 0
                time_str = f" | {processing_time:.2f}s" if processing_time else ""
                
                self.llm_logger.info(f"LLM_CALL | {diagnostico} | {confidence:.2f}{time_str} | Prompt: {prompt_short}")
        except Exception as e:
            self.llm_logger.error(f"Erro ao fazer log da chamada LLM: {e}")
    
    def log_websocket_event(self, event, data=None, error=None):
        """Log de eventos WebSocket"""
        try:
            if error:
                self.ws_logger.error(f"WS_{event} | ERRO: {error}")
            else:
                data_str = str(data)[:200] if data else ""
                self.ws_logger.info(f"WS_{event} | {data_str}")
        except Exception as e:
            self.ws_logger.error(f"Erro ao fazer log do WebSocket: {e}")
    
    def log_file_processing(self, filename, total_items, results_summary):
        """Log de processamento de arquivos"""
        try:
            approved = results_summary.get('approved', 0)
            rejected = results_summary.get('rejected', 0)
            review = results_summary.get('review_required', 0)
            errors = results_summary.get('errors', 0)
            
            self.logger.info(f"FILE_PROCESSING | {filename} | Total: {total_items} | "
                           f"Aprovados: {approved} | Rejeitados: {rejected} | "
                           f"Revisão: {review} | Erros: {errors}")
        except Exception as e:
            self.logger.error(f"Erro ao fazer log do processamento: {e}")
    
    def log_error(self, context, error, details=None):
        """Log de erros gerais"""
        try:
            details_str = f" | Detalhes: {details}" if details else ""
            self.logger.error(f"{context} | {str(error)}{details_str}")
        except Exception as e:
            print(f"Erro crítico no sistema de logging: {e}")
    
    def log_info(self, message, context="GENERAL"):
        """Log de informações gerais"""
        try:
            self.logger.info(f"{context} | {message}")
        except Exception as e:
            print(f"Erro ao fazer log de info: {e}")

# Instância global
semantic_logger = SemanticaLogger()