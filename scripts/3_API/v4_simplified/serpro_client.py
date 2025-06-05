# serpro_client.py
import os
import json
import time
import uuid
import asyncio
import requests
import aiohttp
from datetime import datetime
from config import *
from logger import semantic_logger

class SerproClient:
    def __init__(self):
        self.access_token = None
        self.token_expires_at = None
        self.setup_ssl()
        semantic_logger.log_info("Serpro Client inicializado", "SERPRO_CLIENT")
    
    def setup_ssl(self):
        """Configura certificados SSL"""
        try:
            if not os.path.exists(CERT_FILE):
                semantic_logger.log_info(f"Baixando certificado SSL: {CERT_URL}", "SSL_SETUP")
                response = requests.get(CERT_URL, verify=False, timeout=10)
                response.raise_for_status()
                with open(CERT_FILE, 'wb') as f:
                    f.write(response.content)
                semantic_logger.log_info(f"Certificado SSL baixado: {CERT_FILE}", "SSL_SETUP")
            else:
                semantic_logger.log_info(f"Certificado SSL já existe: {CERT_FILE}", "SSL_SETUP")
            
            os.environ["REQUESTS_CA_BUNDLE"] = CERT_FILE
            os.environ["SSL_CERT_FILE"] = CERT_FILE
            
        except Exception as e:
            semantic_logger.log_error("SSL_SETUP", e)
            raise
    
    def get_access_token(self):
        """Obtém token de acesso"""
        try:
            # Verificar se token ainda é válido
            if self.access_token and self.token_expires_at:
                if datetime.now().timestamp() < self.token_expires_at:
                    semantic_logger.log_info("Token ainda válido, reutilizando", "TOKEN_REUSE")
                    return self.access_token
            
            semantic_logger.log_info("Solicitando novo token de acesso", "TOKEN_REQUEST")
            
            urls = get_urls()
            data = {"grant_type": "client_credentials"}
            
            for attempt in range(MAX_RETRIES):
                try:
                    start_time = time.time()
                    response = requests.post(
                        urls["token"],
                        data=data,
                        auth=(CLIENT_ID, CLIENT_SECRET),
                        timeout=REQUEST_TIMEOUT
                    )
                    request_time = time.time() - start_time
                    
                    if response.status_code == 200:
                        token_data = response.json()
                        self.access_token = token_data["access_token"]
                        expires_in = token_data.get("expires_in", 3600)
                        self.token_expires_at = datetime.now().timestamp() + expires_in - 300
                        
                        semantic_logger.log_info(
                            f"Token obtido com sucesso | Expira em: {expires_in}s | Tempo: {request_time:.2f}s",
                            "TOKEN_SUCCESS"
                        )
                        return self.access_token
                    
                    semantic_logger.log_error(
                        "TOKEN_REQUEST",
                        f"HTTP {response.status_code}",
                        {"attempt": attempt + 1, "response": response.text[:200]}
                    )
                    
                except Exception as e:
                    semantic_logger.log_error(
                        "TOKEN_REQUEST",
                        e,
                        {"attempt": attempt + 1, "max_retries": MAX_RETRIES}
                    )
                
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY * (attempt + 1)
                    semantic_logger.log_info(f"Aguardando {delay}s antes da próxima tentativa", "TOKEN_RETRY")
                    time.sleep(delay)
            
            error_msg = f"Falha ao obter token após {MAX_RETRIES} tentativas"
            semantic_logger.log_error("TOKEN_FAILURE", error_msg)
            raise Exception(error_msg)
            
        except Exception as e:
            semantic_logger.log_error("GET_ACCESS_TOKEN", e)
            raise
    
    async def call_llm(self, prompt):
        """Chama Serpro LLM"""
        call_id = str(uuid.uuid4())[:8]
        
        try:
            semantic_logger.log_info(f"Iniciando chamada LLM | ID: {call_id}", "LLM_CALL")
            
            token = self.get_access_token()
            urls = get_urls()
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": MODEL_NAME,
                "messages": [{"role": "user", "content": prompt}],
                **LLM_CONFIG
            }
            
            # Log do payload (sem o token)
            semantic_logger.log_info(
                f"Payload LLM | Model: {MODEL_NAME} | Prompt: {len(prompt)} chars",
                f"LLM_PAYLOAD_{call_id}"
            )
            
            for attempt in range(MAX_RETRIES):
                try:
                    start_time = time.time()
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            f"{urls['api']}/chat/completions",
                            headers=headers,
                            json=payload,
                            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                        ) as response:
                            
                            request_time = time.time() - start_time
                            
                            if response.status == 200:
                                result = await response.json()
                                parsed_result = self.parse_response(result)
                                
                                semantic_logger.log_info(
                                    f"LLM sucesso | ID: {call_id} | Status: {response.status} | "
                                    f"Tempo: {request_time:.2f}s | Diagnóstico: {parsed_result.get('diagnosticoLLM', 'N/A')}",
                                    "LLM_SUCCESS"
                                )
                                
                                return parsed_result
                            
                            if response.status == 401:
                                semantic_logger.log_info("Token expirado, renovando", f"LLM_TOKEN_REFRESH_{call_id}")
                                self.access_token = None
                                continue
                            
                            error_text = await response.text()
                            semantic_logger.log_error(
                                "LLM_HTTP_ERROR",
                                f"HTTP {response.status}",
                                {"attempt": attempt + 1, "response": error_text[:300], "call_id": call_id}
                            )
                            
                except asyncio.TimeoutError:
                    semantic_logger.log_error(
                        "LLM_TIMEOUT",
                        f"Timeout após {REQUEST_TIMEOUT}s",
                        {"attempt": attempt + 1, "call_id": call_id}
                    )
                except Exception as e:
                    semantic_logger.log_error(
                        "LLM_REQUEST_ERROR",
                        e,
                        {"attempt": attempt + 1, "call_id": call_id}
                    )
                
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY * (attempt + 1)
                    semantic_logger.log_info(f"Aguardando {delay}s antes da próxima tentativa", f"LLM_RETRY_{call_id}")
                    await asyncio.sleep(delay)
            
            error_msg = f"Falha na chamada LLM após {MAX_RETRIES} tentativas | ID: {call_id}"
            semantic_logger.log_error("LLM_FAILURE", error_msg)
            raise Exception(error_msg)
            
        except Exception as e:
            semantic_logger.log_error("CALL_LLM", e, {"call_id": call_id})
            raise
    
    def parse_response(self, response):
        """Parse da resposta LLM"""
        try:
            content = response["choices"][0]["message"]["content"]
            
            semantic_logger.log_info(
                f"Parsing resposta LLM | Tamanho: {len(content)} chars",
                "LLM_PARSE"
            )
            
            # Tenta JSON direto
            if content.strip().startswith('{'):
                try:
                    parsed = json.loads(content)
                    semantic_logger.log_info("Parse JSON direto bem-sucedido", "LLM_PARSE_JSON")
                    return parsed
                except json.JSONDecodeError as e:
                    semantic_logger.log_error("LLM_PARSE_JSON", e, {"content_preview": content[:100]})
            
            # Busca JSON no texto
            import re
            match = re.search(r'\{[^{}]*\}', content)
            if match:
                try:
                    parsed = json.loads(match.group())
                    semantic_logger.log_info("Parse JSON extraído bem-sucedido", "LLM_PARSE_EXTRACT")
                    return parsed
                except json.JSONDecodeError as e:
                    semantic_logger.log_error("LLM_PARSE_EXTRACT", e, {"match": match.group()})
            
            # Fallback simples
            semantic_logger.log_info("Usando fallback para parse", "LLM_PARSE_FALLBACK")
            return self.create_fallback(content)
            
        except Exception as e:
            semantic_logger.log_error("PARSE_RESPONSE", e, {"response_preview": str(response)[:200]})
            return self.create_fallback(content if 'content' in locals() else "Erro de parsing")
    
    def create_fallback(self, content):
        """Fallback quando não há JSON válido"""
        try:
            content_lower = content.lower()
            
            approve_words = ["sim", "aprovado", "válido", "autorização"]
            reject_words = ["não", "rejeitado", "inválido", "boleto"]
            
            approve_count = sum(1 for word in approve_words if word in content_lower)
            reject_count = sum(1 for word in reject_words if word in content_lower)
            
            if approve_count > reject_count:
                diagnostico = "SIM"
                confidence = min(0.8, 0.5 + approve_count * 0.1)
            else:
                diagnostico = "NÃO"
                confidence = min(0.8, 0.5 + reject_count * 0.1)
            
            result = {
                "diagnosticoLLM": diagnostico,
                "justificativaLLM": content[:100],
                "confidence": confidence
            }
            
            semantic_logger.log_info(
                f"Fallback criado | Diagnóstico: {diagnostico} | Confiança: {confidence:.2f}",
                "LLM_FALLBACK"
            )
            
            return result
            
        except Exception as e:
            semantic_logger.log_error("CREATE_FALLBACK", e)
            return {
                "diagnosticoLLM": "NÃO",
                "justificativaLLM": "Erro no processamento",
                "confidence": 0.1
            }