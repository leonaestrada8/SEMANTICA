# Semântica Consignação API

Sistema de análise semântica para verificação de reclamações de empréstimos consignados usando Serpro LLM.

## Instalação Rápida

```bash
# 1. Clonar/baixar o projeto
# 2. Instalar
chmod +x install.sh
./install.sh

# 3. Configurar credenciais em config.py
CLIENT_ID = "seu_client_id_serpro"
CLIENT_SECRET = "seu_client_secret_serpro"

# 4. Executar
./run.sh
```

## Uso da API

### JSON Estruturado (Recomendado)
```json
{
  "id_termo": "314166",
  "cpf": "4895631478",
  "pratica_vedada": "10,11", 
  "justificativa": "Estou sendo descontado sem autorização"
}
```

### String Delimitada
```json
{
  "input": "314167#4895631478#10,11#Estou sendo descontado sem autorização"
}
```

### Exemplo cURL
```bash
curl -X POST "http://localhost:8000/analise-semantica" \
-H "Content-Type: application/json" \
-d '{"input": "TESTE#123#12#Desconto sem autorização"}'
```

## Endpoints

- `POST /analise-semantica` - Análise principal
- `GET /` - Interface web
- `GET /docs` - Documentação Swagger
- `GET /health` - Status da API
- `WS /ws/semantica-consignacao` - WebSocket tempo real

## Ferramentas

### Teste Manual
```bash
source venv/bin/activate
python teste_manual.py
```

### Processamento em Lote
```bash
source venv/bin/activate
python processador.py
```

## Estrutura

```
├── config.py          # Configuração
├── main.py             # API principal
├── models.py           # Modelos Pydantic
├── serpro_client.py    # Cliente Serpro LLM
├── utils.py            # Utilitários
├── templates/          # Interface web
│   ├── index.html
│   ├── style.css
│   └── script.js
├── teste_manual.py     # Ferramenta teste
├── processador.py      # Processador batch
└── requirements.txt    # Dependências
```

## Classificação

- **APPROVED**: SIM + confiança ≥ 70%
- **REVIEW_REQUIRED**: SIM + confiança 50-69%
- **REJECTED**: NÃO ou confiança < 50%

## Critérios Aceitos

✅ Consignação sem autorização prévia  
✅ Consignação sem crédito do valor  
✅ Desconto de contrato já liquidado  

❌ Rediscussão de contrato (taxas, etc.)  
❌ Solicitação de boletos  

## URLs

- **Interface**: http://localhost:8000
- **Swagger**: http://localhost:8000/docs  
- **Health**: http://localhost:8000/health

## Configuração

Edite `config.py` com suas credenciais Serpro:

```python
CLIENT_ID = "seu_client_id_serpro"
CLIENT_SECRET = "seu_client_secret_serpro"
AMBIENTE = "exp"  # ou "prod"
```

## Desenvolvimento

```bash
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

