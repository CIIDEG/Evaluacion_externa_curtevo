"""Modelos ORM."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean
from .database import Base


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
    status = Column(String(20), default="pending")  # pending | done | error
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class FormAnalysis(Base):
    """Análisis cualitativo agregado de un formulario (temas, citas por criterio CAD)."""
    __tablename__ = "form_analysis"

    id = Column(Integer, primary_key=True, index=True)
    form_code = Column(String(50), index=True)
    payload = Column(JSON, nullable=False)  # estructura: {criterio: {temas:[], citas:[]}}
    model = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, index=True)
    actor = Column(String(80))
    action = Column(String(120))
    meta = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
