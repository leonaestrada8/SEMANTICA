# SEMÂNTICA CONSIGNAÇÃO API v2.0 - Documentação Completa

## 🚀 ENDPOINTS PRINCIPAIS

### 📊 Interface e Dashboard
| Método | Endpoint | Descrição | Uso |
|--------|----------|-----------|-----|
| `GET` | `/` | Interface web principal com dashboard interativo | Acesso via browser |
| `GET` | `/docs` | Interface Swagger UI para testes REST | Desenvolvimento/teste |
| `GET` | `/redoc` | Documentação alternativa da API | Consulta |

### 🧠 Processamento de Análise Semântica
| Método | Endpoint | Descrição | Formato de Entrada |
|--------|----------|-----------|-------------------|
| `POST` | `/analise-semantica` | **Análise via REST (Swagger UI)** | JSON: `{"input": "TERMO#CPF#PRATICA#JUSTIFICATIVA"}` |
| `WebSocket` | `/ws/semantica-consignacao` | Processamento em tempo real | JSON via WebSocket |

### 🔍 Monitoramento e Estatísticas
| Método | Endpoint | Descrição | Resposta |
|--------|----------|-----------|----------|
| `GET` | `/health` | Health check com status de saúde | `{"status": "healthy/warning/critical"}` |
| `GET` | `/error-stats` | Estatísticas detalhadas de erro | Métricas em tempo real |
| `POST` | `/reset-error-stats` | Resetar estatísticas de erro | Confirmação de reset |

### ⚙️ Controle de Processamento
| Método | Endpoint | Descrição | Ação |
|--------|----------|-----------|------|
| `POST` | `/stop-file-processing` | Interromper processamento de arquivo | Parada graceful |

## 🎯 FLUXOS DE USO DETALHADOS

### 1. 🧪 TESTE INDIVIDUAL via Swagger UI
```
1. Acesse: http://localhost:8000/docs
2. Localize: POST /analise-semantica
3. Clique: "Try it out"
4. Input: {"input": "TERMO123#12345678901#Desconto sem autorização#Justificativa aqui"}
5. Execute: Clique "Execute"
6. Resultado: JSON com análise completa
```

### 2. 🖥️ TESTE MANUAL via Interface Web
```
1. Acesse: http://localhost:8000/
2. Dashboard → Seção "Teste Manual"
3. Cole JSON no textarea
4. Clique "Enviar Teste"
5. Veja resultado em tempo real no log
```

### 3. 📁 PROCESSAMENTO EM LOTE
```
1. Acesse: http://localhost:8000/
2. Dashboard → Seção "Processamento de Arquivo"
3. Digite nome do arquivo (ex: 100.txt)
4. Clique "Processar Arquivo"
5. Acompanhe progresso em tempo real
```

### 4. 📊 MONITORAMENTO
```
- Status da API: GET /health
- Métricas detalhadas: GET /error-stats
- Dashboard visual: GET / (seção estatísticas)
```

## 📋 FORMATOS DE ENTRADA ACEITOS

### Formato Padrão (4 campos obrigatórios)
```
IDTERMO#CPF#PRATICA VEDADA#JUSTIFICATIVA
```

### Exemplos Válidos
```json
{
  "input": "TERMO001#12345678901#Desconto sem autorização#Estou sendo descontado sem ter autorizado"
}
```

```json
{
  "input": "TERMO002#98765432109#Contrato liquidado#Continuam descontando valor de contrato quitado"
}
```

## 📤 FORMATOS DE RESPOSTA

### Resposta de Sucesso
```json
{
  "status": "APPROVED",
  "parsed_data": {
    "id_termo": "TERMO123",
    "cpf": "12345678901",
    "pratica_vedada": "Desconto sem autorização",
    "justificativa": "Justificativa completa..."
  },
  "diagnostico_llm": "SIM",
  "confidence": 0.85,
  "justificativa_llm": "Caso válido - desconto sem autorização",
  "timestamp": "2025-01-01T10:30:00",
  "processing_time": 2.34,
  "analysis_id": "abc12345"
}
```

### Resposta de Erro
```json
{
  "status": "ERROR",
  "error": "Descrição do erro",
  "error_type": "PARSE_ERROR",
  "timestamp": "2025-01-01T10:30:00",
  "processing_time": 0.12
}
```

## 🎯 STATUS DE CLASSIFICAÇÃO

| Status | Condição | Ação Recomendada |
|--------|----------|------------------|
| `APPROVED` | SIM + confiança ≥ 0.7 | ✅ Aprovação automática |
| `REVIEW_REQUIRED` | SIM + 0.5 ≤ confiança < 0.7 | ⚠️ Revisão manual |
| `REJECTED` | NÃO ou confiança < 0.5 | ❌ Rejeição |
| `ERROR` | Falha no processamento | 💥 Verificar erro |

## 🔧 CONFIGURAÇÃO E AMBIENTE

### Arquivos de Configuração
- `0_config.py`: Configurações centralizadas
- `ca-pro.pem`: Certificado SSL Serpro (baixado automaticamente)

### Variáveis de Ambiente Importantes
```bash
SERPRO_AMBIENTE=exp          # ou 'prod'
SERPRO_MODEL=deepseek-r1-distill-qwen-14b
REQUEST_TIMEOUT=60
MAX_RETRIES=5
```

### Estrutura de Pastas
```
projeto/
├── 1_api_main.py           # API principal
├── 0_config.py             # Configurações
├── justificativas/         # Arquivos de entrada
├── JSON/                   # Resultados individuais
└── logs/                   # Logs do sistema
```