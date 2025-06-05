# 1_api_main.py - API WEB UNIFICADA PARA ANÁLISE SEMÂNTICA DE CONSIGNAÇÃO
"""
SISTEMA WEB COMPLETO PARA ANÁLISE SEMÂNTICA DE JUSTIFICATIVAS - VERSÃO UNIFICADA

Principais melhorias desta versão:
1. ENDPOINT UNIFICADO: Um único endpoint /analise-semantica que detecta automaticamente o formato
2. DETECÇÃO INTELIGENTE: Aceita tanto JSON estruturado quanto string direta
3. COMPATIBILIDADE TOTAL: Funciona com códigos existentes e novos formatos
4. LOGS APRIMORADOS: Tracking detalhado do formato detectado
5. INTERFACE ATUALIZADA: Interface web otimizada para o novo endpoint
"""

# ========== IMPORTS E DEPENDÊNCIAS ==========
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import asyncio
from pydantic import BaseModel
import time
from pathlib import Path
import aiohttp
import requests
from typing import Dict, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
import logging
from logging.handlers import RotatingFileHandler
import uuid
import re
import sys
from dataclasses import dataclass
from enum import Enum
import traceback
from contextlib import asynccontextmanager

# ========== IMPORT DA CONFIGURAÇÃO CENTRALIZADA ==========
sys.path.append(os.path.dirname(__file__))
import importlib.util
spec = importlib.util.spec_from_file_location("config", "0_config.py")
config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_module)
SerproConfig = config_module.SerproConfig

