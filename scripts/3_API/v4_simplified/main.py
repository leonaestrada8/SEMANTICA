# main.py
import asyncio
import time
import uuid
import json
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from models import SemanticaInput, SemanticaResponse
from serpro_client import SerproClient
from utils import *
from config import *
from logger import semantic_logger

# Variáveis globais
serpro_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global serpro_client
    
    print("🚀 Iniciando Semântica Consignação API")
    semantic_logger.log_info("=== API INICIADA ===", "STARTUP")
    
    setup_folders()
    serpro_client = SerproClient()
    
    semantic_logger.log_info("Serpro Client inicializado", "STARTUP")
    
    yield
    
    print("⏹️ Encerrando API")
    semantic_logger.log_info("=== API ENCERRADA ===", "SHUTDOWN")

# Criar app FastAPI
app = FastAPI(
    title="Semântica Consignação API",
    version="3.2",
    description="API de Análise Semântica para Empréstimos Consignados usando Serpro LLM - Apenas JSON Estruturado",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir arquivos estáticos
app.mount("/static", StaticFiles(directory="templates"), name="static")

@app.get("/", response_class=HTMLResponse)
async def web_interface():
    """Interface web"""
    try:
        with open("templates/index.html", "r", encoding="utf-8") as f:
            semantic_logger.log_info("Interface web acessada", "WEB")
            return HTMLResponse(f.read())
    except Exception as e:
        semantic_logger.log_error("WEB_INTERFACE", e)
        raise HTTPException(500, "Erro ao carregar interface")

@app.post("/analise-semantica", response_model=SemanticaResponse)
async def analise_semantica(entrada: SemanticaInput):
    """
    Análise semântica de justificativas usando Serpro LLM.
    
    Aceita apenas JSON estruturado com os campos:
    - id_termo: Identificador único do termo
    - cpf: CPF do cliente (11 dígitos)
    - pratica_vedada: Código da prática vedada
    - justificativa: Texto com no mínimo 10 caracteres
    """
    start_time = time.time()
    analysis_id = str(uuid.uuid4())[:8]
    
    try:
        # Log da entrada
        semantic_logger.log_info(f"Nova análise iniciada | ID: {analysis_id} | Termo: {entrada.id_termo}", "API_REQUEST")
        
        # Log da justificativa (preview)
        justificativa_preview = entrada.justificativa[:100] + "..." if len(entrada.justificativa) > 100 else entrada.justificativa
        semantic_logger.log_info(f"Justificativa: {justificativa_preview}", f"ANALYSIS_{analysis_id}")
        
        # Criar prompt e chamar LLM
        prompt = create_prompt(entrada.justificativa)
        llm_start_time = time.time()
        llm_result = await serpro_client.call_llm(prompt)
        llm_processing_time = time.time() - llm_start_time
        
        # Log da chamada LLM
        semantic_logger.log_llm_call(prompt, llm_result, processing_time=llm_processing_time)
        
        # Classificar resultado
        diagnostico = llm_result.get("diagnosticoLLM", "NÃO")
        confidence = llm_result.get("confidence", 0.5)
        status = classify_result(diagnostico, confidence)
        
        processing_time = time.time() - start_time
        
        # Criar resposta
        response = SemanticaResponse(
            status=status,
            diagnostico_llm=diagnostico,
            confidence=confidence,
            justificativa_llm=llm_result.get("justificativaLLM", ""),
            processing_time=processing_time,
            analysis_id=analysis_id
        )
        
        # Log do resultado
        semantic_logger.log_api_request(
            endpoint="analise-semantica",
            result=response.dict(),
            processing_time=processing_time
        )
        
        update_stats()
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        # Log do erro
        semantic_logger.log_error("API_ANALYSIS", e, {
            "analysis_id": analysis_id,
            "termo": entrada.id_termo if hasattr(entrada, 'id_termo') else "UNKNOWN"
        })
        
        update_stats(error=True)
        raise HTTPException(500, f"Erro interno: {str(e)}")

@app.websocket("/ws/semantica-consignacao")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket para tempo real"""
    client_id = str(uuid.uuid4())[:8]
    
    try:
        await websocket.accept()
        semantic_logger.log_websocket_event("CONNECT", {"client_id": client_id})
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            semantic_logger.log_websocket_event("MESSAGE_RECEIVED", {
                "client_id": client_id,
                "action": message.get("action", "unknown")
            })
            
            if message.get("action") == "process_file":
                await process_file_ws(websocket, message.get("filename", "100.txt"), client_id)
            else:
                # Processar entrada individual JSON
                try:
                    entrada = SemanticaInput(**message)
                    result = await analise_semantica(entrada)
                    await websocket.send_text(result.json())
                    
                    semantic_logger.log_websocket_event("INDIVIDUAL_ANALYSIS", {
                        "client_id": client_id,
                        "status": result.status
                    })
                except Exception as e:
                    error_msg = str(e)
                    await websocket.send_text(json.dumps({"error": error_msg}))
                    semantic_logger.log_websocket_event("PROCESSING_ERROR", {
                        "client_id": client_id,
                        "error": error_msg
                    })
                    
    except Exception as e:
        semantic_logger.log_websocket_event("DISCONNECT", {
            "client_id": client_id,
            "error": str(e)
        })

async def process_file_ws(websocket: WebSocket, filename: str, client_id: str):
    """Processamento de arquivo via WebSocket"""
    try:
        semantic_logger.log_info(f"Iniciando processamento de arquivo: {filename}", f"FILE_PROC_{client_id}")
        
        file_path = Path(INPUT_FOLDER) / filename
        if not file_path.exists():
            error_msg = "Arquivo não encontrado"
            await websocket.send_text(json.dumps({"error": error_msg}))
            semantic_logger.log_error("FILE_PROCESSING", error_msg, {"filename": filename})
            return
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        
        # Pular cabeçalho se existir
        if lines and lines[0].startswith("IDTERMO#CPF"):
            lines = lines[1:]
        
        total = len(lines)
        results_summary = {"approved": 0, "rejected": 0, "review_required": 0, "errors": 0}
        
        await websocket.send_text(json.dumps({
            "status": "started",
            "total": total
        }))
        
        semantic_logger.log_info(f"Processando {total} itens do arquivo {filename}", f"FILE_PROC_{client_id}")
        
        for i, line in enumerate(lines, 1):
            try:
                data = parse_line(line)
                
                # Criar entrada JSON estruturada
                entrada = SemanticaInput(
                    id_termo=data["id_termo"],
                    cpf=data["cpf"],
                    pratica_vedada=data["pratica_vedada"],
                    justificativa=data["justificativa"]
                )
                
                # Processar
                result = await analise_semantica(entrada)
                
                # Atualizar sumário
                results_summary[result.status.lower()] += 1
                
                result_data = {
                    "progress": f"{i}/{total}",
                    "percentage": round((i/total) * 100, 1),
                    "item": data["id_termo"],
                    "status": result.status,
                    "diagnostico": result.diagnostico_llm,
                    "confidence": result.confidence
                }
                
                await websocket.send_text(json.dumps(result_data))
                await asyncio.sleep(1)  # Delay entre itens
                
            except Exception as e:
                results_summary["errors"] += 1
                error_msg = f"Erro no item {i}: {str(e)}"
                await websocket.send_text(json.dumps({"error": error_msg}))
                semantic_logger.log_error("FILE_ITEM_PROCESSING", e, {"item": i, "filename": filename})
        
        await websocket.send_text(json.dumps({"status": "completed"}))
        
        # Log final do processamento
        semantic_logger.log_file_processing(filename, total, results_summary)
        
    except Exception as e:
        error_msg = str(e)
        await websocket.send_text(json.dumps({"error": error_msg}))
        semantic_logger.log_error("FILE_PROCESSING", e, {"filename": filename, "client_id": client_id})

@app.get("/health")
async def health_check():
    """Health check"""
    try:
        stats = get_stats()
        semantic_logger.log_info("Health check realizado", "HEALTH")
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "stats": stats
        }
    except Exception as e:
        semantic_logger.log_error("HEALTH_CHECK", e)
        raise HTTPException(500, "Erro no health check")

@app.get("/stats")
async def get_statistics():
    """Estatísticas"""
    try:
        stats = get_stats()
        semantic_logger.log_info("Estatísticas solicitadas", "STATS")
        return stats
    except Exception as e:
        semantic_logger.log_error("STATS", e)
        raise HTTPException(500, "Erro ao obter estatísticas")

@app.post("/stats/reset")
async def reset_statistics():
    """Reset estatísticas"""
    try:
        global stats
        stats = {
            "total_requests": 0,
            "total_errors": 0,
            "start_time": datetime.now()
        }
        semantic_logger.log_info("Estatísticas resetadas", "STATS_RESET")
        return {"message": "Estatísticas resetadas"}
    except Exception as e:
        semantic_logger.log_error("STATS_RESET", e)
        raise HTTPException(500, "Erro ao resetar estatísticas")

@app.get("/logs")
async def get_logs():
    """Endpoint para visualizar logs recentes"""
    try:
        log_file = Path("logs/semantica_api.log")
        if not log_file.exists():
            return {"message": "Arquivo de log não encontrado"}
        
        # Ler últimas 100 linhas
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            recent_lines = lines[-100:] if len(lines) > 100 else lines
        
        return {
            "total_lines": len(lines),
            "recent_lines": len(recent_lines),
            "logs": recent_lines
        }
    except Exception as e:
        semantic_logger.log_error("LOGS_ENDPOINT", e)
        raise HTTPException(500, "Erro ao acessar logs")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)