"""Modelos ORM."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from .database import Base


class SurveyResponse(Base):
    __tablename__ = "survey_responses"

    id = Column(Integer, primary_key=True, index=True)
    form_code = Column(String(50), index=True, nullable=False)  # 'estudiantes' | 'docentes'
    institucion = Column(String(200))
    sexo = Column(String(20))
    edad = Column(Integer, nullable=True)
    data = Column(JSON, nullable=False)  # respuestas completas
    user_agent = Column(String(300), nullable=True)
    ip = Column(String(60), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, index=True)
    actor = Column(String(80))
    action = Column(String(120))
    meta = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
