# H_teste_manual_llm.py - FERRAMENTA DE TESTE MANUAL SERPRO LLM
"""
UTILITÁRIO INTERATIVO PARA TESTE DIRETO DO SERPRO LLM

Esta ferramenta de linha de comando permite:
1. Testar justificativas diretamente no Serpro LLM
2. Verificar conectividade e autenticação
3. Analisar respostas do LLM em tempo real
4. Debugging e desenvolvimento de prompts
5. Validação de configurações
6. Processamento de linhas completas com salvamento automático

PROPÓSITO:
- Ferramenta de desenvolvimento e debugging
- Teste rápido de prompts e justificativas
- Verificação de conectividade com Serpro LLM
- Análise de qualidade das respostas
- Prototipagem de novos prompts
- Processamento individual com salvamento em JSON

FORMATOS DE ENTRADA ACEITOS:
1. Justificativa simples: "Texto da justificativa aqui"
2. Linha completa: "IDTERMO#CPF#PRATICA VEDADA#JUSTIFICATIVA"

DIFERENÇAS DA API WEB:
- Modo interativo via linha de comando
- Sem interface web ou WebSocket
- Foco em teste e debugging
- Execução única por vez
- Feedback detalhado sobre parsing
- Salvamento automático em JSON quando linha completa

FLUXO DE EXECUÇÃO:
1. Configuração inicial e autenticação
2. Loop interativo para entrada de justificativas/linhas
3. Para cada entrada:
   - Detecção do formato (simples ou completa)
   - Parsing da linha se formato completo
   - Criação do prompt especializado
   - Chamada ao Serpro LLM
   - Parsing da resposta (múltiplas estratégias)
   - Salvamento em JSON se linha completa
   - Exibição formatada dos resultados
4. Opção de continuar ou sair
"""

# ========== IMPORTS E DEPENDÊNCIAS ==========
import asyncio         # Para programação assíncrona (chamadas LLM)
import aiohttp          # Cliente HTTP assíncrono para Serpro LLM
import requests         # Cliente HTTP síncrono (autenticação)
import json             # Para parsing e formatação JSON
import os               # Para sistema de arquivos e variáveis ambiente
import sys              # Para manipulação de imports
import time             # Para medição de tempo de resposta
from datetime import datetime  # Para timestamps
import uuid             # Para geração de IDs únicos
import re               # Para regex (extração JSON de texto)
from pathlib import Path       # Para manipulação de caminhos
from dataclasses import dataclass, asdict  # Para estruturas de dados

# ========== IMPORT DA CONFIGURAÇÃO CENTRALIZADA ==========
# Importação dinâmica do arquivo 0_config.py para reutilizar configurações
sys.path.append(os.path.dirname(__file__))
import importlib.util
spec = importlib.util.spec_from_file_location("config", "0_config.py")
config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_module)
SerproConfig = config_module.SerproConfig

# ========== ESTRUTURAS DE DADOS ==========

@dataclass
class TesteResult:
    """
    RESULTADO ESTRUTURADO DO TESTE MANUAL
    
    Armazena todas as informações sobre o processamento de uma justificativa:
    - Dados originais (ID, CPF, prática vedada, justificativa)  
    - Resultado da análise LLM (diagnóstico, confiança, justificativa)
    - Metadados (tempo, modelo, ambiente, fallback)
    
    Similar ao ProcessingResult do E_processador_arquivo.py mas
    adaptado para teste manual com informações adicionais.
    """
    id_termo: str = "MANUAL"               # ID do termo (ou "MANUAL" se justificativa simples)
    cpf: str = ""                          # CPF do usuário
    pratica_vedada: str = ""               # Tipo de prática vedada
    justificativa: str = ""                # Justificativa completa do usuário
    diagnostico_llm: str = ""              # Resposta do LLM: SIM/NÃO
    confidence: float = 0.0                # Nível de confiança (0.0 a 1.0)
    justificativa_llm: str = ""            # Explicação do LLM sobre a decisão
    processing_time: float = 0.0           # Tempo gasto no processamento (segundos)
    timestamp: str = ""                    # Timestamp ISO 8601 do processamento
    model_used: str = ""                   # Modelo LLM utilizado
    ambiente_serpro: str = ""              # Ambiente Serpro (exp/prod)
    fallback_used: bool = False            # Se foi usado fallback semântico
    request_id: str = ""                   # ID único da requisição
    
    def __post_init__(self):
        """Gera timestamp e request_id automaticamente se não fornecidos"""
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.request_id:
            self.request_id = str(uuid.uuid4())

