# E_processador_arquivo.py - PROCESSADOR DE ARQUIVOS SERPRO LLM
"""
SISTEMA DE PROCESSAMENTO BATCH PARA ANÁLISE SEMÂNTICA DE JUSTIFICATIVAS

Este arquivo implementa um processador que:
1. Lê um arquivo TXT com justificativas de empréstimos consignados
2. Envia cada justificativa para o Serpro LLM para análise
3. Classifica como APROVADO, REJEITADO, REVISÃO ou ERRO
4. Gera relatórios detalhados e estatísticas completas

ARQUITETURA:
- ProcessingResult: Dataclass que armazena resultado de cada item
- ProcessingStatistics: Dataclass que mantém estatísticas globais
- FileProcessor: Classe principal que orquestra todo o processamento

FLUXO DE EXECUÇÃO:
main() → FileProcessor.process_file() → para cada linha: process_item() → call_serpro_llm()
"""

import asyncio          # Para programação assíncrona (requisições HTTP simultâneas)
import aiohttp          # Cliente HTTP assíncrono para chamadas ao Serpro LLM
import json             # Para parsing de JSON (respostas do LLM)
import time             # Para medição de tempo de processamento
import sys              # Para manipulação de paths e imports
import os               # Para variáveis de ambiente e sistema de arquivos
from pathlib import Path        # Para manipulação moderna de caminhos de arquivo
from datetime import datetime  # Para timestamps e medição de tempo
from typing import Dict, List, Any, Optional  # Type hints para melhor documentação
import logging          # Para logging detalhado em arquivo
from dataclasses import dataclass, asdict    # Para estruturas de dados organizadas
import uuid             # Para geração de IDs únicos
import traceback        # Para captura detalhada de erros

# ========== IMPORT DA CONFIGURAÇÃO CENTRALIZADA ==========
# Importação dinâmica do arquivo 0_config.py para acesso às configurações
sys.path.append(os.path.dirname(__file__))
import importlib.util
spec = importlib.util.spec_from_file_location("config", "0_config.py")
config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_module)
SerproConfig = config_module.SerproConfig

# ========== ESTRUTURAS DE DADOS ==========

@dataclass
class ProcessingResult:
    """
    RESULTADO DO PROCESSAMENTO DE UM ITEM INDIVIDUAL
    
    Armazena todas as informações sobre o processamento de uma justificativa:
    - Dados originais (ID, CPF, prática vedada, justificativa)
    - Resultado da análise LLM (diagnóstico, confiança, justificativa)
    - Metadados (tempo, erros, tentativas)
    
    Status possíveis:
    - APPROVED: Justificativa válida (SIM + confiança >= 0.7)
    - REVIEW_REQUIRED: Necessita revisão manual (SIM + 0.5 <= confiança < 0.7)
    - REJECTED: Justificativa inválida (NÃO ou confiança < 0.5)
    - ERROR: Erro no processamento
    """
    id_termo: str                           # ID do termo do processo
    cpf: str                               # CPF do usuário (mascarado nos logs)
    pratica_vedada: str                    # Tipo de prática vedada alegada
    justificativa: str                     # Justificativa completa do usuário
    status: str                            # Status final: APPROVED/REJECTED/REVIEW_REQUIRED/ERROR
    diagnostico_llm: Optional[str] = None  # Resposta do LLM: SIM/NÃO
    confidence: Optional[float] = None     # Nível de confiança (0.0 a 1.0)
    justificativa_llm: Optional[str] = None # Explicação do LLM sobre a decisão
    error_message: Optional[str] = None    # Mensagem de erro, se houver
    error_type: Optional[str] = None       # Tipo do erro para categorização
    processing_time: Optional[float] = None # Tempo gasto no processamento (segundos)
    timestamp: Optional[str] = None        # Timestamp ISO 8601 do processamento
    attempt_number: int = 1                # Número da tentativa (para retry)
    
    def __post_init__(self):
        """Gera timestamp automaticamente se não fornecido"""
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

@dataclass 
class ProcessingStatistics:
    """
    ESTATÍSTICAS GLOBAIS DO PROCESSAMENTO
    
    Mantém contadores e métricas sobre todo o processamento:
    - Contadores por status (aprovados, rejeitados, etc.)
    - Métricas de tempo e performance
    - Cálculo automático de taxas percentuais
    """
    total_items: int = 0                   # Total de itens no arquivo
    processed: int = 0                     # Total processados até agora
    approved: int = 0                      # Contador de aprovados
    rejected: int = 0                      # Contador de rejeitados
    review_required: int = 0               # Contador que precisam revisão
    errors: int = 0                        # Contador de erros
    total_time: float = 0.0                # Tempo total gasto (segundos)
    average_time: float = 0.0              # Tempo médio por item
    start_time: Optional[str] = None       # Horário de início
    end_time: Optional[str] = None         # Horário de fim
    
    def calculate_rates(self):
        """
        CALCULA TAXAS PERCENTUAIS
        
        Retorna dicionário com percentuais de cada status.
        Evita divisão por zero se nenhum item foi processado.
        """
        if self.processed > 0:
            return {
                "approval_rate": (self.approved / self.processed) * 100,
                "rejection_rate": (self.rejected / self.processed) * 100,
                "review_rate": (self.review_required / self.processed) * 100,
                "error_rate": (self.errors / self.processed) * 100
            }
        return {"approval_rate": 0, "rejection_rate": 0, "review_rate": 0, "error_rate": 0}

