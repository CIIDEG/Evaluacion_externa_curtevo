"""
Transcripción local de audios pendientes en la nube.

Uso:
    python transcribe_local.py \
        --url https://evafinal.metacalidad.cloud \
        --user admin --pass TU_CLAVE \
        --openai-key sk-...

Requisitos:
    pip install requests openai

Transcribe solo los audios con status "pending", "not_configured",
"not_implemented" o "error" y actualiza la BD en la nube.
"""

import argparse
import os
import sys
import tempfile
import time
from pathlib import Path

import requests

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


def login(session: requests.Session, base: str, user: str, password: str) -> bool:
    r = session.post(
        f"{base}/login",
        data={"username": user, "password": password, "next": "/admin"},
        allow_redirects=True,
        timeout=15,
    )
    # Si llegamos al panel admin o a /perfil la cookie ya está guardada
    return r.status_code == 200 and "/login" not in r.url


def get_pending(session: requests.Session, base: str) -> list:
    r = session.get(f"{base}/admin/ai/pending-transcripts", timeout=15)
    r.raise_for_status()
    return r.json()


def download_audio(session: requests.Session, base: str, form_code: str, rid: int, filename: str) -> bytes:
    url = f"{base}/admin/audio/{form_code}/{rid}/{filename}"
    r = session.get(url, timeout=30)
    r.raise_for_status()
    return r.content


def transcribe_with_openai(client, audio_bytes: bytes, filename: str) -> dict:
    """Usa Whisper-1 de OpenAI para transcribir."""
    with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix or ".webm", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        with open(tmp_path, "rb") as f:
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="es",
                response_format="verbose_json",
            )
        return {
            "status": "done",
            "transcript": result.text,
            "language": getattr(result, "language", "es"),
            "model": "whisper-1",
            "error": None,
        }
    except Exception as e:
        return {"status": "error", "transcript": None, "language": None, "model": "whisper-1", "error": str(e)[:300]}
    finally:
        os.unlink(tmp_path)


def update_transcript(session: requests.Session, base: str, tid: int, payload: dict) -> bool:
    r = session.post(
        f"{base}/admin/ai/update-transcript/{tid}",
        json=payload,
        timeout=15,
    )
    return r.ok


def main():
    parser = argparse.ArgumentParser(description="Transcripción local de audios pendientes en la nube")
    parser.add_argument("--url", default="https://evafinal.metacalidad.cloud", help="URL base del portal")
    parser.add_argument("--user", default=os.getenv("PORTAL_USER", "admin"), help="Usuario del portal")
    parser.add_argument("--pass", dest="password", default=os.getenv("PORTAL_PASS", ""), help="Contraseña del portal")
    parser.add_argument("--openai-key", default=os.getenv("OPENAI_API_KEY", ""), help="Clave de OpenAI (Whisper)")
    parser.add_argument("--dry-run", action="store_true", help="Listar pendientes sin transcribir")
    args = parser.parse_args()

    base = args.url.rstrip("/")

    # Validar dependencias
    if not args.dry_run:
        if OpenAI is None:
            print("ERROR: instala openai  →  pip install openai", file=sys.stderr)
            sys.exit(1)
        if not args.openai_key:
            print("ERROR: proporciona --openai-key o define OPENAI_API_KEY", file=sys.stderr)
            sys.exit(1)

    client = OpenAI(api_key=args.openai_key) if (not args.dry_run and OpenAI) else None

    session = requests.Session()
    session.headers["User-Agent"] = "transcribe-local/1.0"

    print(f"Conectando a {base} ...")
    if not login(session, base, args.user, args.password):
        print("ERROR: no se pudo autenticar. Verifica usuario y contraseña.", file=sys.stderr)
        sys.exit(1)
    print("Autenticado correctamente.")

    pendientes = get_pending(session, base)
    print(f"\nAudios pendientes o con error: {len(pendientes)}")
    if not pendientes:
        print("Nada que hacer.")
        return

    for item in pendientes:
        tid = item["id"]
        form_code = item["form_code"]
        rid = item["response_id"]
        fname = item["filename"]
        print(f"\n[{tid}] {form_code}/{rid}/{fname}  (estado actual: {item['status']})")

        if args.dry_run:
            continue

        # Descargar audio
        try:
            audio_bytes = download_audio(session, base, form_code, rid, fname)
            print(f"  Descargado: {len(audio_bytes)/1024:.1f} KB")
        except Exception as e:
            print(f"  ERROR descargando: {e}")
            update_transcript(session, base, tid, {
                "status": "error", "transcript": None, "language": None,
                "model": None, "error": f"Descarga fallida: {e}"[:300],
            })
            continue

        # Transcribir
        result = transcribe_with_openai(client, audio_bytes, fname)
        if result["status"] == "done":
            preview = (result["transcript"] or "")[:80].replace("\n", " ")
            print(f"  Transcrito: \"{preview}...\"")
        else:
            print(f"  ERROR transcribiendo: {result['error']}")

        # Actualizar nube
        ok = update_transcript(session, base, tid, result)
        print(f"  Nube actualizada: {'OK' if ok else 'FALLO'}")

        # Pausa breve para no saturar la API
        time.sleep(0.5)

    if not args.dry_run:
        # Re-verificar cuántos quedaron pendientes
        restantes = get_pending(session, base)
        print(f"\nResumen: {len(pendientes)} procesados, {len(restantes)} aún pendientes.")


if __name__ == "__main__":
    main()
