# models.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

class SemanticaInput(BaseModel):
    """Modelo para entrada de análise semântica - Apenas JSON estruturado"""
    
    id_termo: str = Field(
        description="Identificador único do termo",
        examples=["314166", "314167", "314168"]
    )
    cpf: str = Field(
        description="CPF do cliente",
        examples=["48956314785", "12345678901", "98765432100"]
    )
    pratica_vedada: str = Field(
        description="Código da prática vedada",
        examples=["10,11", "12", "Contrato liquidado"]
    )
    justificativa: str = Field(
        description="Justificativa do cliente (mínimo 10 caracteres)",
        examples=[
            "Estou sendo descontado sem autorização prévia do empréstimo consignado no valor de R$ 450,00 mensais.",
            "Foi descontado empréstimo consignado do meu benefício, porém nunca recebi o valor creditado.",
            "Continuo sendo descontado mesmo após ter quitado completamente o empréstimo há 3 meses."
        ]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id_termo": "314166",
                    "cpf": "48956314785",
                    "pratica_vedada": "10,11",
                    "justificativa": "Estou sendo descontado sem autorização prévia do empréstimo consignado no valor de R$ 450,00 mensais. Nunca solicitei este empréstimo e não recebi nenhum valor creditado em minha conta."
                },
                {
                    "id_termo": "314167",
                    "cpf": "12345678901",
                    "pratica_vedada": "12",
                    "justificativa": "Foi descontado empréstimo consignado do meu benefício, porém nunca recebi o valor creditado na minha conta bancária. Solicito o estorno imediato dos valores."
                },
                {
                    "id_termo": "314168",
                    "cpf": "98765432100",
                    "pratica_vedada": "Contrato liquidado",
                    "justificativa": "Continuo sendo descontado mesmo após ter quitado completamente o empréstimo consignado há 3 meses. Tenho comprovante de quitação mas os descontos persistem."
                }
            ]
        }
    }
    
    @field_validator('justificativa')
    @classmethod
    def validate_justificativa(cls, v):
        """Validação da justificativa"""
        if len(v.strip()) < 10:
            raise ValueError('Justificativa deve ter pelo menos 10 caracteres')
        return v.strip()
    
    @field_validator('cpf')
    @classmethod
    def validate_cpf(cls, v):
        """Validação básica do CPF"""
        cpf_clean = ''.join(filter(str.isdigit, v))
        if len(cpf_clean) != 11:
            raise ValueError('CPF deve ter 11 dígitos')
        return cpf_clean
    
    @field_validator('id_termo')
    @classmethod
    def validate_id_termo(cls, v):
        """Validação do ID do termo"""
        if not v.strip():
            raise ValueError('ID do termo é obrigatório')
        return v.strip()
    
    def get_format_type(self):
        """Sempre retorna JSON estruturado"""
        return "JSON_ESTRUTURADO"
    
    def to_internal_format(self):
        """Converte para formato interno (compatibilidade)"""
        return f"{self.id_termo}#{self.cpf}#{self.pratica_vedada}#{self.justificativa}"

class SemanticaResponse(BaseModel):
    """Resposta da análise semântica"""
    
    status: str = Field(description="Status: APPROVED, REVIEW_REQUIRED, ou REJECTED")
    diagnostico_llm: str = Field(description="Diagnóstico do LLM: SIM ou NÃO")
    confidence: float = Field(description="Confiança (0.0 a 1.0)")
    justificativa_llm: str = Field(description="Justificativa do LLM")
    processing_time: float = Field(description="Tempo de processamento (segundos)")
    analysis_id: str = Field(description="ID único da análise")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "APPROVED",
                "diagnostico_llm": "SIM",
                "confidence": 0.85,
                "justificativa_llm": "A justificativa indica claramente uma consignação sem autorização prévia.",
                "processing_time": 1.23,
                "analysis_id": "a1b2c3d4",
                "timestamp": "2025-06-05T15:30:15.123456"
            }
        }
    }

class ProcessingResult(BaseModel):
    """Resultado de processamento individual"""
    
    id_termo: str
    cpf: str
    pratica_vedada: str
    justificativa: str
    status: str
    diagnostico_llm: Optional[str] = None
    confidence: Optional[float] = None
    justificativa_llm: Optional[str] = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())