# ========== CLASSE PRINCIPAL DO PROCESSADOR ==========

class FileProcessor:
    """
    PROCESSADOR PRINCIPAL DE ARQUIVOS COM SERPRO LLM
    
    Classe que orquestra todo o processamento:
    1. Configuração e inicialização
    2. Leitura e parsing do arquivo de entrada
    3. Comunicação com Serpro LLM
    4. Geração de relatórios e estatísticas
    
    CARACTERÍSTICAS:
    - Processamento assíncrono para melhor performance
    - Sistema robusto de retry para chamadas LLM
    - Logging detalhado em arquivo
    - Validação de dados de entrada
    - Geração automática de relatórios JSON
    """
    
    def __init__(self, config_file: str = None):
        """
        INICIALIZAÇÃO DO PROCESSADOR
        
        1. Carrega configurações centralizadas
        2. Inicializa estruturas de dados
        3. Configura paths de entrada e saída
        4. Configura sistema de logging
        """
        # Carregar configurações do arquivo 0_config.py
        self.config = SerproConfig()
        
        # Inicializar estruturas de controle
        self.stats = ProcessingStatistics()     # Estatísticas globais
        self.results: List[ProcessingResult] = []  # Lista com todos os resultados
        
        # Configurar paths de entrada e saída (cria pastas se não existirem)
        self.paths = self.config.get_file_processing_paths()
        
        # Configurar sistema de logging (apenas em arquivo, sem duplicação)
        self.setup_logging()
        
        # Variáveis para comunicação HTTP assíncrona
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Controle de autenticação com Serpro LLM
        self.access_token = None               # Token JWT atual
        self.token_expires_at = None           # Timestamp de expiração do token
        
    def setup_logging(self):
        """
        CONFIGURAÇÃO DO SISTEMA DE LOGGING
        
        Configura logging APENAS para arquivo (evita duplicação no console):
        - Log detalhado em arquivo: JSON/processamento.log
        - Formato: timestamp - level - mensagem
        - Encoding UTF-8 para caracteres especiais
        """
        log_file = self.paths["output"] / "processamento.log"
        
        # Configurar logger principal
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Limpar handlers existentes (evita duplicação)
        self.logger.handlers.clear()
        
        # Configurar handler apenas para arquivo
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(file_handler)
    
    def print_clean(self, message: str, emoji: str = ""):
        """
        SISTEMA DE OUTPUT LIMPO (SEM DUPLICAÇÃO)
        
        Evita duplicação entre console e log:
        - Console: mensagem formatada com emoji
        - Arquivo: log detalhado para auditoria
        
        Args:
            message: Mensagem a ser exibida
            emoji: Emoji opcional para o console
        """
        if emoji:
            formatted_message = f"{emoji} {message}"
        else:
            formatted_message = message
        
        # Log apenas para arquivo (auditoria)
        self.logger.info(formatted_message)
        
        # Print apenas no console (experiência do usuário)
        print(formatted_message)
    
    # ========== LEITURA E PARSING DE ARQUIVO ==========
    
    def read_input_file(self, filename: str = None) -> List[str]:
        """
        LEITURA DO ARQUIVO DE ENTRADA
        
        Lê arquivo TXT com formato: IDTERMO#CPF#PRATICA VEDADA#JUSTIFICATIVA
        
        Funcionalidades:
        - Detecta automaticamente o arquivo padrão se não especificado
        - Pula linha de cabeçalho se configurado
        - Remove linhas vazias
        - Preserva justificativas que contenham o caractere #
        
        Args:
            filename: Nome do arquivo (opcional, usa padrão se None)
            
        Returns:
            Lista de strings, cada uma representando uma linha processada
            
        Raises:
            FileNotFoundError: Se o arquivo não for encontrado
        """
        # Determinar caminho do arquivo
        if filename:
            file_path = self.paths["input"] / filename
        else:
            file_path = self.paths["input_file"]  # Arquivo padrão (5.txt)
        
        # Verificar se arquivo existe
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        
        self.print_clean(f"Lendo arquivo: {file_path}", "📖")
        
        # Ler todas as linhas com encoding UTF-8
        with open(file_path, 'r', encoding=self.config.FILE_PROCESSING["encoding"]) as f:
            lines = f.readlines()
        
        # Processar linhas (filtrar vazias, pular cabeçalho)
        processed_lines = []
        for i, line in enumerate(lines):
            line = line.strip()  # Remove espaços e quebras de linha
            if not line:         # Pula linhas vazias
                continue
                
            # Pular linha de cabeçalho se configurado
            if (i == 0 and self.config.FILE_PROCESSING["skip_header"] 
                and line.startswith("IDTERMO#CPF#PRATICA VEDADA#JUSTIFICATIVA")):
                self.print_clean("Pulando linha de cabeçalho", "⏭️")
                continue
                
            processed_lines.append(line)
        
        self.print_clean(f"Carregadas {len(processed_lines)} linhas para processamento", "✅")
        return processed_lines
    
    def parse_line(self, line: str) -> Dict[str, str]:
        """
        PARSING DE UMA LINHA DO ARQUIVO
        
        Converte string no formato: IDTERMO#CPF#PRATICA VEDADA#JUSTIFICATIVA
        Para dicionário com campos nomeados.
        
        TRATAMENTO ESPECIAL:
        - Se justificativa contém #, preserva o conteúdo usando join()
        - Exemplo: "123#456#Desconto#Texto com # no meio" → justificativa = "Texto com # no meio"
        
        Args:
            line: Linha do arquivo no formato delimitado por #
            
        Returns:
            Dicionário com campos: id_termo, cpf, pratica_vedada, justificativa
            
        Raises:
            ValueError: Se formato da linha for inválido (menos de 4 campos)
        """
        parts = line.split("#")
        if len(parts) < 4:
            raise ValueError(f"Formato inválido. Esperado: IDTERMO#CPF#PRATICA VEDADA#JUSTIFICATIVA")
        
        return {
            "id_termo": parts[0],
            "cpf": parts[1], 
            "pratica_vedada": parts[2],
            "justificativa": "#".join(parts[3:])  # Join caso justificativa contenha #
        }
    
    def validate_data(self, data: Dict[str, str]) -> bool:
        """
        VALIDAÇÃO DOS DADOS DE ENTRADA
        
        Verifica se os dados atendem aos critérios mínimos:
        - Todos os campos obrigatórios estão presentes
        - Justificativa tem tamanho adequado (min/max caracteres)
        - CPF válido (se validação habilitada)
        
        Args:
            data: Dicionário com dados parseados
            
        Returns:
            True se dados válidos, False caso contrário
        """
        validation = self.config.VALIDATION_CONFIG
        
        # Verificar campos obrigatórios
        for field in validation["required_fields"]:
            if not data.get(field):
                return False
        
        # Validar tamanho da justificativa
        justificativa = data.get("justificativa", "")
        if len(justificativa) < validation["min_justificativa_length"]:
            return False
        if len(justificativa) > validation["max_justificativa_length"]:
            return False
            
        return True
    
    # ========== COMUNICAÇÃO COM SERPRO LLM ==========
    
    async def get_access_token(self):
        """
        OBTENÇÃO DO TOKEN DE ACESSO SERPRO LLM
        
        Sistema robusto de autenticação com:
        - Cache de token (reutiliza se ainda válido)
        - Renovação automática antes da expiração
        - Sistema de retry com backoff exponencial
        - Tratamento específico de erros de autenticação
        
        FLUXO:
        1. Verifica se token atual ainda é válido
        2. Se não, faz nova requisição OAuth2 client_credentials
        3. Armazena token e timestamp de expiração
        4. Retry automático em caso de falha temporária
        
        Returns:
            String com access token válido
            
        Raises:
            Exception: Se falhar após todas as tentativas
        """
        # Verificar se token atual ainda é válido
        if self.access_token and self.token_expires_at:
            if datetime.now().timestamp() < self.token_expires_at:
                return self.access_token
        
        # Obter URLs e configurações
        urls = self.config.get_urls()
        retry_config = self.config.RETRY_CONFIG
        
        # Tentar obter novo token com retry
        for attempt in range(1, retry_config["max_retries"] + 1):
            try:
                self.print_clean(f"Obtendo token (tentativa {attempt})", "🔑")
                
                # Preparar requisição OAuth2
                data = {"grant_type": "client_credentials"}
                auth = aiohttp.BasicAuth(self.config.CLIENT_ID, self.config.CLIENT_SECRET)
                
                # Fazer requisição assíncrona
                async with self.session.post(
                    urls["token"], 
                    data=data, 
                    auth=auth,
                    timeout=aiohttp.ClientTimeout(total=self.config.REQUEST_TIMEOUT)
                ) as response:
                    
                    if response.status == 200:
                        # Token obtido com sucesso
                        token_data = await response.json()
                        self.access_token = token_data["access_token"]
                        
                        # Calcular expiração (com buffer de segurança de 5 min)
                        expires_in = token_data.get("expires_in", 3600)
                        self.token_expires_at = datetime.now().timestamp() + expires_in - 300
                        
                        self.print_clean("Token obtido com sucesso", "✅")
                        return self.access_token
                    
                    else:
                        # Erro HTTP
                        error_text = await response.text()
                        self.print_clean(f"Erro HTTP {response.status}: {error_text}", "❌")
                        
                        # Não fazer retry para erros de autenticação (401, 403)
                        if response.status in [401, 403]:
                            raise Exception(f"Erro de autenticação: {response.status}")
                        
                        # Aguardar antes de retry (backoff exponencial)
                        if attempt < retry_config["max_retries"]:
                            delay = retry_config["retry_delay"] * (retry_config["backoff_multiplier"] ** (attempt - 1))
                            await asyncio.sleep(delay)
                            
            except Exception as e:
                self.print_clean(f"Erro ao obter token: {str(e)}", "💥")
                if attempt == retry_config["max_retries"]:
                    raise
                    
                # Delay simples para outros erros
                delay = retry_config["retry_delay"] * attempt
                await asyncio.sleep(delay)
        
        raise Exception("Falha ao obter token após todas as tentativas")
    
    async def call_serpro_llm(self, prompt: str) -> Dict[str, Any]:
        """
        CHAMADA PRINCIPAL PARA O SERPRO LLM
        
        Sistema robusto de comunicação com:
        - Renovação automática de token se expirado
        - Retry com backoff exponencial para falhas temporárias
        - Timeouts configuráveis
        - Tratamento específico por tipo de erro
        
        TIPOS DE ERRO TRATADOS:
        - 401: Token expirado → renovar e tentar novamente
        - 429: Rate limit → aguardar mais tempo
        - 5xx: Erro servidor → retry com backoff
        - Timeout: Problema rede → retry
        
        Args:
            prompt: Prompt formatado para enviar ao LLM
            
        Returns:
            Dicionário com resposta parseada do LLM
            
        Raises:
            Exception: Se falhar após todas as tentativas
        """
        # Garantir que temos token válido
        await self.get_access_token()
        
        # Preparar requisição
        urls = self.config.get_urls()
        retry_config = self.config.RETRY_CONFIG
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # Payload no formato esperado pelo Serpro LLM (compatível OpenAI)
        payload = {
            "model": self.config.MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            **self.config.LLM_CONFIG  # temperature, max_tokens, etc.
        }
        
        # Tentativas com retry
        for attempt in range(1, retry_config["max_retries"] + 1):
            try:
                async with self.session.post(
                    f"{urls['api']}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.REQUEST_TIMEOUT)
                ) as response:
                    
                    if response.status == 200:
                        # Sucesso - parsear resposta
                        result = await response.json()
                        return self.parse_llm_response(result)
                    
                    elif response.status == 401:
                        # Token expirado - renovar e continuar loop
                        self.print_clean("Token expirado, renovando...", "🔄")
                        self.access_token = None
                        await self.get_access_token()
                        continue
                    
                    else:
                        # Outros erros HTTP
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text}")
                        
            except asyncio.TimeoutError:
                # Timeout - tentar novamente
                self.print_clean(f"Timeout na tentativa {attempt}", "⏰")
                if attempt == retry_config["max_retries"]:
                    raise Exception("Timeout na chamada LLM")
                    
            except Exception as e:
                # Outros erros
                self.print_clean(f"Erro LLM tentativa {attempt}: {str(e)}", "❌")
                if attempt == retry_config["max_retries"]:
                    raise
                    
            # Aguardar antes de próxima tentativa (backoff exponencial)
            delay = retry_config["retry_delay"] * (retry_config["backoff_multiplier"] ** (attempt - 1))
            await asyncio.sleep(delay)
        
        raise Exception("Falha na chamada LLM após todas as tentativas")
    
    def parse_llm_response(self, response: Dict) -> Dict[str, Any]:
        """
        PARSING DA RESPOSTA DO LLM
        
        Converte resposta bruta do LLM em formato estruturado.
        Tenta múltiplas estratégias para extrair JSON:
        
        1. JSON direto (resposta já é JSON válido)
        2. Extração via regex (JSON embutido em texto)
        3. Fallback inteligente (análise por palavras-chave)
        
        Args:
            response: Resposta bruta do Serpro LLM
            
        Returns:
            Dicionário com campo "llm_analysis" contendo dados estruturados
            
        Raises:
            Exception: Se formato da resposta for completamente inválido
        """
        try:
            # Extrair conteúdo da resposta
            content = response["choices"][0]["message"]["content"]
            
            # Estratégia 1: JSON direto
            try:
                if content.strip().startswith('{'):
                    return {"llm_analysis": json.loads(content)}
                
                # Estratégia 2: Extração via regex
                import re
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
                if json_match:
                    return {"llm_analysis": json.loads(json_match.group())}
                
            except json.JSONDecodeError:
                pass
            
            # Estratégia 3: Fallback inteligente
            return {"llm_analysis": self.create_fallback_response(content)}
            
        except (KeyError, IndexError) as e:
            raise Exception(f"Formato de resposta LLM inválido: {e}")
    
    def create_fallback_response(self, content: str) -> Dict[str, Any]:
        """
        FALLBACK INTELIGENTE PARA RESPOSTAS NÃO-JSON
        
        Quando o LLM não retorna JSON válido, analisa o texto por palavras-chave
        para determinar se a justificativa deve ser aprovada ou rejeitada.
        
        ALGORITMO:
        1. Converte texto para minúsculas
        2. Conta palavras que indicam aprovação vs rejeição
        3. Determina diagnóstico baseado na contagem
        4. Calcula confiança baseada na força das indicações
        
        Args:
            content: Texto bruto da resposta do LLM
            
        Returns:
            Dicionário no formato esperado com diagnóstico inferido
        """
        content_lower = content.lower()
        
        # Palavras que indicam que a justificativa deve ser aprovada
        approve_words = ["sim", "aprovado", "válido", "procedente", "autorização", "liquidado", "crédito"]
        
        # Palavras que indicam que a justificativa deve ser rejeitada
        reject_words = ["não", "rejeitado", "inválido", "taxa", "boleto", "renegociar"]
        
        # Contar ocorrências
        approve_count = sum(1 for word in approve_words if word in content_lower)
        reject_count = sum(1 for word in reject_words if word in content_lower)
        
        # Determinar diagnóstico baseado na contagem
        if approve_count > reject_count:
            diagnostico = "SIM"
            confidence = min(0.9, 0.5 + (approve_count * 0.1))
        else:
            diagnostico = "NÃO"
            confidence = min(0.9, 0.5 + (reject_count * 0.1))
        
        # Retornar no formato padrão
        return {
            "requestId": str(uuid.uuid4()),
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00"),
            "diagnosticoLLM": diagnostico,
            "justificativaLLM": content[:144],  # Limitar a 144 caracteres
            "confidence": confidence,
            "status": "success"
        }
    
    # ========== PROCESSAMENTO PRINCIPAL ==========
    
    async def process_item(self, line: str, item_number: int) -> ProcessingResult:
        """
        PROCESSAMENTO DE UM ITEM INDIVIDUAL
        
        Fluxo completo para processar uma justificativa:
        1. Parse da linha do arquivo
        2. Validação dos dados
        3. Criação do prompt para o LLM
        4. Chamada ao Serpro LLM
        5. Análise da resposta e determinação do status final
        6. Criação do resultado estruturado
        
        LÓGICA DE CLASSIFICAÇÃO:
        - APPROVED: SIM + confiança >= 0.7
        - REVIEW_REQUIRED: SIM + 0.5 <= confiança < 0.7
        - REJECTED: NÃO ou confiança < 0.5
        - ERROR: Erro em qualquer etapa
        
        Args:
            line: Linha do arquivo no formato delimitado
            item_number: Número sequencial do item (para identificação)
            
        Returns:
            ProcessingResult com todos os dados e resultado da análise
        """
        start_time = time.time()
        
        try:
            # 1. Parse da linha
            data = self.parse_line(line)
            
            # 2. Validação dos dados
            if not self.validate_data(data):
                return ProcessingResult(
                    **data,
                    status="ERROR",
                    error_message="Dados inválidos",
                    error_type="VALIDATION_ERROR",
                    processing_time=time.time() - start_time
                )
            
            # 3. Criar prompt usando template configurado
            prompt = self.config.get_prompt_template().format(justificativa=data["justificativa"])
            
            # 4. Chamar Serpro LLM
            llm_response = await self.call_serpro_llm(prompt)
            llm_result = llm_response.get("llm_analysis", {})
            
            # 5. Extrair resultados da análise
            diagnostico_llm = llm_result.get("diagnosticoLLM", "NÃO")
            confidence = llm_result.get("confidence", 0.5)
            justificativa_llm = llm_result.get("justificativaLLM", "")
            
            # 6. Determinar status final baseado na lógica de negócio
            if diagnostico_llm == "SIM" and confidence >= 0.7:
                status = "APPROVED"           # Alta confiança - aprovar
            elif diagnostico_llm == "SIM" and confidence >= 0.5:
                status = "REVIEW_REQUIRED"    # Média confiança - revisar
            else:
                status = "REJECTED"           # Baixa confiança ou NÃO - rejeitar
            
            # 7. Criar resultado estruturado
            result = ProcessingResult(
                **data,
                status=status,
                diagnostico_llm=diagnostico_llm,
                confidence=confidence,
                justificativa_llm=justificativa_llm,
                processing_time=time.time() - start_time
            )
            
            # 8. Salvar resultado individual se configurado
            if self.config.FILE_PROCESSING["save_individual_files"]:
                await self.save_individual_result(result)
            
            return result
            
        except Exception as e:
            # Tratamento de erros - criar resultado de erro
            self.print_clean(f"Erro no item {item_number}: {str(e)}", "💥")
            
            # Tentar parsear dados para o resultado de erro
            try:
                data = self.parse_line(line)
            except:
                # Se parse falhar, criar dados mínimos
                data = {"id_termo": f"ERRO_{item_number}", "cpf": "", "pratica_vedada": "", "justificativa": line}
            
            return ProcessingResult(
                **data,
                status="ERROR",
                error_message=str(e),
                error_type=type(e).__name__,
                processing_time=time.time() - start_time
            )
    
    # ========== PERSISTÊNCIA E RELATÓRIOS ==========
    
    async def save_individual_result(self, result: ProcessingResult):
        """
        SALVAR RESULTADO INDIVIDUAL EM ARQUIVO JSON
        
        Cria um arquivo JSON para cada item processado, permitindo:
        - Auditoria detalhada de cada decisão
        - Reprocessamento individual se necessário
        - Análise posterior dos resultados
        
        Formato do arquivo: {id_termo}.json
        Localização: pasta JSON/ configurada
        
        Args:
            result: Resultado a ser salvo
        """
        filename = f"{result.id_termo}.json"
        filepath = self.paths["output"] / filename
        
        # Salvar com formatação legível e encoding UTF-8
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(asdict(result), f, indent=self.config.JSON_CONFIG["indent"], ensure_ascii=False)
    
    def update_statistics(self, result: ProcessingResult):
        """
        ATUALIZAR ESTATÍSTICAS GLOBAIS
        
        Incrementa contadores baseado no resultado:
        - Contadores por status (approved, rejected, etc.)
        - Métricas de tempo (total e médio)
        - Total processado
        
        Args:
            result: Resultado para contabilizar
        """
        self.stats.processed += 1
        
        # Incrementar contador específico
        if result.status == "APPROVED":
            self.stats.approved += 1
        elif result.status == "REJECTED":
            self.stats.rejected += 1
        elif result.status == "REVIEW_REQUIRED":
            self.stats.review_required += 1
        elif result.status == "ERROR":
            self.stats.errors += 1
        
        # Atualizar métricas de tempo
        if result.processing_time:
            self.stats.total_time += result.processing_time
            self.stats.average_time = self.stats.total_time / self.stats.processed
    
    # ========== INTERFACE DO USUÁRIO ==========
    
    def print_progress(self, current: int, total: int, result: ProcessingResult):
        """
        EXIBIR PROGRESSO DETALHADO DO PROCESSAMENTO
        
        Mostra informações completas sobre cada item processado:
        - Identificação e progresso ([1/5] 20.0%)
        - Status final com emoji visual
        - Justificativa completa do usuário
        - Diagnóstico e confiança do LLM
        - Justificativa/razão do LLM
        - Métricas de tempo e erros
        
        FORMATO VISUAL:
        ----------------------------------------------------------------------
        [1/5] (20.0%) ✅ TERMO123 - APPROVED
        ----------------------------------------------------------------------
        👤 USUÁRIO: Justificativa completa aqui...
        🤖 LLM: SIM (confiança: 0.85) 🎯
        💭 RAZÃO: Justificativa válida - desconto sem autorização
        ℹ️  INFO: ⏱️ 14.2s
        ⏳ Aguardando 1.0s para próximo item...
        ----------------------------------------------------------------------
        
        Args:
            current: Número do item atual
            total: Total de itens
            result: Resultado do processamento
        """
        
        # Mapeamento de status para emojis visuais
        status_emojis = {
            "APPROVED": "✅",        # Aprovado
            "REJECTED": "❌",        # Rejeitado
            "REVIEW_REQUIRED": "⚠️", # Precisa revisão
            "ERROR": "💥"            # Erro
        }
        
        emoji = status_emojis.get(result.status, "❓")
        percentage = (current / total) * 100
        
        # Cabeçalho com progresso
        print(f"\n{'-'*70}")
        print(f"[{current}/{total}] ({percentage:.1f}%) {emoji} {result.id_termo} - {result.status}")
        print(f"{'-'*70}")
        
        # Justificativa do usuário COMPLETA (sem cortes)
        print(f"👤 USUÁRIO: {result.justificativa}")
        
        # Resultado da análise LLM
        if result.diagnostico_llm:
            # Indicador visual de confiança
            confidence_indicator = "🎯" if result.confidence and result.confidence >= 0.7 else "🤔"
            confidence_text = f" (confiança: {result.confidence:.2f})" if result.confidence else ""
            print(f"🤖 LLM: {result.diagnostico_llm}{confidence_text} {confidence_indicator}")
        
        # Justificativa/razão do LLM
        if result.justificativa_llm:
            print(f"💭 RAZÃO: {result.justificativa_llm}")
        
        # Informações adicionais (tempo, erros)
        info_parts = []
        if result.processing_time:
            info_parts.append(f"⏱️ {result.processing_time:.1f}s")
        if result.error_message:
            info_parts.append(f"💥 {result.error_message}")
        
        if info_parts:
            print(f"ℹ️  INFO: {' | '.join(info_parts)}")
        
        # Indicador de pausa (exceto último item)
        if current < total:
            delay = self.config.FILE_PROCESSING["delay_between_requests"]
            print(f"⏳ Aguardando {delay}s para próximo item...")
        
        print(f"{'-'*70}")
    
    async def save_final_statistics(self):
        """
        SALVAR ESTATÍSTICAS FINAIS EM ARQUIVO JSON
        
        Gera relatório completo com:
        - Estatísticas de processamento
        - Taxas percentuais
        - Configurações utilizadas
        - Lista detalhada de todos os resultados
        
        Arquivo gerado: JSON/estatisticas.json
        """
        if not self.config.STATS_CONFIG["save_stats"]:
            return
        
        rates = self.stats.calculate_rates()
        
        # Estrutura completa do relatório
        final_stats = {
            "processamento": asdict(self.stats),
            "taxas": rates,
            "configuracao": {
                "modelo_llm": self.config.MODEL_NAME,
                "arquivo_processado": str(self.paths["input_file"]),
                "pasta_output": str(self.paths["output"])
            },
            "resultados_detalhados": [asdict(r) for r in self.results]
        }
        
        # Salvar com formatação legível
        stats_file = self.paths["stats_file"]
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(final_stats, f, indent=2, ensure_ascii=False)
        
        self.print_clean(f"Estatísticas salvas em: {stats_file}", "💾")
    
    def print_final_summary(self):
        """
        EXIBIR RELATÓRIO FINAL COMPLETO
        
        Sumário detalhado do processamento com:
        - Informações do arquivo e configuração
        - Métricas de performance
        - Resultados por categoria
        - Análise de procedência
        - Arquivos gerados
        - Período de execução
        
        FORMATO:
        ======================================================================
        📊 RELATÓRIO FINAL - SERPRO LLM
        ======================================================================
        📁 Arquivo processado: 5.txt
        🤖 Modelo utilizado: deepseek-r1-distill-qwen-14b
        [... mais informações ...]
        ======================================================================
        """
        rates = self.stats.calculate_rates()
        
        print(f"\n{'='*70}")
        print("📊 RELATÓRIO FINAL - SERPRO LLM")
        print(f"{'='*70}")
        
        # Informações básicas do processamento
        print(f"📁 Arquivo processado: {self.paths['input_file'].name}")
        print(f"🤖 Modelo utilizado: {self.config.MODEL_NAME}")
        print(f"🌐 Ambiente: {self.config.AMBIENTE}")
        print(f"📈 Total processado: {self.stats.processed} itens")
        
        # Métricas de performance
        print(f"\n⏱️ PERFORMANCE:")
        print(f"   Tempo total: {self.stats.total_time:.1f}s ({self.stats.total_time/60:.1f} min)")
        print(f"   Tempo médio por item: {self.stats.average_time:.1f}s")
        
        # Resultados detalhados por categoria
        print(f"\n🎯 RESULTADOS DETALHADOS:")
        print(f"   ✅ Aprovados: {self.stats.approved} ({rates['approval_rate']:.1f}%)")
        print(f"   ⚠️ Necessitam revisão: {self.stats.review_required} ({rates['review_rate']:.1f}%)")
        print(f"   ❌ Rejeitados: {self.stats.rejected} ({rates['rejection_rate']:.1f}%)")
        print(f"   💥 Erros: {self.stats.errors} ({rates['error_rate']:.1f}%)")
        
        # Análise de procedência (aprovados + revisão = casos válidos)
        print(f"\n📋 ANÁLISE:")
        total_validos = self.stats.approved + self.stats.review_required
        if total_validos > 0:
            taxa_procedencia = (total_validos / self.stats.processed) * 100
            print(f"   📈 Taxa de procedência: {taxa_procedencia:.1f}% ({total_validos} de {self.stats.processed})")
        
        # Status de qualidade do processamento
        if self.stats.errors == 0:
            print(f"   🎉 Processamento sem erros!")
        else:
            print(f"   ⚠️ {self.stats.errors} erros encontrados - verifique os logs")
        
        # Arquivos gerados para auditoria
        print(f"\n💾 ARQUIVOS GERADOS:")
        print(f"   📊 Estatísticas: {self.paths['stats_file']}")
        print(f"   📁 JSONs individuais: {self.paths['output']}")
        print(f"   📝 Log detalhado: {self.paths['output']}/processamento.log")
        
        # Período de execução
        if self.stats.start_time and self.stats.end_time:
            inicio = datetime.fromisoformat(self.stats.start_time).strftime("%H:%M:%S")
            fim = datetime.fromisoformat(self.stats.end_time).strftime("%H:%M:%S")
            print(f"\n🕐 PERÍODO: {inicio} → {fim}")
        
        print(f"{'='*70}")
        print("🎉 PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
        print(f"{'='*70}")
    
    # ========== MÉTODO PRINCIPAL ==========
    
    async def process_file(self, filename: str = None):
        """
        MÉTODO PRINCIPAL - PROCESSAR ARQUIVO COMPLETO
        
        Orquestra todo o fluxo de processamento:
        1. Inicialização da sessão HTTP
        2. Leitura do arquivo de entrada
        3. Loop de processamento item por item
        4. Geração de relatórios finais
        5. Cleanup de recursos
        
        CONTROLE DE FLUXO:
        - Processamento sequencial com delay configurável
        - Tratamento robusto de erros
        - Logging detalhado
        - Cleanup garantido em finally
        
        Args:
            filename: Nome do arquivo (opcional, usa padrão se None)
            
        Raises:
            Exception: Erros fatais são propagados após logging
        """
        try:
            # 1. Inicializar sessão HTTP assíncrona
            self.session = aiohttp.ClientSession()
            
            # 2. Ler e preparar dados do arquivo
            lines = self.read_input_file(filename)
            self.stats.total_items = len(lines)
            self.stats.start_time = datetime.now().isoformat()
            
            self.print_clean(f"Iniciando processamento de {len(lines)} itens", "🚀")
            
            # 3. Loop principal - processar cada linha
            for i, line in enumerate(lines, 1):
                # Processar item individual
                result = await self.process_item(line, i)
                
                # Armazenar resultado e atualizar estatísticas
                self.results.append(result)
                self.update_statistics(result)
                
                # Exibir progresso detalhado
                self.print_progress(i, len(lines), result)
                
                # Delay entre requests (evita sobrecarga do servidor)
                if i < len(lines):
                    await asyncio.sleep(self.config.FILE_PROCESSING["delay_between_requests"])
            
            # 4. Finalização e relatórios
            self.stats.end_time = datetime.now().isoformat()
            
            # Salvar estatísticas em arquivo JSON
            await self.save_final_statistics()
            
            # Exibir relatório final no console
            self.print_final_summary()
            
        except Exception as e:
            # Tratamento de erros fatais
            self.print_clean(f"Erro fatal: {str(e)}", "💥")
            self.logger.error(traceback.format_exc())
            raise
            
        finally:
            # Cleanup garantido (fechar sessão HTTP)
            if self.session:
                await self.session.close()

# ========== FUNÇÃO PRINCIPAL DE EXECUÇÃO ==========

async def main():
    """
    FUNÇÃO PRINCIPAL DO PROGRAMA
    
    Ponto de entrada que:
    1. Exibe cabeçalho do programa
    2. Carrega e valida configurações
    3. Verifica existência do arquivo de entrada
    4. Executa o processamento
    5. Trata interrupções e erros
    
    TRATAMENTO DE CASOS:
    - Arquivo não encontrado → cria exemplo automaticamente
    - Ctrl+C → interrupção graceful
    - Erros → logging e exit code apropriado
    
    Returns:
        0 se sucesso, 1 se erro
    """
    print("🤖 PROCESSADOR DE ARQUIVO - SERPRO LLM")
    print("="*50)
    
    # Carregar configurações
    config = SerproConfig()
    
    # Criar instância do processador
    processor = FileProcessor()
    
    # Verificar se arquivo de entrada existe
    if not processor.paths["input_file"].exists():
        print(f"❌ Arquivo não encontrado: {processor.paths['input_file']}")
        print("💡 Criando arquivo de exemplo...")
        config.create_sample_input_file()
        print(f"📁 Use o arquivo criado ou coloque seu arquivo em: {processor.paths['input']}")
        return
    
    try:
        # Executar processamento principal
        await processor.process_file()
        
    except KeyboardInterrupt:
        # Interrupção pelo usuário (Ctrl+C)
        print("\n⏹️ Processamento interrompido pelo usuário")
        
    except Exception as e:
        # Outros erros
        print(f"\n💥 Erro: {str(e)}")
        return 1
    
    return 0

# ========== PONTO DE ENTRADA ==========

if __name__ == "__main__":
    """
    EXECUÇÃO PRINCIPAL
    
    Executa a função main() de forma assíncrona e retorna exit code apropriado.
    O asyncio.run() gerencia automaticamente o event loop.
    """
    exit_code = asyncio.run(main())