"""Hooks de IA — preparados para activarse cuando exista OPENAI_API_KEY.

Sin API key, las funciones devuelven estado 'not_configured' y dejan placeholders.
Más adelante se puede sustituir por implementación real con openai-python.
"""
import os
from pathlib import Path
from typing import Optional


def is_ai_enabled() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def transcribe_audio(audio_path: Path) -> dict:
    """Devuelve {'status', 'transcript', 'language', 'model', 'error'}."""
    if not is_ai_enabled():
        return {
            "status": "not_configured",
            "transcript": None,
            "language": None,
            "model": None,
            "error": "Configura OPENAI_API_KEY en .env para activar la transcripción automática.",
        }
    # Implementación real (cuando se active):
    # from openai import OpenAI
    # client = OpenAI()
    # with open(audio_path, "rb") as f:
    #     r = client.audio.transcriptions.create(model="whisper-1", file=f, language="es")
    # return {"status":"done","transcript":r.text,"language":"es","model":"whisper-1","error":None}
    return {
        "status": "not_implemented",
        "transcript": None,
        "language": None,
        "model": None,
        "error": "Pendiente de implementación.",
    }


def analyze_qualitative(form_code: str, items: list) -> dict:
    """Análisis temático por criterio CAD a partir de respuestas/transcripts.

    items: lista de dicts {qid, label, text, response_id}
    Devuelve estructura {criterio: {temas:[{titulo, mencion_count, citas:[...]}]}}.
    """
    if not is_ai_enabled():
        return {
            "status": "not_configured",
            "data": None,
            "model": None,
            "error": "Configura OPENAI_API_KEY en .env para generar el análisis cualitativo automático.",
        }
    # Implementación real (cuando se active):
    # Construir prompt con criterios CAD + items. Llamar GPT-4o-mini con JSON schema.
    return {
        "status": "not_implemented",
        "data": None,
        "model": None,
        "error": "Pendiente de implementación.",
    }