# ========== CLASSE PRINCIPAL DE TESTE ==========

class TesteLLMManual:
    """
    CLASSE PRINCIPAL PARA TESTE MANUAL DO SERPRO LLM
    
    Implementa um cliente simplificado e direto para:
    - Autenticação OAuth2 com Serpro LLM
    - Configuração automática de certificados SSL
    - Criação de prompts especializados
    - Chamadas assíncronas ao LLM
    - Parsing inteligente de respostas
    - Fallback para respostas não-JSON
    
    CARACTERÍSTICAS:
    - Interface simples focada em teste
    - Sem sistema de retry complexo (para debugging)
    - Feedback detalhado sobre cada etapa
    - Medição de tempo de resposta
    - Detecção de uso de fallback
    
    DIFERENÇAS DA VERSÃO PRODUÇÃO:
    - Sem sistema robusto de retry
    - Sem monitoramento de estatísticas
    - Sem categorização avançada de erros
    - Foco em simplicidade e clareza
    """
    
    def __init__(self):
        """
        INICIALIZAÇÃO DA CLASSE DE TESTE
        
        1. Carrega configurações centralizadas
        2. Inicializa token como None (será obtido quando necessário)
        3. Configura certificados SSL do Serpro
        4. Configura pasta de saída JSON
        """
        # Carregar configurações do arquivo 0_config.py
        self.config = SerproConfig()
        
        # Token de acesso (será obtido dinamicamente)
        self.access_token = None
        
        # Configurar certificados SSL automaticamente
        self.setup_certificates()
        
        # Configurar pasta de saída JSON
        self.setup_output_folder()
        
    def setup_output_folder(self):
        """
        CONFIGURAÇÃO DA PASTA DE SAÍDA JSON
        
        Cria pasta ./JSON se não existir para salvar resultados
        individuais quando processando linhas completas.
        """
        self.json_folder = Path("./JSON")
        self.json_folder.mkdir(exist_ok=True)
        
    def detect_input_format(self, entrada: str) -> str:
        """
        DETECÇÃO INTELIGENTE DO FORMATO DE ENTRADA
        
        Identifica se a entrada é:
        1. Linha completa: IDTERMO#CPF#PRATICA VEDADA#JUSTIFICATIVA (4+ campos)
        2. Justificativa simples: Texto livre
        
        Args:
            entrada: String de entrada do usuário
            
        Returns:
            str: "linha_completa" ou "justificativa_simples"
        """
        # Contar campos separados por #
        campos = entrada.split("#")
        
        # Se tem 4 ou mais campos, considerar linha completa
        if len(campos) >= 4:
            return "linha_completa"
        else:
            return "justificativa_simples"
    
    def parse_linha_completa(self, linha: str) -> dict:
        """
        PARSING DE LINHA COMPLETA NO FORMATO PADRÃO
        
        Converte string no formato: IDTERMO#CPF#PRATICA VEDADA#JUSTIFICATIVA
        Para dicionário com campos nomeados.
        
        TRATAMENTO ESPECIAL:
        - Se justificativa contém #, preserva o conteúdo usando join()
        - Exemplo: "123#456#12#Texto com # no meio" → justificativa = "Texto com # no meio"
        
        Args:
            linha: String no formato delimitado por #
            
        Returns:
            dict: Campos estruturados
            
        Raises:
            ValueError: Se formato da linha for inválido (menos de 4 campos)
        """
        parts = linha.split("#")
        if len(parts) < 4:
            raise ValueError(f"Formato inválido. Esperado: IDTERMO#CPF#PRATICA VEDADA#JUSTIFICATIVA. Recebido: {linha}")
        
        return {
            "id_termo": parts[0].strip(),
            "cpf": parts[1].strip(),
            "pratica_vedada": parts[2].strip(),
            "justificativa": "#".join(parts[3:]).strip()  # Join caso justificativa contenha #
        }
        
    def setup_certificates(self):
        """
        CONFIGURAÇÃO AUTOMÁTICA DE CERTIFICADOS SSL SERPRO
        
        O Serpro requer certificados específicos para conexões HTTPS.
        Este método:
        1. Verifica se certificado já existe localmente
        2. Se não existe, baixa automaticamente do site oficial
        3. Configura variáveis de ambiente para uso pelo requests/aiohttp
        
        CERTIFICADO SERPRO:
        - URL oficial: https://lcrspo.serpro.gov.br/ca/ca-pro.pem
        - Arquivo local: ca-pro.pem
        - Necessário para todas as conexões HTTPS com Serpro
        
        Raises:
            Exception: Se falhar ao baixar ou configurar certificado
        """
        cert_file = self.config.CERT_FILE
        
        # Verificar se certificado já existe
        if not os.path.exists(cert_file):
            try:
                print("📥 Baixando certificado SSL...")
                
                # Baixar certificado oficial (temporariamente sem verificação SSL)
                response = requests.get(self.config.CERT_URL, verify=False, timeout=10)
                response.raise_for_status()
                
                # Salvar certificado localmente
                with open(cert_file, 'wb') as f:
                    f.write(response.content)
                print("✅ Certificado SSL configurado")
                
            except Exception as e:
                print(f"❌ Erro ao baixar certificado: {e}")
                raise
        
        # Configurar variáveis de ambiente para uso do certificado
        os.environ["REQUESTS_CA_BUNDLE"] = cert_file
        os.environ["SSL_CERT_FILE"] = cert_file
    
    def get_access_token(self):
        """
        OBTENÇÃO DE TOKEN DE ACESSO OAUTH2
        
        Implementa fluxo OAuth2 Client Credentials simplificado:
        1. Prepara dados da requisição
        2. Faz autenticação com credenciais configuradas
        3. Extrai access_token da resposta
        4. Armazena token para uso posterior
        
        FLUXO OAUTH2 CLIENT CREDENTIALS:
        POST /oauth2/token
        - grant_type: client_credentials
        - Auth: Basic (client_id, client_secret)
        
        RESPOSTA ESPERADA:
        {
            "access_token": "jwt_token_aqui",
            "expires_in": 3600,
            "token_type": "Bearer"
        }
        
        Returns:
            bool: True se token obtido com sucesso, False caso contrário
        """
        try:
            print("\n🔑 Obtendo token de acesso...")
            
            # Obter URLs baseadas no ambiente (exp/prod)
            urls = self.config.get_urls()
            
            # Preparar dados OAuth2 Client Credentials
            dados = {"grant_type": "client_credentials"}
            
            # Fazer requisição de autenticação
            resposta = requests.post(
                urls["token"],
                data=dados,
                auth=(self.config.CLIENT_ID, self.config.CLIENT_SECRET),
                timeout=self.config.REQUEST_TIMEOUT
            )
            
            # Verificar sucesso da autenticação
            if resposta.status_code != 200:
                print(f"❌ Erro na autenticação: {resposta.status_code}")
                print(f"Resposta: {resposta.text}")
                return False
            
            # Extrair token da resposta
            token_data = resposta.json()
            self.access_token = token_data["access_token"]
            print("✅ Token obtido com sucesso")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao obter token: {e}")
            return False
    
    def create_llm_prompt(self, justificativa: str) -> str:
        """
        CRIAÇÃO DO PROMPT ESPECIALIZADO PARA ANÁLISE SEMÂNTICA
        
        Cria o prompt padrão usado em todo o sistema para:
        1. Definir o papel do LLM como especialista em consignados
        2. Especificar critérios exatos de aprovação
        3. Listar exclusões (fora do escopo)
        4. Solicitar formato de resposta JSON estruturado
        5. Incluir a justificativa específica do usuário
        
        ESTRUTURA DO PROMPT:
        1. Definição de papel (especialista em empréstimos consignados)
        2. Critérios de aprovação (3 categorias principais)
        3. Exclusões (rediscussão de contratos, boletos)
        4. Instruções de formato JSON
        5. Especificação de campos obrigatórios
        6. Justificativa do usuário
        
        CRITÉRIOS DE APROVAÇÃO:
        • Consignação sem autorização prévia e formal
        • Consignação sem correspondente crédito
        • Desconto de contrato já liquidado
        
        EXCLUSÕES (DEVEM SER NEGADAS):
        • Rediscussão de contrato assinado
        • Requisições de boletos
        
        Args:
            justificativa: Texto da justificativa enviada pelo usuário
            
        Returns:
            str: Prompt completo formatado para o LLM
        """
        return f"""Você é um especialista em empréstimos consignados.
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
    
    async def call_serpro_llm(self, prompt: str, dados_entrada: dict = None):
        """
        CHAMADA PRINCIPAL PARA O SERPRO LLM
        
        Executa comunicação assíncrona com Serpro LLM:
        1. Verifica se há token válido (obtém se necessário)
        2. Prepara headers e payload
        3. Faz requisição HTTP POST assíncrona
        4. Mede tempo de resposta
        5. Trata erros HTTP
        6. Parseia resposta usando estratégias múltiplas
        7. Retorna TesteResult estruturado
        
        FORMATO DO PAYLOAD (OpenAI-compatible):
        {
            "model": "deepseek-r1-distill-qwen-14b",
            "messages": [{"role": "user", "content": "prompt"}],
            "temperature": 0.1,
            "max_tokens": 500,
            ...outras configurações do LLM
        }
        
        MEDIÇÃO DE PERFORMANCE:
        - Tempo de resposta em segundos
        - Sucesso/falha da requisição
        - Tamanho da resposta
        
        Args:
            prompt: Prompt formatado para enviar ao LLM
            dados_entrada: Dados da entrada (id_termo, cpf, etc.) para resultado estruturado
            
        Returns:
            TesteResult: Resultado estruturado completo, ou None se erro
        """
        # Garantir que dados_entrada existe
        if dados_entrada is None:
            dados_entrada = {"justificativa": "Teste manual"}
            
        try:
            # 1. Garantir que temos token válido
            if not self.access_token:
                if not self.get_access_token():
                    return None
            
            print("🧠 Enviando para Serpro LLM...")
            
            # 2. Preparar URLs e headers
            urls = self.config.get_urls()
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # 3. Preparar payload compatível com OpenAI API
            payload = {
                "model": self.config.MODEL_NAME,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                **self.config.LLM_CONFIG  # temperature, max_tokens, etc.
            }
            
            # 4. Iniciar medição de tempo
            start_time = time.time()
            
            # 5. Fazer requisição assíncrona
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{urls['api']}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.REQUEST_TIMEOUT)
                ) as response:
                    
                    # 6. Calcular tempo de resposta
                    response_time = time.time() - start_time
                    
                    # 7. Verificar sucesso
                    if response.status == 200:
                        result = await response.json()
                        print(f"✅ Resposta recebida em {response_time:.2f}s")
                        return self.parse_llm_response(result, response_time, dados_entrada)
                    else:
                        # 8. Tratar erro HTTP
                        error_text = await response.text()
                        print(f"❌ Erro HTTP {response.status}: {error_text}")
                        return None
                        
        except Exception as e:
            print(f"❌ Erro na chamada LLM: {e}")
            return None
    
    def parse_llm_response(self, llm_response: dict, response_time: float, dados_entrada: dict) -> TesteResult:
        """
        PARSING INTELIGENTE DE RESPOSTA DO LLM COM MÚLTIPLAS ESTRATÉGIAS
        
        O Serpro LLM pode retornar diferentes formatos de resposta:
        1. JSON puro e válido
        2. JSON embutido em texto/markdown  
        3. Texto livre sem JSON válido
        
        ESTRATÉGIAS DE PARSING (em ordem de tentativa):
        1. **JSON DIRETO**: Se conteúdo começa com '{', tenta JSON.loads()
        2. **EXTRAÇÃO REGEX**: Busca padrões JSON no meio do texto
        3. **FALLBACK INTELIGENTE**: Análise semântica por palavras-chave
        
        RESULTADO ESTRUTURADO:
        - Cria TesteResult com todos os dados do processamento
        - Inclui metadados de performance e configuração
        - Preserva informações originais de entrada
        
        Args:
            llm_response: Resposta bruta do Serpro LLM
            response_time: Tempo da requisição em segundos
            dados_entrada: Dados originais da entrada (id_termo, cpf, etc.)
            
        Returns:
            TesteResult: Resultado estruturado completo, ou None se erro total
        """
        try:
            # Extrair conteúdo principal da resposta
            content = llm_response["choices"][0]["message"]["content"]
            
            # Inicializar flags
            fallback_used = False
            
            # ESTRATÉGIA 1: JSON DIRETO
            try:
                if content.strip().startswith('{'):
                    parsed_content = json.loads(content)
                else:
                    # ESTRATÉGIA 2: EXTRAÇÃO VIA REGEX
                    # Regex para encontrar JSON complexo (incluindo objetos aninhados)
                    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
                    if json_match:
                        parsed_content = json.loads(json_match.group())
                    else:
                        # ESTRATÉGIA 3: FALLBACK INTELIGENTE
                        parsed_content = self.create_fallback_response(content)
                        fallback_used = True
                        
            except json.JSONDecodeError:
                # Se JSON inválido, usar fallback
                parsed_content = self.create_fallback_response(content)
                fallback_used = True
            
            # Criar resultado estruturado
            resultado = TesteResult(
                id_termo=dados_entrada.get("id_termo", "MANUAL"),
                cpf=dados_entrada.get("cpf", ""),
                pratica_vedada=dados_entrada.get("pratica_vedada", ""),
                justificativa=dados_entrada.get("justificativa", ""),
                diagnostico_llm=parsed_content.get("diagnosticoLLM", ""),
                confidence=parsed_content.get("confidence", 0.0),
                justificativa_llm=parsed_content.get("justificativaLLM", ""),
                processing_time=response_time,
                model_used=self.config.MODEL_NAME,
                ambiente_serpro=self.config.AMBIENTE,
                fallback_used=fallback_used,
                request_id=parsed_content.get("requestId", str(uuid.uuid4()))
            )
            
            return resultado
            
        except Exception as e:
            print(f"❌ Erro ao parsear resposta: {e}")
            return None
    
    async def save_result_json(self, resultado: TesteResult):
        """
        SALVAMENTO DO RESULTADO EM ARQUIVO JSON
        
        Salva o resultado estruturado em arquivo JSON na pasta ./JSON
        com formato: idtermo_YYYYMMDD_HHMMSS.json
        
        FORMATO DO ARQUIVO:
        - Nome: {id_termo}_{data}_{hora}.json
        - Conteúdo: Todos os dados do TesteResult em formato JSON
        - Encoding: UTF-8 
        - Formatação: Indentado para legibilidade
        
        Args:
            resultado: TesteResult com dados completos do processamento
        """
        try:
            # Gerar timestamp para nome do arquivo
            now = datetime.now()
            timestamp_str = now.strftime("%Y%m%d_%H%M%S")
            
            # Criar nome do arquivo
            filename = f"{resultado.id_termo}_{timestamp_str}.json"
            filepath = self.json_folder / filename
            
            # Salvar resultado em JSON
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(asdict(resultado), f, indent=2, ensure_ascii=False)
            
            print(f"💾 Resultado salvo em: {filepath}")
            
        except Exception as e:
            print(f"❌ Erro ao salvar JSON: {e}")
    
    def create_fallback_response(self, content: str):
        """
        SISTEMA DE FALLBACK INTELIGENTE PARA ANÁLISE SEMÂNTICA
        
        Quando o LLM não retorna JSON válido, este método faz:
        1. Análise semântica do texto por palavras-chave
        2. Contagem de indicadores de aprovação vs rejeição
        3. Cálculo de diagnóstico baseado na análise
        4. Estimativa de confiança baseada na força dos indicadores
        5. Geração de resposta no formato padrão
        
        ALGORITMO DE ANÁLISE:
        - **Palavras de Aprovação**: sim, válido, procedente, autorização, etc.
        - **Palavras de Rejeição**: não, inválido, taxa, boleto, etc.
        - **Diagnóstico**: Categoria com mais ocorrências
        - **Confiança**: Baseada na quantidade e força dos indicadores
        
        CÁLCULO DE CONFIANÇA:
        - Base: 0.5 (neutro)
        - +0.1 por palavra indicativa (máximo 0.9)
        - Limitado a 0.9 para manter margem de incerteza
        
        Args:
            content: Texto livre da resposta do LLM
            
        Returns:
            dict: Resposta no formato padrão com diagnóstico inferido
        """
        content_lower = content.lower()
        
        # Listas de palavras-chave para análise semântica
        approve_words = ["sim", "aprovado", "válido", "procedente", "autorização", "liquidado", "crédito"]
        reject_words = ["não", "rejeitado", "inválido", "taxa", "boleto", "renegociar"]
        
        # Contar ocorrências de cada categoria
        approve_count = sum(1 for word in approve_words if word in content_lower)
        reject_count = sum(1 for word in reject_words if word in content_lower)
        
        # Determinar diagnóstico baseado na análise
        if approve_count > reject_count:
            diagnostico = "SIM"
            # Confiança baseada na força dos indicadores (máximo 0.9)
            confidence = min(0.9, 0.5 + (approve_count * 0.1))
        else:
            diagnostico = "NÃO"
            confidence = min(0.9, 0.5 + (reject_count * 0.1))
            
        # Retornar resposta no formato padrão
        return {
            "requestId": str(uuid.uuid4()),
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00"),
            "diagnosticoLLM": diagnostico,
            "justificativaLLM": content[:144],  # Limitar a 144 caracteres
            "confidence": confidence,
            "status": "success"
        }

# ========== FUNÇÃO PRINCIPAL INTERATIVA ==========

async def main():
    """
    LOOP PRINCIPAL INTERATIVO DO TESTE MANUAL
    
    Implementa interface de linha de comando para:
    1. Inicialização e exibição de configurações
    2. Loop interativo para entrada de justificativas/linhas completas
    3. Processamento e exibição de resultados
    4. Controle de continuação/saída
    5. Salvamento automático quando linha completa
    
    FLUXO DE EXECUÇÃO:
    1. **Inicialização**:
       - Cria instância de TesteLLMManual
       - Exibe configurações atuais
       - Configura certificados automaticamente
    
    2. **Loop Interativo**:
       - Solicita entrada do usuário
       - Detecta formato (justificativa simples ou linha completa)
       - Para linha completa: parseia dados e salva JSON
       - Para justificativa simples: processa normalmente
       - Cria prompt especializado
       - Chama Serpro LLM
       - Parseia e exibe resposta
       - Pergunta se quer continuar
    
    3. **Exibição de Resultados**:
       - JSON formatado completo
       - Resumo executivo
       - Métricas de performance
       - Alertas sobre fallback
    
    COMANDOS DE SAÍDA:
    - 'sair', 'exit', 'quit', '' (vazio)
    
    COMANDOS DE CONTINUAÇÃO:
    - Enter: continuar
    - 'n', 'no', 'nao', 'não': parar
    """
    print("🧪 TESTE MANUAL SERPRO LLM")
    print("=" * 50)
    
    # 1. Inicializar sistema de teste
    teste = TesteLLMManual()
    
    # 2. Exibir configurações atuais
    print(f"🤖 Modelo: {teste.config.MODEL_NAME}")
    print(f"🌐 Ambiente: {teste.config.AMBIENTE}")
    print(f"⏱️ Timeout: {teste.config.REQUEST_TIMEOUT}s")
    print(f"📁 Pasta JSON: {teste.json_folder}")
    
    # 3. Loop principal interativo
    while True:
        print("\n" + "=" * 50)
        print("📝 DIGITE SUA ENTRADA")
        print("=" * 50)
        print("Formatos aceitos:")
        print("1. Justificativa simples: 'Estou sendo descontado sem autorização'")
        print("2. Linha completa: 'TERMO123#12345678901#12#Desconto sem autorização'")
        print()
        
        # 4. Solicitar entrada do usuário
        print("Digite sua entrada (ou 'sair' para terminar):")
        entrada = input("> ").strip()
        
        # 5. Verificar comandos de saída
        if entrada.lower() in ['sair', 'exit', 'quit', '']:
            print("👋 Encerrando teste...")
            break
        
        # 6. Detectar formato da entrada
        formato = teste.detect_input_format(entrada)
        print(f"\n🔍 Formato detectado: {formato}")
        
        # 7. Processar entrada baseado no formato
        if formato == "linha_completa":
            try:
                # Parsear linha completa
                dados_entrada = teste.parse_linha_completa(entrada)
                print(f"📋 Dados parseados:")
                print(f"   ID Termo: {dados_entrada['id_termo']}")
                print(f"   CPF: {dados_entrada['cpf']}")
                print(f"   Prática Vedada: {dados_entrada['pratica_vedada']}")
                print(f"   Justificativa: {dados_entrada['justificativa'][:100]}...")
                
                # Usar justificativa para o prompt
                justificativa_para_prompt = dados_entrada['justificativa']
                
            except ValueError as e:
                print(f"❌ Erro no formato da linha: {e}")
                continue
        else:
            # Entrada simples - toda a entrada é a justificativa
            dados_entrada = {"justificativa": entrada}
            justificativa_para_prompt = entrada
            print(f"📋 Justificativa recebida: {entrada[:100]}...")
        
        # 8. Criar prompt especializado
        prompt = teste.create_llm_prompt(justificativa_para_prompt)
        
        # 9. Chamar Serpro LLM
        resultado = await teste.call_serpro_llm(prompt, dados_entrada)
        
        # 10. Processar e exibir resultados
        if resultado:
            print("\n" + "=" * 50)
            print("📊 RESPOSTA DO SERPRO LLM")
            print("=" * 50)
            
            # 11. Exibir JSON formatado completo
            print(json.dumps(asdict(resultado), indent=2, ensure_ascii=False))
            
            # 12. Salvar JSON se linha completa
            if formato == "linha_completa":
                await teste.save_result_json(resultado)
            
            # 13. Exibir resumo executivo
            print("\n📈 RESUMO:")
            print(f"   🎯 Diagnóstico: {resultado.diagnostico_llm}")
            print(f"   📊 Confiança: {resultado.confidence:.2f}")
            print(f"   ⏱️ Tempo: {resultado.processing_time:.2f}s")
            print(f"   🧠 Justificativa: {resultado.justificativa_llm[:144]}.")
            
            # 14. Alertar sobre uso de fallback
            if resultado.fallback_used:
                print("   ⚠️ Fallback usado (LLM não retornou JSON válido)")
                
            # 15. Mostrar metadados adicionais
            print(f"   🆔 Request ID: {resultado.request_id}")
            print(f"   🤖 Modelo: {resultado.model_used}")
            print(f"   🌐 Ambiente: {resultado.ambiente_serpro}")
            
        else:
            print("❌ Falha na comunicação com Serpro LLM")
        
        # 16. Perguntar sobre continuação
        print("\n🔄 Deseja fazer outro teste? (Enter = sim, 'n' = não)")
        continuar = input("> ").strip().lower()
        if continuar in ['n', 'no', 'nao', 'não']:
            break

# ========== FUNÇÃO WRAPPER SÍNCRONA ==========

def run_teste():
    """
    WRAPPER SÍNCRONO PARA EXECUÇÃO DO TESTE
    
    Executa a função assíncrona main() em um event loop:
    - Trata interrupção por Ctrl+C gracefully
    - Captura e exibe erros fatais
    - Garante cleanup adequado
    
    TRATAMENTO DE EXCEÇÕES:
    - KeyboardInterrupt: Usuário pressionou Ctrl+C
    - Exception: Outros erros inesperados
    """
    try:
        # Executar função principal assíncrona
        asyncio.run(main())
    except KeyboardInterrupt:
        # Interrupção pelo usuário (Ctrl+C)
        print("\n🛑 Teste interrompido pelo usuário")
    except Exception as e:
        # Outros erros inesperados
        print(f"\n💥 Erro fatal: {e}")

# ========== PONTO DE ENTRADA ==========

if __name__ == "__main__":
    """
    EXECUÇÃO PRINCIPAL DO SCRIPT
    
    Ponto de entrada quando script é executado diretamente:
    - Chama função wrapper síncrona
    - Permite execução via: python H_teste_manual_llm.py
    """
    run_teste()