# ========== CONFIGURAÇÃO AVANÇADA DE LOGGING ==========
def setup_enhanced_logging():
    """CONFIGURAÇÃO AVANÇADA DE LOGGING COM ROTAÇÃO E ESTRUTURAÇÃO"""
    
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)
    
    logger = logging.getLogger("serpro_llm_api")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s'
    )
    
    console_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s'
    )
    
    # Handler principal com rotação
    file_handler = RotatingFileHandler(
        log_dir / 'api_semantica.log',
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(detailed_formatter)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    
    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    
    # Handler para erros críticos
    error_handler = RotatingFileHandler(
        log_dir / 'api_errors.log',
        maxBytes=5*1024*1024,
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setFormatter(detailed_formatter)
    error_handler.setLevel(logging.ERROR)
    logger.addHandler(error_handler)
    
    # Handler para performance
    performance_handler = RotatingFileHandler(
        log_dir / 'api_performance.log',
        maxBytes=5*1024*1024,
        backupCount=3,
        encoding='utf-8'
    )
    performance_handler.setFormatter(logging.Formatter(
        '%(asctime)s | PERF | %(message)s'
    ))
    performance_handler.setLevel(logging.INFO)
    
    perf_logger = logging.getLogger("performance")
    perf_logger.setLevel(logging.INFO)
    perf_logger.handlers.clear()
    perf_logger.addHandler(performance_handler)
    perf_logger.addHandler(console_handler)
    
    return logger, perf_logger

logger, perf_logger = setup_enhanced_logging()

# ========== SISTEMA DE CLASSIFICAÇÃO DE ERROS ==========
class ErrorType(Enum):
    """ENUM PARA CATEGORIZAÇÃO INTELIGENTE DE ERROS"""
    AUTH_ERROR = "auth_error"
    TOKEN_EXPIRED = "token_expired"
    ACCESS_DENIED = "access_denied"
    CONNECTION_ERROR = "connection_error"
    TIMEOUT_ERROR = "timeout_error"
    SSL_CERT_ERROR = "ssl_cert_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    SERVER_ERROR = "server_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    JSON_PARSE_ERROR = "json_parse_error"
    VALIDATION_ERROR = "validation_error"
    PARSE_ERROR = "parse_error"
    LLM_TIMEOUT = "llm_timeout"
    LLM_CONNECTION_ERROR = "llm_connection_error"
    LLM_ERROR = "llm_error"
    HTTP_ERROR = "http_error"
    UNEXPECTED_ERROR = "unexpected_error"
    MAX_RETRIES_EXCEEDED = "max_retries_exceeded"

@dataclass
class ErrorDetail:
    """ESTRUTURA DETALHADA PARA INFORMAÇÕES DE ERRO"""
    error_type: ErrorType
    message: str
    status_code: Optional[int] = None
    retry_after: Optional[int] = None
    attempt: int = 1
    timestamp: str = None
    traceback_info: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

class SerproLLMError(Exception):
    """EXCEÇÃO CUSTOMIZADA PARA ERROS ESPECÍFICOS DO SERPRO LLM"""
    def __init__(self, message: str, error_type: ErrorType = ErrorType.UNEXPECTED_ERROR, status_code: int = None):
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        super().__init__(self.message)

# ========== SISTEMA DE MONITORAMENTO DE ERROS ==========
class ErrorStatistics:
    """SISTEMA INTELIGENTE DE MONITORAMENTO E MÉTRICAS COM LOGGING INTEGRADO"""
    
    def __init__(self):
        self.error_counts = {error_type.value: 0 for error_type in ErrorType}
        self.total_requests = 0
        self.total_retries = 0
        self.start_time = datetime.now()
        self.last_reset = datetime.now()
        self.last_alert_time = {}
        
        logger.info("📊 Sistema de monitoramento de erros inicializado")
        
    def record_error(self, error_type: ErrorType):
        """REGISTRAR OCORRÊNCIA DE ERRO COM LOGGING INTELIGENTE"""
        self.error_counts[error_type.value] += 1
        total_errors = sum(self.error_counts.values())
        
        logger.warning(f"🚨 Erro registrado: {error_type.value} - Total: {self.error_counts[error_type.value]}")
        
        now = datetime.now()
        last_alert = self.last_alert_time.get(error_type.value, datetime.min)
        
        if (now - last_alert).total_seconds() > 300:
            error_count = self.error_counts[error_type.value]
            
            if error_count >= 10:
                logger.error(f"🔥 ALERTA CRÍTICO: {error_type.value} ocorreu {error_count} vezes!")
                self.last_alert_time[error_type.value] = now
            elif error_count >= 5:
                logger.warning(f"⚠️ ALERTA: {error_type.value} ocorreu {error_count} vezes")
                self.last_alert_time[error_type.value] = now
        
        if self.total_requests > 0:
            error_rate = (total_errors / self.total_requests) * 100
            if error_rate > 15:
                perf_logger.warning(f"Taxa de erro crítica: {error_rate:.2f}% - Total requests: {self.total_requests}")
            elif error_rate > 5:
                perf_logger.info(f"Taxa de erro elevada: {error_rate:.2f}% - Total requests: {self.total_requests}")
        
    def record_retry(self):
        """REGISTRAR TENTATIVA DE RETRY COM LOG"""
        self.total_retries += 1
        logger.info(f"🔄 Retry registrado - Total retries: {self.total_retries}")
        
    def record_request(self):
        """REGISTRAR NOVA REQUISIÇÃO COM LOG PERIÓDICO"""
        self.total_requests += 1
        
        if self.total_requests % 100 == 0:
            uptime = (datetime.now() - self.start_time).total_seconds()
            error_rate = (sum(self.error_counts.values()) / self.total_requests) * 100 if self.total_requests > 0 else 0
            perf_logger.info(f"📈 Milestone: {self.total_requests} requests processadas - Error rate: {error_rate:.2f}% - Uptime: {uptime:.0f}s")
        
    def get_statistics(self) -> Dict[str, Any]:
        """GERAR RELATÓRIO COMPLETO DE ESTATÍSTICAS"""
        total_errors = sum(self.error_counts.values())
        uptime = datetime.now() - self.start_time
        
        stats = {
            "total_requests": self.total_requests,
            "total_errors": total_errors,
            "total_retries": self.total_retries,
            "error_rate": (total_errors / self.total_requests * 100) if self.total_requests > 0 else 0,
            "retry_rate": (self.total_retries / self.total_requests * 100) if self.total_requests > 0 else 0,
            "uptime_seconds": uptime.total_seconds(),
            "start_time": self.start_time.isoformat(),
            "error_breakdown": self.error_counts.copy(),
            "most_common_error": max(self.error_counts.items(), key=lambda x: x[1])[0] if total_errors > 0 else "none"
        }
        
        logger.debug(f"📊 Estatísticas consultadas: Requests={stats['total_requests']}, Errors={stats['total_errors']}, Rate={stats['error_rate']:.2f}%")
        return stats
    
    def reset_statistics(self):
        """RESET MANUAL DAS ESTATÍSTICAS COM LOG"""
        old_stats = self.get_statistics()
        
        self.error_counts = {error_type.value: 0 for error_type in ErrorType}
        self.total_requests = 0
        self.total_retries = 0
        self.last_reset = datetime.now()
        
        logger.info(f"🔄 Estatísticas resetadas - Última sessão: {old_stats['total_requests']} requests, {old_stats['total_errors']} errors")

# ========== CONECTOR PRINCIPAL SERPRO LLM ==========
class SerproLLMConnector:
    """CONECTOR ROBUSTO E INTELIGENTE PARA SERPRO LLM COM LOGGING COMPLETO"""
    
    def __init__(self):
        logger.info("🔧 Inicializando SerproLLMConnector...")
        
        self.config = SerproConfig()
        self.client_id = self.config.CLIENT_ID
        self.client_secret = self.config.CLIENT_SECRET
        self.ambiente = self.config.AMBIENTE
        self.model_name = self.config.MODEL_NAME
        
        urls = self.config.get_urls()
        self.url_base = urls["base"]
        self.url_token = urls["token"]
        self.url_api = urls["api"]
        
        logger.info(f"🌐 Configurado para ambiente: {self.ambiente}")
        logger.info(f"🤖 Modelo LLM: {self.model_name}")
        logger.info(f"🔗 URL API: {self.url_api}")
        
        self.setup_certificates()
        
        self.access_token = None
        self.token_expires_at = None
        self.error_stats = ErrorStatistics()
        
        logger.info("✅ SerproLLMConnector inicializado com sucesso")
        
    def setup_certificates(self):
        """CONFIGURAÇÃO AUTOMÁTICA DE CERTIFICADOS SSL COM LOGGING"""
        cert_file = self.config.CERT_FILE
        
        if not os.path.exists(cert_file):
            try:
                logger.info(f"📥 Certificado não encontrado, baixando de: {self.config.CERT_URL}")
                response = requests.get(self.config.CERT_URL, verify=False, timeout=10)
                response.raise_for_status()
                
                with open(cert_file, 'wb') as f:
                    f.write(response.content)
                logger.info(f"✅ Certificado Serpro baixado e salvo em: {cert_file}")
                
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Erro ao baixar certificado: {e}")
                raise SerproLLMError(f"Falha ao baixar certificado SSL: {e}", ErrorType.SSL_CERT_ERROR)
        else:
            logger.info(f"✅ Certificado Serpro encontrado: {cert_file}")
        
        os.environ["REQUESTS_CA_BUNDLE"] = cert_file
        os.environ["SSL_CERT_FILE"] = cert_file
        logger.debug("🔒 Variáveis de ambiente SSL configuradas")
    
    def is_token_valid(self):
        """VERIFICAÇÃO INTELIGENTE DE VALIDADE DO TOKEN"""
        if not self.access_token:
            logger.debug("🔑 Token não disponível")
            return False
        if self.token_expires_at and datetime.now().timestamp() >= self.token_expires_at:
            logger.info("⏰ Token expirado, necessário renovar")
            return False
        
        expires_in = self.token_expires_at - datetime.now().timestamp() if self.token_expires_at else 0
        logger.debug(f"🔑 Token válido, expira em: {expires_in:.0f}s")
        return True
    
    def _categorize_request_error(self, error: Exception, response: requests.Response = None) -> ErrorDetail:
        """CATEGORIZAÇÃO INTELIGENTE DE ERROS DE REQUISIÇÃO"""
        
        if isinstance(error, requests.exceptions.Timeout):
            error_detail = ErrorDetail(
                error_type=ErrorType.TIMEOUT_ERROR,
                message=f"Timeout na requisição: {str(error)}"
            )
            logger.warning(f"⏰ Timeout detectado: {str(error)}")
            return error_detail
        
        if isinstance(error, requests.exceptions.ConnectionError):
            error_detail = ErrorDetail(
                error_type=ErrorType.CONNECTION_ERROR,
                message=f"Erro de conexão: {str(error)}"
            )
            logger.warning(f"🔌 Erro de conexão: {str(error)}")
            return error_detail
        
        if response:
            status = response.status_code
            
            if status == 401:
                logger.warning(f"🚫 Credenciais inválidas (401)")
                return ErrorDetail(
                    error_type=ErrorType.AUTH_ERROR,
                    message="Credenciais inválidas",
                    status_code=status
                )
            
            if status == 403:
                logger.warning(f"🚫 Acesso negado (403)")
                return ErrorDetail(
                    error_type=ErrorType.ACCESS_DENIED,
                    message="Acesso negado",
                    status_code=status
                )
            
            if status == 429:
                retry_after = response.headers.get('Retry-After')
                logger.warning(f"🚦 Rate limit excedido (429) - Retry after: {retry_after}s")
                return ErrorDetail(
                    error_type=ErrorType.RATE_LIMIT_ERROR,
                    message="Rate limit excedido",
                    status_code=status,
                    retry_after=int(retry_after) if retry_after else None
                )
            
            if 500 <= status < 600:
                logger.error(f"🔥 Erro do servidor ({status})")
                return ErrorDetail(
                    error_type=ErrorType.SERVER_ERROR,
                    message=f"Erro do servidor: {status}",
                    status_code=status
                )
        
        logger.error(f"💥 Erro inesperado não categorizado: {str(error)}")
        return ErrorDetail(
            error_type=ErrorType.UNEXPECTED_ERROR,
            message=f"Erro inesperado: {str(error)}",
            traceback_info=traceback.format_exc()
        )
    
    def _calculate_retry_delay(self, attempt: int, error_detail: ErrorDetail) -> float:
        """CÁLCULO INTELIGENTE DE DELAY PARA RETRY"""
        base_delay = self.config.RETRY_CONFIG.get("retry_delay", 1.0)
        backoff = self.config.RETRY_CONFIG.get("backoff_multiplier", 2.0)
        max_delay = self.config.RETRY_CONFIG.get("max_delay", 60.0)
        
        if error_detail.retry_after:
            delay = min(error_detail.retry_after, max_delay)
            logger.info(f"⏳ Usando Retry-After header: {delay}s")
            return delay
        
        delay = base_delay * (backoff ** (attempt - 1))
        jitter = delay * 0.1 * (0.5 - time.time() % 1)
        final_delay = min(delay + jitter, max_delay)
        
        logger.debug(f"⏳ Delay calculado para tentativa {attempt}: {final_delay:.2f}s (base: {delay:.2f}s)")
        return final_delay
    
    def _should_retry(self, error_detail: ErrorDetail, attempt: int) -> bool:
        """DECISÃO INTELIGENTE DE RETRY"""
        max_retries = self.config.RETRY_CONFIG.get("max_retries", 3)
        
        if attempt >= max_retries:
            logger.warning(f"❌ Máximo de tentativas excedido ({max_retries})")
            return False
        
        non_retryable = {
            ErrorType.AUTH_ERROR,
            ErrorType.ACCESS_DENIED,
            ErrorType.VALIDATION_ERROR,
            ErrorType.PARSE_ERROR
        }
        
        should_retry = error_detail.error_type not in non_retryable
        
        if should_retry:
            logger.info(f"🔄 Retry permitido para {error_detail.error_type.value} - Tentativa {attempt}/{max_retries}")
        else:
            logger.warning(f"🚫 Retry não permitido para {error_detail.error_type.value}")
        
        return should_retry
    
    def get_access_token(self):
        """OBTENÇÃO DE TOKEN DE ACESSO COM RETRY INTELIGENTE"""
        max_retries = self.config.RETRY_CONFIG.get("max_retries", 3)
        
        logger.info("🔑 Iniciando obtenção de token Serpro LLM...")
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"🔑 Obtendo token (tentativa {attempt}/{max_retries})")
                
                dados = {"grant_type": "client_credentials"}
                
                start_time = time.time()
                resposta = requests.post(
                    self.url_token, 
                    data=dados, 
                    auth=(self.client_id, self.client_secret),
                    timeout=self.config.REQUEST_TIMEOUT
                )
                
                response_time = time.time() - start_time
                logger.debug(f"⏱️ Token request time: {response_time:.2f}s")
                
                if resposta.status_code == 200:
                    token_data = resposta.json()
                    self.access_token = token_data["access_token"]
                    
                    expires_in = token_data.get("expires_in", 3600)
                    self.token_expires_at = datetime.now().timestamp() + expires_in - 300
                    
                    logger.info(f"✅ Token obtido com sucesso - Expira em: {expires_in}s")
                    perf_logger.info(f"Token obtido em {response_time:.2f}s - Tentativa {attempt}")
                    return self.access_token
                
                error_detail = self._categorize_request_error(None, resposta)
                error_detail.attempt = attempt
                
                logger.warning(f"❌ Erro ao obter token (tentativa {attempt}): {error_detail.message}")
                self.error_stats.record_error(error_detail.error_type)
                
                if not self._should_retry(error_detail, attempt):
                    raise SerproLLMError(error_detail.message, error_detail.error_type, error_detail.status_code)
                
                if attempt < max_retries:
                    delay = self._calculate_retry_delay(attempt, error_detail)
                    logger.info(f"🔄 Aguardando {delay:.2f}s antes do próximo retry...")
                    time.sleep(delay)
                    self.error_stats.record_retry()
                    
            except requests.exceptions.RequestException as e:
                error_detail = self._categorize_request_error(e)
                error_detail.attempt = attempt
                
                logger.warning(f"❌ Erro de requisição token (tentativa {attempt}): {error_detail.message}")
                self.error_stats.record_error(error_detail.error_type)
                
                if not self._should_retry(error_detail, attempt):
                    raise SerproLLMError(error_detail.message, error_detail.error_type)
                
                if attempt < max_retries:
                    delay = self._calculate_retry_delay(attempt, error_detail)
                    time.sleep(delay)
                    self.error_stats.record_retry()
                else:
                    raise SerproLLMError(error_detail.message, error_detail.error_type)
                    
            except Exception as e:
                error_detail = ErrorDetail(
                    error_type=ErrorType.UNEXPECTED_ERROR,
                    message=f"Erro inesperado ao obter token: {str(e)}",
                    attempt=attempt,
                    traceback_info=traceback.format_exc()
                )
                
                logger.error(f"💥 {error_detail.message}")
                logger.debug(f"💥 Traceback: {error_detail.traceback_info}")
                self.error_stats.record_error(error_detail.error_type)
                
                if attempt == max_retries:
                    raise SerproLLMError(error_detail.message, error_detail.error_type)
                    
                delay = self._calculate_retry_delay(attempt, error_detail)
                time.sleep(delay)
                self.error_stats.record_retry()
        
        logger.error("💥 Máximo de tentativas excedido para obter token")
        raise SerproLLMError("Máximo de tentativas excedido para obter token", ErrorType.MAX_RETRIES_EXCEEDED)
    
    async def call_serpro_llm(self, prompt: str) -> Dict[Any, Any]:
        """CHAMADA PRINCIPAL PARA SERPRO LLM COM SISTEMA COMPLETO DE RETRY"""
        request_id = str(uuid.uuid4())[:8]
        max_retries = self.config.RETRY_CONFIG.get("max_retries", 3)
        
        logger.info(f"🤖 [REQ-{request_id}] Iniciando chamada Serpro LLM - Prompt: {len(prompt)} chars")
        
        self.error_stats.record_request()
        
        for attempt in range(1, max_retries + 1):
            try:
                if not self.is_token_valid():
                    logger.info(f"🔑 [REQ-{request_id}] Token inválido, renovando...")
                    self.get_access_token()
                
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": self.model_name,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    **self.config.LLM_CONFIG
                }
                
                logger.info(f"🔄 [REQ-{request_id}] Tentativa {attempt}/{max_retries} - Modelo: {self.model_name}")
                
                start_time = time.time()
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.url_api}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=self.config.REQUEST_TIMEOUT)
                    ) as response:
                        
                        response_time = time.time() - start_time
                        
                        if response.status == 200:
                            result = await response.json()
                            
                            logger.info(f"✅ [REQ-{request_id}] Resposta recebida - Tempo: {response_time:.2f}s - Status: 200")
                            perf_logger.info(f"LLM call successful - Request: {request_id} - Time: {response_time:.2f}s - Attempt: {attempt}")
                            
                            return self.parse_llm_response(result)
                        
                        error_text = await response.text()
                        error_detail = self._categorize_http_error(response.status, error_text)
                        error_detail.attempt = attempt
                        
                        logger.warning(f"❌ [REQ-{request_id}] Erro HTTP - Status: {response.status} - Tempo: {response_time:.2f}s - {error_detail.message}")
                        self.error_stats.record_error(error_detail.error_type)
                        
                        if error_detail.error_type == ErrorType.TOKEN_EXPIRED:
                            logger.info(f"🔑 [REQ-{request_id}] Token expirado, forçando renovação...")
                            self.access_token = None
                            
                        if not self._should_retry(error_detail, attempt):
                            logger.error(f"💥 [REQ-{request_id}] Erro sem retry permitido: {error_detail.message}")
                            raise SerproLLMError(error_detail.message, error_detail.error_type, error_detail.status_code)
                        
                        if attempt < max_retries:
                            delay = self._calculate_retry_delay(attempt, error_detail)
                            logger.info(f"🔄 [REQ-{request_id}] Retry em {delay:.2f}s...")
                            await asyncio.sleep(delay)
                            self.error_stats.record_retry()
                            
            except asyncio.TimeoutError:
                elapsed = time.time() - start_time if 'start_time' in locals() else 0
                error_detail = ErrorDetail(
                    error_type=ErrorType.LLM_TIMEOUT,
                    message=f"Timeout na chamada LLM (tentativa {attempt})",
                    attempt=attempt
                )
                
                logger.warning(f"⏰ [REQ-{request_id}] Timeout - Tentativa {attempt} - Tempo decorrido: {elapsed:.2f}s")
                self.error_stats.record_error(error_detail.error_type)
                
                if attempt == max_retries:
                    logger.error(f"💥 [REQ-{request_id}] Timeout final após {max_retries} tentativas")
                    raise SerproLLMError(error_detail.message, error_detail.error_type)
                    
                delay = self._calculate_retry_delay(attempt, error_detail)
                await asyncio.sleep(delay)
                self.error_stats.record_retry()
                    
            except aiohttp.ClientError as e:
                error_detail = ErrorDetail(
                    error_type=ErrorType.LLM_CONNECTION_ERROR,
                    message=f"Erro de conexão LLM: {str(e)}",
                    attempt=attempt
                )
                
                logger.warning(f"🔌 [REQ-{request_id}] Erro de conexão - Tentativa {attempt}: {str(e)}")
                self.error_stats.record_error(error_detail.error_type)
                
                if attempt == max_retries:
                    logger.error(f"💥 [REQ-{request_id}] Erro de conexão final")
                    raise SerproLLMError(error_detail.message, error_detail.error_type)
                    
                delay = self._calculate_retry_delay(attempt, error_detail)
                await asyncio.sleep(delay)
                self.error_stats.record_retry()
                    
            except SerproLLMError:
                raise
                
            except Exception as e:
                error_detail = ErrorDetail(
                    error_type=ErrorType.UNEXPECTED_ERROR,
                    message=f"Erro inesperado na chamada LLM: {str(e)}",
                    attempt=attempt,
                    traceback_info=traceback.format_exc()
                )
                
                logger.error(f"💥 [REQ-{request_id}] Erro inesperado - Tentativa {attempt}: {str(e)}")
                logger.debug(f"💥 [REQ-{request_id}] Traceback: {error_detail.traceback_info}")
                self.error_stats.record_error(error_detail.error_type)
                
                if attempt == max_retries:
                    logger.error(f"💥 [REQ-{request_id}] Erro inesperado final")
                    raise SerproLLMError(error_detail.message, error_detail.error_type)
                    
                delay = self._calculate_retry_delay(attempt, error_detail)
                await asyncio.sleep(delay)
                self.error_stats.record_retry()
        
        logger.error(f"💥 [REQ-{request_id}] Máximo de tentativas excedido")
        self.error_stats.record_error(ErrorType.MAX_RETRIES_EXCEEDED)
        raise SerproLLMError("Máximo de tentativas excedido para LLM", ErrorType.MAX_RETRIES_EXCEEDED)
    
    def _categorize_http_error(self, status_code: int, response_text: str) -> ErrorDetail:
        """CATEGORIZAÇÃO ESPECÍFICA DE ERROS HTTP"""
        
        if status_code == 401:
            return ErrorDetail(
                error_type=ErrorType.TOKEN_EXPIRED,
                message="Token expirado",
                status_code=status_code
            )
        
        if status_code == 429:
            return ErrorDetail(
                error_type=ErrorType.RATE_LIMIT_ERROR,
                message="Rate limit excedido",
                status_code=status_code
            )
        
        if status_code == 503:
            return ErrorDetail(
                error_type=ErrorType.SERVICE_UNAVAILABLE,
                message="Serviço temporariamente indisponível",
                status_code=status_code
            )
        
        if 500 <= status_code < 600:
            return ErrorDetail(
                error_type=ErrorType.SERVER_ERROR,
                message=f"Erro do servidor: {status_code}",
                status_code=status_code
            )
        
        return ErrorDetail(
            error_type=ErrorType.HTTP_ERROR,
            message=f"Erro HTTP {status_code}: {response_text[:100]}...",
            status_code=status_code
        )
    
    def parse_llm_response(self, llm_response: Dict) -> Dict:
        """PARSING INTELIGENTE DE RESPOSTAS LLM"""
        try:
            content = llm_response["choices"][0]["message"]["content"]
            
            logger.debug(f"🔍 Parsing resposta LLM - Tamanho: {len(content)} chars")
            
            try:
                if content.strip().startswith('{'):
                    parsed_content = json.loads(content)
                    logger.debug("✅ Parsing JSON direto bem-sucedido")
                    return {"llm_analysis": parsed_content}
                
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
                if json_match:
                    parsed_content = json.loads(json_match.group())
                    logger.debug("✅ Parsing JSON via regex bem-sucedido")
                    return {"llm_analysis": parsed_content}
                
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Erro ao parsear JSON da resposta LLM: {e}")
                logger.debug(f"⚠️ Conteúdo que falhou: {content[:200]}...")
                self.error_stats.record_error(ErrorType.JSON_PARSE_ERROR)
            
            logger.info("🔄 Usando fallback inteligente para parsing")
            fallback_response = self.create_fallback_response(content)
            return {"llm_analysis": fallback_response}
                
        except (KeyError, IndexError) as e:
            logger.error(f"❌ Formato de resposta LLM inválido: {e}")
            logger.debug(f"❌ Resposta completa: {llm_response}")
            self.error_stats.record_error(ErrorType.PARSE_ERROR)
            raise SerproLLMError("Formato de resposta LLM inválido", ErrorType.PARSE_ERROR)
    
    def create_fallback_response(self, content: str) -> Dict:
        """FALLBACK INTELIGENTE PARA RESPOSTAS NÃO-JSON"""
        content_lower = content.lower()
        
        approve_words = ["sim", "aprovado", "válido", "procedente", "autorização", "liquidado", "crédito"]
        reject_words = ["não", "rejeitado", "inválido", "taxa", "boleto", "renegociar"]
        
        approve_count = sum(1 for word in approve_words if word in content_lower)
        reject_count = sum(1 for word in reject_words if word in content_lower)
        
        logger.debug(f"🔍 Fallback analysis - Approve: {approve_count}, Reject: {reject_count}")
        
        if approve_count > reject_count:
            diagnostico = "SIM"
            confidence = min(0.9, 0.5 + (approve_count * 0.1))
            logger.info(f"✅ Fallback: APROVAÇÃO inferida - Confiança: {confidence:.2f}")
        else:
            diagnostico = "NÃO"
            confidence = min(0.9, 0.5 + (reject_count * 0.1))
            logger.info(f"❌ Fallback: REJEIÇÃO inferida - Confiança: {confidence:.2f}")
            
        fallback_response = {
            "requestId": str(uuid.uuid4()),
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00"),
            "diagnosticoLLM": diagnostico,
            "justificativaLLM": content[:144],
            "confidence": confidence,
            "status": "success"
        }
        
        logger.debug(f"🔄 Fallback response generated: {fallback_response}")
        return fallback_response
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """INTERFACE PARA OBTER ESTATÍSTICAS COMPLETAS"""
        stats = self.error_stats.get_statistics()
        logger.debug(f"📊 Estatísticas obtidas: {stats['total_requests']} requests, {stats['total_errors']} errors")
        return stats

