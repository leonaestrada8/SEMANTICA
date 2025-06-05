# utils.py
import json
import uuid
import time
from pathlib import Path
from datetime import datetime
from config import *
from models import ProcessingResult

# Estatísticas simples
stats = {
    "total_requests": 0,
    "total_errors": 0,
    "start_time": datetime.now()
}

def parse_line(line):
    """Parse linha do arquivo (para compatibilidade com processamento em lote)"""
    parts = line.split("#")
    if len(parts) < 4:
        raise ValueError("Formato inválido")
    
    return {
        "id_termo": parts[0],
        "cpf": parts[1],
        "pratica_vedada": parts[2],
        "justificativa": "#".join(parts[3:])
    }

def normalize_input(entrada):
    """Normaliza entrada para formato interno"""
    return {
        "input": entrada.to_internal_format(),
        "format": "json_estruturado"
    }

def classify_result(diagnostico, confidence):
    """Classifica resultado baseado na confiança"""
    if diagnostico == "SIM" and confidence >= CONFIDENCE_HIGH:
        return "APPROVED"
    elif diagnostico == "SIM" and confidence >= CONFIDENCE_MEDIUM:
        return "REVIEW_REQUIRED"
    else:
        return "REJECTED"

def create_prompt(justificativa):
    """Cria prompt para LLM"""
    return PROMPT_TEMPLATE.format(justificativa=justificativa)

def save_json(data, filename):
    """Salva dados em JSON"""
    Path(OUTPUT_FOLDER).mkdir(exist_ok=True)
    filepath = Path(OUTPUT_FOLDER) / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def update_stats(error=False):
    """Atualiza estatísticas"""
    stats["total_requests"] += 1
    if error:
        stats["total_errors"] += 1

def get_stats():
    """Retorna estatísticas"""
    uptime = (datetime.now() - stats["start_time"]).total_seconds()
    error_rate = (stats["total_errors"] / max(stats["total_requests"], 1)) * 100
    
    return {
        "total_requests": stats["total_requests"],
        "total_errors": stats["total_errors"],
        "error_rate": round(error_rate, 2),
        "uptime_seconds": round(uptime, 2)
    }

def setup_folders():
    """Cria pastas necessárias"""
    Path(INPUT_FOLDER).mkdir(exist_ok=True)
    Path(OUTPUT_FOLDER).mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)

def mask_cpf(cpf):
    """Mascara CPF para logs"""
    if not cpf or len(cpf) < 11:
        return cpf
    return f"{cpf[:3]}***{cpf[-2:]}"