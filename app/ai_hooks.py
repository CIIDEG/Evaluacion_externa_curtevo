"""Hooks de IA con Gemini 2.5 Flash."""
import os
import base64
import json
import time
from pathlib import Path
import urllib.request
import urllib.error


GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"


def is_ai_enabled() -> bool:
    return bool(os.getenv("GEMINI_API_KEY"))


def _post_gemini(payload: dict, model: str = None) -> dict:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY no configurada")
    url = f"{GEMINI_ENDPOINT}/{model or GEMINI_MODEL}:generateContent"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
    )
    last_err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            last_err = f"HTTP {e.code}: {body[:300]}"
            if e.code in (429, 503) and attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            break
        except Exception as e:
            last_err = str(e)
            break
    raise RuntimeError(last_err)


def transcribe_audio(audio_path: Path) -> dict:
    if not is_ai_enabled():
        return {"status": "not_configured", "transcript": None, "language": None,
                "model": None, "error": "GEMINI_API_KEY no configurada."}
    if not audio_path.exists():
        return {"status": "error", "transcript": None, "language": None,
                "model": None, "error": f"Archivo no existe: {audio_path}"}
    try:
        audio_bytes = audio_path.read_bytes()
        b64 = base64.b64encode(audio_bytes).decode("utf-8")
        payload = {
            "contents": [{
                "parts": [
                    {"text":
                        "Transcribe literalmente el siguiente audio en español de Perú "
                        "(Cutervo, Cajamarca). Devuelve SOLO el texto transcrito, "
                        "sin marcas temporales, sin etiquetas de hablante. "
                        "Si hay varias voces distinguibles, intercálalas como "
                        "'— Voz 1:' / '— Voz 2:'. Mantén puntuación natural."},
                    {"inline_data": {"mime_type": "audio/webm", "data": b64}},
                ],
            }],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 32000},
        }
        r = _post_gemini(payload)
        try:
            text = r["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError):
            finish = r.get("candidates", [{}])[0].get("finishReason", "?")
            return {"status": "error", "transcript": None, "language": "es",
                    "model": GEMINI_MODEL,
                    "error": f"Respuesta sin texto (finishReason={finish}). Posible audio muy largo o respuesta cortada."}
        return {"status": "done", "transcript": text, "language": "es",
                "model": GEMINI_MODEL, "error": None}
    except Exception as e:
        return {"status": "error", "transcript": None, "language": "es",
                "model": GEMINI_MODEL, "error": str(e)}


def analyze_qualitative(form_code: str, items: list) -> dict:
    if not is_ai_enabled():
        return {"status": "not_configured", "data": None, "model": None,
                "error": "GEMINI_API_KEY no configurada."}
    if not items:
        return {"status": "done", "data": {}, "model": GEMINI_MODEL, "error": None}
    corpus = "\n\n".join([
        f"[#{i.get('response_id','?')} · {i.get('qid','?')} · {i.get('label','')[:120]}]\n{i.get('text','')[:1500]}"
        for i in items[:60]
    ])
    prompt = (
        "Eres analista de evaluación de proyectos de cooperación al desarrollo (criterios CAD/OCDE). "
        f"Instrumento evaluado: {form_code}. "
        "Lee los siguientes fragmentos y clasifícalos por criterio CAD. "
        "Para cada criterio extrae 1-3 temas recurrentes y, para cada tema, 1-3 citas literales "
        "representativas (textuales del corpus, con su response_id y qid entre corchetes). "
        "Devuelve ESTRICTAMENTE JSON con este esquema: "
        "{\"pertinencia\":{\"temas\":[{\"titulo\":\"...\",\"citas\":[\"...\"]}]},"
        "\"coherencia\":{\"temas\":[]},\"eficiencia\":{\"temas\":[]},"
        "\"eficacia\":{\"temas\":[]},\"impacto\":{\"temas\":[]},"
        "\"sostenibilidad\":{\"temas\":[]}}\n\n"
        f"CORPUS:\n{corpus}"
    )
    try:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
                "maxOutputTokens": 8000,
            },
        }
        r = _post_gemini(payload)
        text = r["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(text)
        return {"status": "done", "data": data, "model": GEMINI_MODEL, "error": None}
    except Exception as e:
        return {"status": "error", "data": None, "model": GEMINI_MODEL, "error": str(e)}