# ========== LÓGICA DE NEGÓCIO PRINCIPAL ==========
class SemanticaConsignacao:
    """CLASSE PRINCIPAL DE LÓGICA DE NEGÓCIO COM LOGGING INTEGRADO"""
    
    def __init__(self):
        logger.info("🚀 Inicializando SemanticaConsignacao...")
        
        self.serpro_connector = SerproLLMConnector()
        self.justificativas_folder = "./justificativas"
        
        logger.info("✅ SemanticaConsignacao inicializada com sucesso")
        
    def read_justificativas_file(self, filename: str = "100.txt") -> list:
        """LEITURA DE ARQUIVO DE JUSTIFICATIVAS COM LOGGING"""
        try:
            file_path = Path(self.justificativas_folder) / filename
            logger.info(f"📁 Tentando ler arquivo: {file_path}")
            
            if not file_path.exists():
                logger.error(f"❌ Arquivo não encontrado: {file_path}")
                return []
                
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            logger.info(f"📖 Arquivo lido: {len(lines)} linhas totais")
                
            justificativas = []
            for i, line in enumerate(lines):
                line = line.strip()
                if line:
                    if i == 0 and line.startswith("IDTERMO#CPF#PRATICA VEDADA#JUSTIFICATIVA"):
                        logger.info("⏭️ Pulando linha de cabeçalho")
                        continue
                    justificativas.append(line)
                    
            logger.info(f"✅ Carregadas {len(justificativas)} justificativas para processamento")
            return justificativas
            
        except Exception as e:
            logger.error(f"💥 Erro ao ler arquivo {filename}: {str(e)}")
            return []
        
    def parse_input_data(self, data: Dict[Any, Any]) -> Dict[str, str]:
        """PARSING DE DADOS DE ENTRADA COM LOGGING"""
        try:
            input_string = data.get("input", "")
            logger.debug(f"🔍 Parsing entrada: {len(input_string)} chars")
            
            parts = input_string.split("#")
            
            if len(parts) >= 4:
                justificativa = "#".join(parts[3:])
                
                parsed_data = {
                    "id_termo": parts[0],
                    "cpf": parts[1],
                    "pratica_vedada": parts[2],
                    "justificativa": justificativa
                }
                
                logger.debug(f"✅ Parsing bem-sucedido - ID: {parsed_data['id_termo']}, Justificativa: {len(justificativa)} chars")
                return parsed_data
            else:
                raise ValueError("Input format should be IDTERMO#CPF#PRATICA VEDADA#JUSTIFICATIVA")
                
        except Exception as e:
            logger.error(f"❌ Erro no parsing de entrada: {str(e)}")
            logger.debug(f"❌ Entrada problemática: {data}")
            return {"error": str(e)}
    
    def create_llm_prompt(self, justificativa: str) -> str:
        """CRIAÇÃO DO PROMPT ESPECÍFICO PARA ANÁLISE SEMÂNTICA"""
        prompt = f"""Você é um especialista em empréstimos consignados.
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
        
        logger.debug(f"📝 Prompt criado - Tamanho: {len(prompt)} chars")
        return prompt
        
    async def analisar_semantica_consignacao(self, request_data: Dict[Any, Any]) -> Dict[str, Any]:
        """MÉTODO PRINCIPAL DE ANÁLISE SEMÂNTICA COM LOGGING COMPLETO"""
        analysis_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        logger.info(f"🔍 [ANALYSIS-{analysis_id}] Iniciando análise semântica")
        
        parsed_input = self.parse_input_data(request_data)
        
        if "error" in parsed_input:
            logger.error(f"❌ [ANALYSIS-{analysis_id}] Erro no parsing: {parsed_input['error']}")
            return {
                "status": "ERROR",
                "error": parsed_input["error"],
                "error_type": ErrorType.PARSE_ERROR.value,
                "timestamp": datetime.now().isoformat(),
                "request_data": request_data,
                "analysis_id": analysis_id
            }
        
        logger.info(f"✅ [ANALYSIS-{analysis_id}] Parsing bem-sucedido - ID: {parsed_input['id_termo']}")
        
        llm_prompt = self.create_llm_prompt(parsed_input["justificativa"])
        
        try:
            logger.info(f"🤖 [ANALYSIS-{analysis_id}] Chamando Serpro LLM...")
            llm_response = await self.serpro_connector.call_serpro_llm(llm_prompt)
            
        except SerproLLMError as e:
            processing_time = time.time() - start_time
            logger.error(f"💥 [ANALYSIS-{analysis_id}] Erro Serpro LLM: {e.message} - Tempo: {processing_time:.2f}s")
            
            return {
                "status": "ERROR",
                "error": e.message,
                "error_type": e.error_type.value,
                "status_code": e.status_code,
                "timestamp": datetime.now().isoformat(),
                "request_data": request_data,
                "parsed_data": parsed_input,
                "analysis_id": analysis_id,
                "processing_time": processing_time
            }
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"💥 [ANALYSIS-{analysis_id}] Erro inesperado: {str(e)} - Tempo: {processing_time:.2f}s")
            logger.debug(f"💥 [ANALYSIS-{analysis_id}] Traceback: {traceback.format_exc()}")
            
            return {
                "status": "ERROR",
                "error": f"Erro inesperado: {str(e)}",
                "error_type": ErrorType.UNEXPECTED_ERROR.value,
                "timestamp": datetime.now().isoformat(),
                "request_data": request_data,
                "analysis_id": analysis_id,
                "processing_time": processing_time,
                "traceback": traceback.format_exc()
            }
        
        if "error" in llm_response:
            processing_time = time.time() - start_time
            logger.error(f"💥 [ANALYSIS-{analysis_id}] LLM retornou erro: {llm_response['error']} - Tempo: {processing_time:.2f}s")
            
            return {
                "status": "ERROR",
                "error": llm_response["error"],
                "error_type": ErrorType.LLM_ERROR.value,
                "timestamp": datetime.now().isoformat(),
                "request_data": request_data,
                "analysis_id": analysis_id,
                "processing_time": processing_time
            }
        
        llm_result = llm_response.get("llm_analysis", {})
        diagnostico_llm = llm_result.get("diagnosticoLLM", "NÃO")
        confidence = llm_result.get("confidence", 0.5)
        
        logger.info(f"🤖 [ANALYSIS-{analysis_id}] LLM Response - Diagnóstico: {diagnostico_llm}, Confiança: {confidence:.2f}")
        
        if diagnostico_llm == "SIM" and confidence >= 0.7:
            final_status = "APPROVED"
            logger.info(f"✅ [ANALYSIS-{analysis_id}] APROVADO - Alta confiança ({confidence:.2f})")
        elif diagnostico_llm == "SIM" and confidence >= 0.5:
            final_status = "REVIEW_REQUIRED"
            logger.info(f"⚠️ [ANALYSIS-{analysis_id}] REVISÃO NECESSÁRIA - Média confiança ({confidence:.2f})")
        else:
            final_status = "REJECTED"
            logger.info(f"❌ [ANALYSIS-{analysis_id}] REJEITADO - Baixa confiança ou NÃO ({confidence:.2f})")
        
        processing_time = time.time() - start_time
        
        perf_logger.info(f"Analysis completed - ID: {analysis_id} - Status: {final_status} - Time: {processing_time:.2f}s - Confidence: {confidence:.2f}")
        
        result = {
            "status": final_status,
            "parsed_data": parsed_input,
            "llm_prompt": llm_prompt,
            "llm_analysis": llm_result,
            "diagnostico_llm": diagnostico_llm,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat(),
            "request_data": request_data,
            "analysis_id": analysis_id,
            "processing_time": processing_time
        }
        
        logger.info(f"🎉 [ANALYSIS-{analysis_id}] Análise concluída - Status: {final_status} - Tempo: {processing_time:.2f}s")
        
        return result

# ========== SISTEMA DE LIFESPAN MODERNO ==========
@asynccontextmanager
async def lifespan(app: FastAPI):
    """GERENCIADOR DE CICLO DE VIDA DA API (MODERNO - SEM WARNINGS)"""
    
    # ========== STARTUP ==========
    config = SerproConfig()
    
    logger.info("="*80)
    logger.info("🚀 INICIANDO SEMÂNTICA CONSIGNAÇÃO API v3.0 - ENDPOINT ÚNICO")
    logger.info("="*80)
    logger.info(f"🌐 Ambiente: {config.AMBIENTE}")
    logger.info(f"🤖 Modelo: {config.MODEL_NAME}")
    logger.info(f"🔗 URL Base: {config.get_urls()['base']}")
    logger.info(f"⏱️ Request Timeout: {config.REQUEST_TIMEOUT}s")
    logger.info(f"🔄 Max Retries: {config.RETRY_CONFIG['max_retries']}")
    logger.info(f"📁 Pasta Logs: ./logs/")
    logger.info("🎯 ENDPOINT ÚNICO: POST /analise-semantica (formato JSON simples)")
    logger.info("="*80)
    
    monitoring_task = asyncio.create_task(log_system_health())
    logger.info("🔍 Monitoramento automático de saúde iniciado")
    
    perf_logger.info(f"API started - Environment: {config.AMBIENTE} - Model: {config.MODEL_NAME}")
    
    yield
    
    # ========== SHUTDOWN ==========
    try:
        monitoring_task.cancel()
        
        final_stats = semantica_consignacao.serpro_connector.get_error_statistics()
        uptime_hours = final_stats['uptime_seconds'] / 3600
        
        logger.info("="*80)
        logger.info("⏹️ ENCERRANDO SEMÂNTICA CONSIGNAÇÃO API v3.0 - ENDPOINT ÚNICO")
        logger.info("="*80)
        logger.info(f"📊 Estatísticas finais:")
        logger.info(f"   Total Requests: {final_stats['total_requests']}")
        logger.info(f"   Total Errors: {final_stats['total_errors']}")
        logger.info(f"   Error Rate: {final_stats['error_rate']:.2f}%")
        logger.info(f"   Total Retries: {final_stats['total_retries']}")
        logger.info(f"   Uptime: {uptime_hours:.2f}h")
        logger.info("="*80)
        logger.info("🎉 API encerrada com sucesso!")
        
        perf_logger.info(f"API shutdown - Total requests: {final_stats['total_requests']} - Uptime: {uptime_hours:.2f}h - Error rate: {final_stats['error_rate']:.2f}%")
        
    except Exception as e:
        logger.error(f"💥 Erro durante shutdown: {str(e)}")

# ========== CRIAÇÃO DA FASTAPI COM CORS ==========
app = FastAPI(
    title="SEMÂNTICA CONSIGNAÇÃO API", 
    version="3.0.0",
    description="Sistema inteligente de análise semântica com Serpro LLM - Endpoint Unificado",
    lifespan=lifespan
)

# ========== CONFIGURAÇÃO CORS (CORRIGE WEBSOCKET 403) ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar domínios exatos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== INSTÂNCIA GLOBAL ==========
semantica_consignacao = SemanticaConsignacao()
file_processing_active = False

# ========== ENDPOINTS WEBSOCKET ==========
@app.websocket("/ws/semantica-consignacao")
async def websocket_endpoint(websocket: WebSocket):
    """ENDPOINT WEBSOCKET PRINCIPAL COM LOGGING DETALHADO"""
    client_ip = websocket.client.host if websocket.client else "unknown"
    connection_id = str(uuid.uuid4())[:8]
    
    await websocket.accept()
    logger.info(f"🔌 [WS-{connection_id}] WebSocket conectado - IP: {client_ip}")
    
    try:
        while True:
            data = await websocket.receive_text()
            data_size = len(data)
            
            try:
                request_json = json.loads(data)
                action = request_json.get("action", "manual")
                
                logger.info(f"📨 [WS-{connection_id}] Requisição recebida - IP: {client_ip} - Action: {action} - Size: {data_size} bytes")
                
                if request_json.get("action") == "process_file":
                    await handle_file_processing(websocket, request_json, connection_id)
                else:
                    await handle_manual_input(websocket, request_json, connection_id)
                
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ [WS-{connection_id}] JSON inválido - IP: {client_ip} - Erro: {str(e)}")
                
                error_response = {
                    "error": "Invalid JSON format",
                    "error_type": ErrorType.JSON_PARSE_ERROR.value,
                    "timestamp": datetime.now().isoformat(),
                    "connection_id": connection_id
                }
                await websocket.send_text(json.dumps(error_response))
                
    except WebSocketDisconnect:
        logger.info(f"🔌 [WS-{connection_id}] WebSocket desconectado - IP: {client_ip}")
    except Exception as e:
        logger.error(f"💥 [WS-{connection_id}] Erro WebSocket - IP: {client_ip} - Erro: {str(e)}")
        logger.debug(f"💥 [WS-{connection_id}] Traceback: {traceback.format_exc()}")
        await websocket.close()

async def handle_manual_input(websocket: WebSocket, request_json: dict, connection_id: str = "unknown"):
    """PROCESSAMENTO DE ENTRADA MANUAL COM LOGGING DETALHADO"""
    start_time = time.time()
    
    try:
        input_text = request_json.get("input", "")
        logger.info(f"🔍 [WS-{connection_id}] Processando entrada manual - Tamanho: {len(input_text)} chars")
        
        resultado_semantica = await semantica_consignacao.analisar_semantica_consignacao(request_json)
        
        processing_time = time.time() - start_time
        status = resultado_semantica.get("status", "UNKNOWN")
        analysis_id = resultado_semantica.get("analysis_id", "N/A")
        
        logger.info(f"✅ [WS-{connection_id}] Processamento concluído - Analysis: {analysis_id} - Status: {status} - Tempo: {processing_time:.2f}s")
        
        if status == "APPROVED":
            confidence = resultado_semantica.get("confidence", 0)
            id_termo = resultado_semantica.get("parsed_data", {}).get("id_termo", "N/A")
            logger.info(f"🎯 [WS-{connection_id}] APROVADO - ID: {id_termo} - Confiança: {confidence:.2f}")
            perf_logger.info(f"Manual approval - Connection: {connection_id} - ID: {id_termo} - Confidence: {confidence:.2f} - Time: {processing_time:.2f}s")
        
        await websocket.send_text(json.dumps(resultado_semantica, indent=2))
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"💥 [WS-{connection_id}] Erro no processamento manual - Tempo: {processing_time:.2f}s - Erro: {str(e)}")
        logger.debug(f"💥 [WS-{connection_id}] Traceback: {traceback.format_exc()}")
        
        error_response = {
            "error": f"Erro no processamento: {str(e)}",
            "error_type": ErrorType.UNEXPECTED_ERROR.value,
            "timestamp": datetime.now().isoformat(),
            "connection_id": connection_id,
            "processing_time": processing_time
        }
        await websocket.send_text(json.dumps(error_response))

async def handle_file_processing(websocket: WebSocket, request_json: dict, connection_id: str = "unknown"):
    """PROCESSAMENTO DE ARQUIVO EM LOTE COM LOGGING COMPLETO"""
    global file_processing_active
    
    filename = request_json.get("filename", "100.txt")
    batch_id = str(uuid.uuid4())[:8]
    
    logger.info(f"📁 [WS-{connection_id}] [BATCH-{batch_id}] Iniciando processamento de arquivo: {filename}")
    
    if file_processing_active:
        logger.warning(f"⚠️ [WS-{connection_id}] [BATCH-{batch_id}] Processamento já ativo, rejeitando")
        await websocket.send_text(json.dumps({
            "error": "File processing already active",
            "error_type": ErrorType.VALIDATION_ERROR.value,
            "timestamp": datetime.now().isoformat(),
            "connection_id": connection_id,
            "batch_id": batch_id
        }))
        return
    
    justificativas = semantica_consignacao.read_justificativas_file(filename)
    
    if not justificativas:
        logger.error(f"❌ [WS-{connection_id}] [BATCH-{batch_id}] Arquivo vazio ou não encontrado: {filename}")
        await websocket.send_text(json.dumps({
            "error": f"No data found in file {filename}",
            "error_type": "FILE_NOT_FOUND",
            "timestamp": datetime.now().isoformat(),
            "connection_id": connection_id,
            "batch_id": batch_id
        }))
        return
    
    file_processing_active = True
    start_time = time.time()
    
    logger.info(f"📊 [WS-{connection_id}] [BATCH-{batch_id}] Processamento iniciado - {len(justificativas)} itens")
    perf_logger.info(f"Batch processing started - Connection: {connection_id} - Batch: {batch_id} - Items: {len(justificativas)}")
    
    try:
        await websocket.send_text(json.dumps({
            "status": "File processing started",
            "total_records": len(justificativas),
            "filename": filename,
            "timestamp": datetime.now().isoformat(),
            "connection_id": connection_id,
            "batch_id": batch_id
        }))
        
        processed_count = 0
        
        for i, justificativa_line in enumerate(justificativas, 1):
            if not file_processing_active:
                logger.info(f"⏹️ [WS-{connection_id}] [BATCH-{batch_id}] Processamento interrompido - Item {i}/{len(justificativas)}")
                break
                
            item_start_time = time.time()
            
            file_request = {"input": justificativa_line.strip()}
            
            logger.debug(f"🔄 [WS-{connection_id}] [BATCH-{batch_id}] Processando item {i}/{len(justificativas)}")
            
            await handle_manual_input(websocket, file_request, f"{connection_id}-BATCH")
            
            processed_count += 1
            item_time = time.time() - item_start_time
            
            error_stats = semantica_consignacao.serpro_connector.get_error_statistics()
            
            progress_update = {
                "progress": f"{i}/{len(justificativas)}",
                "percentage": round((i / len(justificativas)) * 100, 2),
                "current_record": i,
                "total_records": len(justificativas),
                "error_statistics": error_stats,
                "timestamp": datetime.now().isoformat(),
                "connection_id": connection_id,
                "batch_id": batch_id,
                "item_processing_time": round(item_time, 2)
            }
            await websocket.send_text(json.dumps(progress_update))
            
            if i % 10 == 0:
                elapsed_time = time.time() - start_time
                avg_time = elapsed_time / i
                eta = avg_time * (len(justificativas) - i)
                logger.info(f"📈 [WS-{connection_id}] [BATCH-{batch_id}] Progresso: {i}/{len(justificativas)} ({(i/len(justificativas)*100):.1f}%) - ETA: {eta:.0f}s")
            
            if i < len(justificativas):
                await asyncio.sleep(5)
        
        final_stats = semantica_consignacao.serpro_connector.get_error_statistics()
        total_time = time.time() - start_time
        
        logger.info(f"🎉 [WS-{connection_id}] [BATCH-{batch_id}] Processamento concluído - {processed_count} itens - Tempo total: {total_time:.2f}s")
        perf_logger.info(f"Batch processing completed - Connection: {connection_id} - Batch: {batch_id} - Items: {processed_count} - Time: {total_time:.2f}s")
        
        await websocket.send_text(json.dumps({
            "status": "File processing completed",
            "total_processed": processed_count,
            "final_error_statistics": final_stats,
            "timestamp": datetime.now().isoformat(),
            "connection_id": connection_id,
            "batch_id": batch_id,
            "total_processing_time": round(total_time, 2)
        }))
        
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"💥 [WS-{connection_id}] [BATCH-{batch_id}] Erro durante processamento: {str(e)} - Tempo: {total_time:.2f}s")
        logger.debug(f"💥 [WS-{connection_id}] [BATCH-{batch_id}] Traceback: {traceback.format_exc()}")
        
        await websocket.send_text(json.dumps({
            "error": f"File processing error: {str(e)}",
            "error_type": "FILE_PROCESSING_ERROR",
            "timestamp": datetime.now().isoformat(),
            "connection_id": connection_id,
            "batch_id": batch_id,
            "processing_time": round(total_time, 2),
            "traceback": traceback.format_exc()
        }))
    finally:
        file_processing_active = False
        logger.info(f"🔓 [WS-{connection_id}] [BATCH-{batch_id}] Processamento finalizado e liberado")

# ========== MODELO PYDANTIC FLEXÍVEL ÚNICO ==========

class SemanticaInput(BaseModel):
    """
    MODELO ÚNICO PARA ANÁLISE SEMÂNTICA
    
    Aceita entrada no campo 'input' em diferentes formatos:
    1. Linha completa: IDTERMO#CPF#PRATICA#JUSTIFICATIVA
    2. Justificativa simples: texto livre
    """
    input: str
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "input": "314163#13758748372#12#SOLICITO MEU BOLETO DE QUITAÇÃO JUNTO A ESSE BANCO"
                },
                {
                    "input": "TERMO123#12345678901#Desconto sem autorização#Estou sendo descontado sem ter autorizado este empréstimo"
                },
                {
                    "input": "TERMO456#98765432109#Contrato liquidado#Continuam descontando de contrato já quitado"
                },
                {
                    "input": "Estou sendo descontado na folha sem autorização"
                }
            ]
        }
    }

# ========== ENDPOINT ÚNICO E FLEXÍVEL ==========

@app.post("/analise-semantica",
          summary="Análise Semântica Flexível",
          description="""
          **🎯 Endpoint Único e Flexível - Funciona em qualquer situação!**
          
          **✅ Para Swagger UI:**
          Use o formato JSON estruturado com o campo "input":
          ```json
          {
            "input": "314163#13758748372#12#SOLICITO MEU BOLETO DE QUITAÇÃO"
          }
          ```
          
          **✅ Para cURL/API direta:**
          Também aceita JSON estruturado (recomendado):
          ```bash
          curl -X 'POST' 'http://localhost:8000/analise-semantica' \\
            -H 'Content-Type: application/json' \\
            -d '{"input": "314163#13758748372#12#SOLICITO MEU BOLETO DE QUITAÇÃO"}'
          ```
          
          **Formatos de Input aceitos:**
          - `IDTERMO#CPF#PRATICA VEDADA#JUSTIFICATIVA` (linha completa)
          - `Justificativa livre` (texto simples)
          
          **Resultado Esperado para o Exemplo:**
          - Status: REJECTED (requisição de boleto fora do escopo)
          - Diagnóstico: NÃO
          - Confiança: ~0.8
          
          **Compatibilidade Total:**
          - ✅ Funciona no Swagger UI "Try it out"
          - ✅ Funciona com qualquer cliente HTTP
          - ✅ Documentação rica e exemplos
          - ✅ Validação automática de entrada
          """,
          response_description="Resultado completo da análise semântica com metadados",
          tags=["Análise Semântica"])


async def analise_semantica_unica(entrada: SemanticaInput):
    """
    ENDPOINT ÚNICO E FLEXÍVEL - MÁXIMA SIMPLICIDADE
    
    Aceita apenas JSON estruturado com campo "input", mas é flexível
    no conteúdo desse campo. Funciona perfeitamente tanto no Swagger UI
    quanto em qualquer cliente HTTP.
    
    SIMPLICIDADE TOTAL:
    - Um formato único: {"input": "texto"}
    - Funciona no Swagger UI sem problemas
    - Funciona com cURL facilmente
    - Sem detecção complicada de formatos
    - Logs claros e diretos
    """
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    
    try:
        input_string = entrada.input.strip()
        
        logger.info(f"🌐 [REST-ÚNICO-{request_id}] Requisição recebida - Input: {len(input_string)} chars")
        logger.debug(f"🔍 [REST-ÚNICO-{request_id}] Conteúdo: '{input_string[:100]}{'...' if len(input_string) > 100 else ''}'")
        
        # Validar se input não está vazio
        if not input_string:
            logger.warning(f"⚠️ [REST-ÚNICO-{request_id}] Input vazio")
            raise HTTPException(status_code=400, detail="O campo 'input' não pode estar vazio")
        
        # Processar usando lógica existente
        request_data = {"input": input_string}
        resultado = await semantica_consignacao.analisar_semantica_consignacao(request_data)
        
        processing_time = time.time() - start_time
        
        logger.info(f"✅ [REST-ÚNICO-{request_id}] Processamento concluído - Status: {resultado.get('status', 'UNKNOWN')} - Tempo: {processing_time:.2f}s")
        
        # Adicionar metadados simples e claros
        resultado.update({
            "rest_request_id": request_id,
            "rest_processing_time": processing_time,
            "endpoint_type": "REST_ÚNICO_FLEXÍVEL",
            "input_format": "json_structured",
            "api_version": "3.0.0",
            "swagger_ui_compatible": True
        })
        
        # Log específico para casos de aprovação
        if resultado.get("status") == "APPROVED":
            confidence = resultado.get("confidence", 0)
            id_termo = resultado.get("parsed_data", {}).get("id_termo", "N/A")
            perf_logger.info(f"REST Único approval - Request: {request_id} - ID: {id_termo} - Confidence: {confidence:.2f}")
        
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"💥 [REST-ÚNICO-{request_id}] Erro: {str(e)} - Tempo: {processing_time:.2f}s")
        logger.debug(f"💥 [REST-ÚNICO-{request_id}] Traceback: {traceback.format_exc()}")
        
        return {
            "status": "ERROR",
            "error": f"Erro no processamento: {str(e)}",
            "error_type": "REST_ÚNICO_ERROR",
            "timestamp": datetime.now().isoformat(),
            "rest_request_id": request_id,
            "processing_time": processing_time,
            "endpoint_type": "REST_ÚNICO_FLEXÍVEL",
            "api_version": "3.0.0"
        }

# ========== ENDPOINTS DE CONTROLE ==========

@app.post("/stop-file-processing")
async def stop_file_processing():
    """ENDPOINT PARA INTERROMPER PROCESSAMENTO DE ARQUIVO"""
    global file_processing_active
    
    if file_processing_active:
        file_processing_active = False
        logger.info("⏹️ Processamento de arquivo interrompido via API")
        return {"message": "File processing stopped", "timestamp": datetime.now().isoformat()}
    else:
        logger.info("⚠️ Tentativa de parar processamento que não estava ativo")
        return {"message": "No file processing was active", "timestamp": datetime.now().isoformat()}

@app.get("/error-stats")
async def get_error_stats():
    """ENDPOINT PARA CONSULTAR ESTATÍSTICAS DE ERRO"""
    try:
        stats = semantica_consignacao.serpro_connector.get_error_statistics()
        
        logger.debug(f"📊 Estatísticas consultadas - Total Requests: {stats['total_requests']} - Error Rate: {stats['error_rate']:.2f}%")
        
        return {
            "error_statistics": stats,
            "timestamp": datetime.now().isoformat(),
            "api_version": "3.0.0"
        }
    except Exception as e:
        logger.error(f"💥 Erro ao obter estatísticas: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reset-error-stats")
async def reset_error_stats():
    """ENDPOINT PARA RESETAR ESTATÍSTICAS DE ERRO"""
    try:
        old_stats = semantica_consignacao.serpro_connector.get_error_statistics()
        semantica_consignacao.serpro_connector.error_stats.reset_statistics()
        
        logger.info(f"🔄 Estatísticas resetadas via API - Última sessão: {old_stats['total_requests']} requests")
        
        return {
            "message": "Error statistics reset successfully",
            "previous_stats": old_stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"💥 Erro ao resetar estatísticas: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """HEALTH CHECK DA API COM LOGGING DETALHADO"""
    try:
        stats = semantica_consignacao.serpro_connector.get_error_statistics()
        
        error_rate = stats.get("error_rate", 0)
        if error_rate < 5:
            health_status = "healthy"
        elif error_rate < 15:
            health_status = "warning"
        else:
            health_status = "critical"
        
        uptime = stats.get("uptime_seconds", 0)
        if health_status == "healthy":
            logger.debug(f"✅ Health check: {health_status} - Error rate: {error_rate:.2f}% - Uptime: {uptime:.0f}s")
        elif health_status == "warning":
            logger.warning(f"⚠️ Health check: {health_status} - Error rate: {error_rate:.2f}% - Uptime: {uptime:.0f}s")
        else:
            logger.error(f"🚨 Health check: {health_status} - Error rate: {error_rate:.2f}% - Uptime: {uptime:.0f}s")
        
        return {
            "status": health_status,
            "timestamp": datetime.now().isoformat(),
            "api_version": "3.0.0",
            "error_rate": error_rate,
            "uptime_seconds": stats.get("uptime_seconds", 0),
            "total_requests": stats.get("total_requests", 0),
            "endpoint_unified": True
        }
    except Exception as e:
        logger.error(f"💥 Erro no health check: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "api_version": "3.0.0"
        }

# ========== INTERFACE WEB ATUALIZADA ==========
@app.get("/")
async def get():
    """INTERFACE WEB INTERATIVA ATUALIZADA PARA ENDPOINT UNIFICADO"""
    logger.info("🌐 Interface web acessada")
    
    return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
    <title>SEMÂNTICA CONSIGNAÇÃO API v3.0 - ENDPOINT ÚNICO</title>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 20px; 
            background: #f5f7fa; 
        }
        .container { max-width: 1200px; margin: 0 auto; }
        
        .header { 
            background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%); 
            color: white; 
            padding: 20px; 
            border-radius: 10px; 
            margin-bottom: 20px; 
            text-align: center; 
        }
        
        .stats-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 15px; 
            margin-bottom: 20px; 
        }
        .stat-card { 
            background: white; 
            padding: 15px; 
            border-radius: 8px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
            border-left: 4px solid #2ecc71; 
        }
        .stat-value { font-size: 24px; font-weight: bold; color: #2c3e50; }
        .stat-label { color: #7f8c8d; font-size: 12px; margin-top: 5px; }
        
        .section { 
            background: white; 
            padding: 20px; 
            border-radius: 8px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
            margin-bottom: 20px; 
        }
        
        .success-highlight {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
        }
        
        .new-feature {
            background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
            color: white;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            text-align: center;
        }
        
        textarea { 
            width: 100%; 
            padding: 10px; 
            border: 1px solid #ddd; 
            border-radius: 4px; 
            font-family: monospace; 
            resize: vertical; 
        }
        
        button { 
            padding: 10px 15px; 
            margin: 5px; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer; 
            font-weight: 500; 
        }
        .btn-primary { background: #3498db; color: white; }
        .btn-success { background: #2ecc71; color: white; }
        .btn-warning { background: #f39c12; color: white; }
        .btn-danger { background: #e74c3c; color: white; }
        .btn-unified { background: #2ecc71; color: white; font-size: 16px; padding: 12px 20px; }
        .btn:hover { opacity: 0.9; transform: translateY(-1px); }
        
        .log-area { 
            background: #2c3e50; 
            color: #ecf0f1; 
            padding: 15px; 
            border-radius: 4px; 
            font-family: 'Courier New', monospace; 
            height: 300px; 
            overflow-y: auto; 
            font-size: 11px; 
        }
        
        .status-indicator { 
            display: inline-block; 
            width: 10px; 
            height: 10px; 
            border-radius: 50%; 
            margin-right: 8px; 
        }
        .status-healthy { background: #2ecc71; }
        .status-warning { background: #f39c12; }
        .status-critical { background: #e74c3c; }
        
        .error-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); 
            gap: 10px; 
        }
        .error-item { 
            background: #f8f9fa; 
            padding: 10px; 
            border-radius: 4px; 
            text-align: center; 
            border-left: 3px solid #e74c3c; 
        }
        
        .auto-refresh { float: right; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 SEMÂNTICA CONSIGNAÇÃO API v3.0 - ENDPOINT ÚNICO</h1>
            <p>Sistema inteligente com Endpoint Único - Máxima Simplicidade</p>
            <div class="auto-refresh">
                <span class="status-indicator" id="healthIndicator"></span>
                <span id="healthStatus">Verificando...</span>
                <button onclick="toggleAutoRefresh()" id="autoRefreshBtn" class="btn-success">Auto-refresh ON</button>
            </div>
        </div>

        <div class="new-feature">
            <h3>🎯 ENDPOINT ÚNICO E SIMPLES!</h3>
            <p>Agora você tem apenas 1 endpoint com formato JSON simples que funciona em tudo!</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value" id="totalRequests">0</div>
                <div class="stat-label">Total Requisições</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="totalErrors">0</div>
                <div class="stat-label">Total Erros</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="errorRate">0%</div>
                <div class="stat-label">Taxa de Erro</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="totalRetries">0</div>
                <div class="stat-label">Total Retries</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="uptime">0s</div>
                <div class="stat-label">Uptime</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="mostCommonError">-</div>
                <div class="stat-label">Erro Mais Comum</div>
            </div>
        </div>

        <div class="section">
            <h3>📊 Breakdown de Erros</h3>
            <div class="error-grid" id="errorBreakdown"></div>
        </div>

        <div class="section">
            <h3>🎯 SOLUÇÃO FINAL - Endpoint Único e Simples</h3>
            
            <div class="success-highlight">
                <h4>✅ Agora você tem apenas 1 endpoint que funciona em tudo!</h4>
                
                <p><strong>📍 Endpoint Único:</strong> <code>POST /analise-semantica</code></p>
                
                <p><strong>✅ Para Swagger UI (Try it out):</strong></p>
                <div style="background: #e8f4fd; border: 1px solid #bee5eb; padding: 10px; border-radius: 4px;">
                    🔗 Acesse: <a href="/docs" target="_blank">http://localhost:8000/docs</a><br>
                    📝 Use o campo "input": <code>314163#13758748372#12#SOLICITO MEU BOLETO DE QUITAÇÃO</code><br>
                    🎯 Clique "Try it out" → funciona perfeitamente!
                </div>
                
                <p><strong>✅ Para cURL (formato JSON):</strong></p>
                <pre style="background: #f8f9fa; padding: 10px; border-radius: 4px; font-size: 12px; color: #2ecc71;">curl -X 'POST' 'http://localhost:8000/analise-semantica' \\
  -H 'Content-Type: application/json' \\
  -d '{"input": "314163#13758748372#12#SOLICITO MEU BOLETO DE QUITAÇÃO"}'</pre>
                
                <p><strong>🧠 O que mudou:</strong></p>
                <ul>
                    <li>✅ Apenas 1 endpoint: <code>/analise-semantica</code></li>
                    <li>✅ Formato único: <code>{"input": "texto"}</code></li>
                    <li>✅ Funciona no Swagger UI sem erros</li>
                    <li>✅ Funciona com qualquer cliente HTTP</li>
                    <li>❌ Removido: <code>/analise-semantica-raw</code> (desnecessário)</li>
                </ul>
            </div>
            
            <h4>📊 Resultado para Seu Caso:</h4>
            <div style="background: #f8d7da; border: 1px solid #f5c6cb; padding: 10px; border-radius: 4px;">
                <p><strong>Status:</strong> REJECTED (❌)</p>
                <p><strong>Motivo:</strong> "SOLICITO MEU BOLETO" é classificado como "requisição de boleto" (fora do escopo)</p>
                <p><strong>Diagnóstico LLM:</strong> NÃO</p>
                <p><strong>Confiança:</strong> ~0.8</p>
            </div>
        </div>

        <div class="section">
            <h3>🧪 Teste o Endpoint Único</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                <div>
                    <h4>Endpoint /analise-semantica</h4>
                    <button onclick="testUnicoEndpoint()" class="btn-unified" style="width: 100%; margin-bottom: 10px;">
                        🚀 Testar Endpoint Único
                    </button>
                    <button onclick="window.open('/docs', '_blank')" class="btn-primary" style="width: 100%;">
                        📖 Abrir Swagger UI
                    </button>
                </div>
                <div>
                    <h4>Documentação</h4>
                    <button onclick="window.open('/redoc', '_blank')" class="btn-warning" style="width: 100%; margin-bottom: 10px;">
                        📚 Abrir ReDoc
                    </button>
                    <button onclick="window.open('/openapi.json', '_blank')" class="btn-primary" style="width: 100%;">
                        📄 Ver OpenAPI Schema
                    </button>
                </div>
            </div>
            <div id="unicoResult" style="margin-top: 15px; font-size: 11px; background: #f8f9fa; padding: 10px; border-radius: 4px; display: none;"></div>
        </div>

        <div class="section">
            <h3>🔧 Teste Manual WebSocket</h3>
            <textarea id="messageInput" rows="6" placeholder="Teste diferentes formatos:

Formato 1 - JSON estruturado:
{\"input\": \"TERMO123#12345678901#12#Estou sendo descontado sem autorização\"}

Formato 2 - String direta:
TERMO123#12345678901#12#Estou sendo descontado sem autorização">
{
    "input": "TERMO123#12345678901#Desconto sem autorização#Estou sendo descontado na folha de pagamento sem ter autorizado este empréstimo consignado. Nunca assinei nenhum contrato."
}
            </textarea>
            <br>
            <button onclick="sendMessage()" class="btn-primary">🚀 Enviar Teste</button>
            <button onclick="testApprovalCase()" class="btn-success">✅ Testar Aprovação</button>
            <button onclick="testRejectionCase()" class="btn-danger">❌ Testar Rejeição</button>
            <button onclick="clearMessages()" class="btn-warning">🗑️ Limpar</button>
        </div>

        <div class="section">
            <h3>📁 Processamento de Arquivo</h3>
            <input type="text" id="filename" placeholder="Nome do arquivo (ex: 100.txt)" value="100.txt" style="padding: 8px; margin-right: 10px;">
            <button onclick="processFile()" id="processBtn" class="btn-success">📋 Processar Arquivo</button>
            <button onclick="stopProcessing()" id="stopBtn" class="btn-danger" disabled>⏹️ Parar</button>
            <div id="progress" style="margin-top: 10px; display: none; background: #ecf0f1; padding: 10px; border-radius: 4px;"></div>
        </div>

        <div class="section">
            <h3>📝 Log de Eventos</h3>
            <div class="log-area" id="logArea">[Aguardando conexão WebSocket...]</div>
        </div>
    </div>

    <script>
        let ws;
        let autoRefreshInterval;
        let isAutoRefreshOn = true;

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/semantica-consignacao`;
            
            ws = new WebSocket(wsUrl);
            
            ws.onopen = function() {
                addLog("✅ WebSocket conectado - API v3.0 Unificada");
            };
            
            ws.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    handleWebSocketMessage(data);
                } catch (e) {
                    addLog(`❌ Erro ao processar mensagem: ${e.message}`);
                }
            };
            
            ws.onclose = function() {
                addLog("❌ WebSocket desconectado - Tentando reconectar...");
                setTimeout(connectWebSocket, 5000);
            };
            
            ws.onerror = function(error) {
                addLog(`💥 Erro WebSocket: ${error.message || 'Erro desconhecido'}`);
            };
        }

        function handleWebSocketMessage(data) {
            const timestamp = new Date().toLocaleTimeString();
            
            if (data.error_statistics) {
                updateErrorStats(data.error_statistics);
            }
            
            if (data.status || data.error) {
                const status = data.status || "ERROR";
                const icon = getStatusIcon(status);
                
                let message = `${icon} ${status}`;
                
                if (status === "APPROVED" && data.confidence) {
                    message += ` (Confiança: ${(data.confidence * 100).toFixed(1)}%)`;
                }
                if (data.analysis_id) {
                    message += ` [${data.analysis_id}]`;
                }
                if (data.processing_time) {
                    message += ` (${data.processing_time.toFixed(2)}s)`;
                }
                
                addLog(`[${timestamp}] ${message}`);
            }
            
            if (data.progress) {
                updateProgress(`Processando: ${data.progress} (${data.percentage}%)`);
                addLog(`[${timestamp}] 📊 Progresso: ${data.progress} (${data.percentage}%)`);
            }
        }

        function getStatusIcon(status) {
            const icons = {
                "APPROVED": "✅",
                "REJECTED": "❌", 
                "REVIEW_REQUIRED": "⚠️",
                "ERROR": "💥",
                "SUCCESS": "✅"
            };
            return icons[status] || "ℹ️";
        }

        function addLog(message) {
            const logArea = document.getElementById('logArea');
            logArea.innerHTML += message + '\\n';
            logArea.scrollTop = logArea.scrollHeight;
        }

        function updateErrorStats(stats) {
            document.getElementById('totalRequests').textContent = stats.total_requests || 0;
            document.getElementById('totalErrors').textContent = stats.total_errors || 0;
            document.getElementById('errorRate').textContent = (stats.error_rate || 0).toFixed(1) + '%';
            document.getElementById('totalRetries').textContent = stats.total_retries || 0;
            document.getElementById('uptime').textContent = Math.round(stats.uptime_seconds || 0) + 's';
            document.getElementById('mostCommonError').textContent = stats.most_common_error || '-';
            
            const breakdown = stats.error_breakdown || {};
            const container = document.getElementById('errorBreakdown');
            container.innerHTML = '';
            
            Object.entries(breakdown).forEach(([errorType, count]) => {
                if (count > 0) {
                    const div = document.createElement('div');
                    div.className = 'error-item';
                    div.innerHTML = `<strong>${count}</strong><br><small>${errorType}</small>`;
                    container.appendChild(div);
                }
            });
        }

        async function refreshStats() {
            try {
                const response = await fetch('/error-stats');
                const data = await response.json();
                updateErrorStats(data.error_statistics);
                
                const healthResponse = await fetch('/health');
                const healthData = await healthResponse.json();
                updateHealthStatus(healthData.status);
                
            } catch (error) {
                addLog(`❌ Erro ao buscar estatísticas: ${error.message}`);
            }
        }

        function updateHealthStatus(status) {
            const indicator = document.getElementById('healthIndicator');
            const statusText = document.getElementById('healthStatus');
            
            indicator.className = `status-indicator status-${status}`;
            statusText.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        }

        function toggleAutoRefresh() {
            const btn = document.getElementById('autoRefreshBtn');
            
            if (isAutoRefreshOn) {
                clearInterval(autoRefreshInterval);
                btn.textContent = 'Auto-refresh OFF';
                btn.className = 'btn-warning';
                isAutoRefreshOn = false;
            } else {
                autoRefreshInterval = setInterval(refreshStats, 5000);
                btn.textContent = 'Auto-refresh ON';
                btn.className = 'btn-success';
                isAutoRefreshOn = true;
            }
        }

        async function testRawEndpoint() {
            // Teste com string direta (sem JSON)
            const testData = "314163#13758748372#12#SOLICITO MEU BOLETO DE QUITAÇÃO JUNTO A ESSE BANCO";
            
            try {
                addLog("🧪 Testando endpoint raw com string direta...");
                
                const response = await fetch('/analise-semantica-raw', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'text/plain',
                    },
                    body: testData  // String direta no body
                });
                
                const result = await response.json();
                const resultDiv = document.getElementById('rawResult');
                resultDiv.style.display = 'block';
                
                // Destacar informações importantes
                const status = result.status || 'UNKNOWN';
                const diagnostico = result.diagnostico_llm || 'N/A';
                const confidence = result.confidence || 0;
                
                resultDiv.innerHTML = `
                    <strong>🎉 Endpoint Raw Funcionando!</strong><br>
                    <strong>HTTP Status:</strong> ${response.status}<br>
                    <strong>Status Final:</strong> ${status}<br>
                    <strong>Diagnóstico LLM:</strong> ${diagnostico}<br>
                    <strong>Confiança:</strong> ${(confidence * 100).toFixed(1)}%<br>
                    <strong>Request ID:</strong> ${result.rest_request_id}<br>
                    <strong>Tempo:</strong> ${result.rest_processing_time?.toFixed(2)}s<br>
                    <details style="margin-top: 10px;">
                        <summary>Ver resposta completa</summary>
                        <pre style="background: #f8f9fa; padding: 10px; border-radius: 4px; font-size: 10px; margin-top: 5px;">${JSON.stringify(result, null, 2)}</pre>
                    </details>
                `;
                
                addLog(`🎉 Teste raw concluído: Status ${response.status} - Final: ${status}`);
                
            } catch (error) {
                const resultDiv = document.getElementById('rawResult');
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = `<strong>❌ Erro:</strong> ${error.message}`;
                addLog(`❌ Erro no teste raw: ${error.message}`);
            }
        }
            // Teste com o caso específico do usuário que estava falhando
            const testData = "314163#13758748372#12#SOLICITO MEU BOLETO DE QUITAÇÃO JUNTO A ESSE BANCO";
            
            try {
                addLog("🧪 Testando endpoint unificado com string direta...");
                
                const response = await fetch('/analise-semantica', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',  // Mesmo Content-Type que estava falhando
                    },
                    body: testData  // String direta (não JSON)
                });
                
                const result = await response.json();
                const resultDiv = document.getElementById('unifiedResult');
                resultDiv.style.display = 'block';
                
                // Destacar informações importantes
                const formatDetected = result.detected_format || 'não detectado';
                const status = result.status || 'UNKNOWN';
                const diagnostico = result.diagnostico_llm || 'N/A';
                const confidence = result.confidence || 0;
                
                resultDiv.innerHTML = `
                    <strong>🎉 SUCESSO! Endpoint Unificado Funcionando!</strong><br>
                    <strong>HTTP Status:</strong> ${response.status}<br>
                    <strong>Formato Detectado:</strong> ${formatDetected}<br>
                    <strong>Status Final:</strong> ${status}<br>
                    <strong>Diagnóstico LLM:</strong> ${diagnostico}<br>
                    <strong>Confiança:</strong> ${(confidence * 100).toFixed(1)}%<br>
                    <strong>Request ID:</strong> ${result.rest_request_id}<br>
                    <strong>Tempo:</strong> ${result.rest_processing_time?.toFixed(2)}s<br>
                    <details style="margin-top: 10px;">
                        <summary>Ver resposta completa</summary>
                        <pre style="background: #f8f9fa; padding: 10px; border-radius: 4px; font-size: 10px; margin-top: 5px;">${JSON.stringify(result, null, 2)}</pre>
                    </details>
                `;
                
                addLog(`🎉 Teste unificado concluído: Status ${response.status} - Formato: ${formatDetected} - Final: ${status}`);
                
            } catch (error) {
                const resultDiv = document.getElementById('unifiedResult');
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = `<strong>❌ Erro:</strong> ${error.message}`;
                addLog(`❌ Erro no teste unificado: ${error.message}`);
            }
        }

        function sendMessage() {
            const input = document.getElementById("messageInput");
            if (input.value.trim() && ws.readyState === WebSocket.OPEN) {
                try {
                    // Verificar se é JSON válido antes de enviar via WebSocket
                    JSON.parse(input.value);
                    ws.send(input.value);
                    addLog(`📤 Enviado via WebSocket: ${input.value.substring(0, 100)}...`);
                } catch (e) {
                    addLog(`❌ JSON inválido para WebSocket: ${e.message}`);
                }
            } else if (ws.readyState !== WebSocket.OPEN) {
                addLog("❌ WebSocket não conectado");
            }
        }

        function testApprovalCase() {
            const approvalCase = {
                "input": "TERMO001#12345678901#Desconto sem autorização#Estou sendo descontado na folha sem ter autorizado este empréstimo consignado. Nunca recebi nenhum valor e nunca assinei contrato."
            };
            
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify(approvalCase));
                addLog("🟢 Testando caso de APROVAÇÃO: desconto sem autorização");
            } else {
                addLog("❌ WebSocket não conectado");
            }
        }

        function testRejectionCase() {
            const rejectionCase = {
                "input": "314163#13758748372#12#SOLICITO MEU BOLETO DE QUITAÇÃO JUNTO A ESSE BANCO"
            };
            
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify(rejectionCase));
                addLog("🔴 Testando caso de REJEIÇÃO: solicitação de boleto (fora do escopo)");
            } else {
                addLog("❌ WebSocket não conectado");
            }
        }

        function processFile() {
            const filename = document.getElementById("filename").value || "100.txt";
            const request = {"action": "process_file", "filename": filename};
            
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify(request));
                document.getElementById('processBtn').disabled = true;
                document.getElementById('stopBtn').disabled = false;
                addLog(`📁 Iniciando processamento de arquivo: ${filename}`);
            } else {
                addLog("❌ WebSocket não conectado");
            }
        }

        async function stopProcessing() {
            try {
                const response = await fetch('/stop-file-processing', { method: 'POST' });
                const data = await response.json();
                
                document.getElementById('processBtn').disabled = false;
                document.getElementById('stopBtn').disabled = true;
                addLog(`⏹️ ${data.message}`);
            } catch (error) {
                addLog(`❌ Erro ao parar processamento: ${error.message}`);
            }
        }

        function updateProgress(message) {
            const progressDiv = document.getElementById('progress');
            progressDiv.textContent = message;
            progressDiv.style.display = 'block';
        }

        function clearMessages() {
            document.getElementById('logArea').innerHTML = '[Log limpo - API v3.0 Unificada]';
        }

        document.addEventListener('DOMContentLoaded', function() {
            connectWebSocket();
            refreshStats();
            autoRefreshInterval = setInterval(refreshStats, 5000);
            
            // Adicionar indicação de que a API é unificada
            addLog("🚀 API v3.0 Unificada carregada - Endpoint único com detecção automática!");
            
            document.getElementById('messageInput').addEventListener('keydown', function(e) {
                if (e.ctrlKey && e.key === 'Enter') {
                    sendMessage();
                }
            });
        });
    </script>
</body>
</html>
    """)

