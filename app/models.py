"""Modelos ORM."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean
from .database import Base


# Roles disponibles en el sistema
ROLES = {
    "evaluador": "Evaluador — control total: usuarios, datos, configuración.",
    "equipo":    "Equipo — completar instrumentos cualitativos, ver respuestas y resultados.",
    "lector":    "Lector — solo ver la página de resultados.",
}

ROLE_LABELS = {
    "evaluador": "Evaluador",
    "equipo":    "Equipo",
    "lector":    "Lector",
}


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, index=True, nullable=False)
    full_name = Column(String(200))
    email = Column(String(200))
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="lector", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    must_change_password = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SurveyResponse(Base):
    __tablename__ = "survey_responses"

    id = Column(Integer, primary_key=True, index=True)
    form_code = Column(String(50), index=True, nullable=False)
    institucion = Column(String(200))
    sexo = Column(String(20))
    edad = Column(Integer, nullable=True)
    data = Column(JSON, nullable=False)
    user_agent = Column(String(300), nullable=True)
    ip = Column(String(60), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class AudioTranscript(Base):
    __tablename__ = "audio_transcripts"

    id = Column(Integer, primary_key=True, index=True)
    response_id = Column(Integer, index=True)
    form_code = Column(String(50), index=True)
    qid = Column(String(80))
    filename = Column(String(200))
    transcript = Column(Text, nullable=True)
    language = Column(String(10), nullable=True)
    model = Column(String(50), nullable=True)
    status = Column(String(20), default="pending")
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class FormAnalysis(Base):
    """Análisis cualitativo agregado de un formulario (temas, citas por criterio CAD)."""
    __tablename__ = "form_analysis"

    id = Column(Integer, primary_key=True, index=True)
    form_code = Column(String(50), index=True)
    payload = Column(JSON, nullable=False)
    model = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, index=True)
    actor = Column(String(80))
    action = Column(String(120))
    meta = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