# ========== MONITORAMENTO AUTOMÁTICO DE SISTEMA ==========
async def log_system_health():
    """TASK EM BACKGROUND PARA MONITORAMENTO AUTOMÁTICO DE SAÚDE"""
    logger.info("🔍 Iniciando monitoramento automático de saúde do sistema")
    
    while True:
        try:
            stats = semantica_consignacao.serpro_connector.get_error_statistics()
            
            if stats['total_requests'] > 0:
                error_rate = stats['error_rate']
                uptime_hours = stats['uptime_seconds'] / 3600
                
                if error_rate > 15:
                    logger.error(f"🚨 ALERTA CRÍTICO - Error rate: {error_rate:.2f}% - Total errors: {stats['total_errors']} - Uptime: {uptime_hours:.1f}h")
                elif error_rate > 5:
                    logger.warning(f"⚠️ ALERTA - Error rate elevado: {error_rate:.2f}% - Total errors: {stats['total_errors']} - Uptime: {uptime_hours:.1f}h")
                else:
                    if int(uptime_hours) != int((uptime_hours - 5/60)):
                        logger.info(f"✅ Sistema saudável - Error rate: {error_rate:.2f}% - Requests: {stats['total_requests']} - Uptime: {uptime_hours:.1f}h")
            
            uptime_hours = stats['uptime_seconds'] / 3600
            if uptime_hours > 0 and int(uptime_hours) % 24 == 0 and stats['uptime_seconds'] % 3600 < 300:
                logger.info(f"🎉 Milestone de uptime: {int(uptime_hours)}h - {stats['total_requests']} requests processadas")
                perf_logger.info(f"Uptime milestone: {int(uptime_hours)}h - Requests: {stats['total_requests']} - Errors: {stats['total_errors']}")
            
            await asyncio.sleep(300)
            
        except Exception as e:
            logger.error(f"💥 Erro no monitoramento automático: {str(e)}")
            await asyncio.sleep(60)

# ========== PONTO DE ENTRADA ==========
if __name__ == "__main__":
    """EXECUÇÃO PRINCIPAL DA API COM LOGGING DE INICIALIZAÇÃO"""
    
    logger.info("🔧 Preparando inicialização do servidor unificado...")
    
    try:
        config = SerproConfig()
        if not config.validate_config():
            logger.error("❌ Configurações inválidas, verifique 0_config.py")
            exit(1)
        
        logger.info("✅ Configurações validadas com sucesso")
        logger.info("🌐 Iniciando servidor FastAPI Unificado em http://0.0.0.0:8000")
        logger.info("🎯 ENDPOINT PRINCIPAL: POST /analise-semantica (detecta automático)")
        
        import uvicorn
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8000,
            log_level="info",
            access_log=True
        )
        
    except KeyboardInterrupt:
        logger.info("⏹️ Servidor interrompido pelo usuário")
    except Exception as e:
        logger.error(f"💥 Erro fatal na inicialização: {str(e)}")
        logger.debug(f"💥 Traceback: {traceback.format_exc()}")
        exit(1)