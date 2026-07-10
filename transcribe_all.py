"""Reset errores + crea registros para huérfanos + transcribe todo lo pendiente."""
import time
from pathlib import Path
from app.database import SessionLocal
from app import models, ai_hooks

AUDIO_DIR = Path("/code/data/audio")
db = SessionLocal()

# 1) registrar huérfanos
files = list(AUDIO_DIR.rglob("*.webm")) if AUDIO_DIR.exists() else []
filenames_bd = {t.filename for t in db.query(models.AudioTranscript).all()}
huerfanos = [p for p in files if p.name not in filenames_bd]
print(f"Audios huérfanos a registrar: {len(huerfanos)}")
for p in huerfanos:
    # ruta: audio/<form>/<draft_id o response_id>/<file>
    parts = p.relative_to(AUDIO_DIR).parts
    if len(parts) >= 3:
        form_code = parts[0]
        rid_str = parts[1]
        # solo registrar si la carpeta es un response_id numérico (no un draft)
        if not rid_str.isdigit():
            print(f"  skip (draft no enviado): {p.name}")
            continue
        rid = int(rid_str)
        qid = p.name.split("-")[0]
        t = models.AudioTranscript(form_code=form_code, response_id=rid, qid=qid, filename=p.name, status="pending")
        db.add(t)
        print(f"  + {form_code}/#{rid}/{p.name}")
db.commit()

# 2) resetear errores 429 a pending
n = db.query(models.AudioTranscript).filter_by(status="error").update({"status":"pending"})
db.commit()
print(f"\nReseteados {n} errores → pending")

# 3) procesar todos los pending
pendientes = db.query(models.AudioTranscript).filter_by(status="pending").all()
print(f"\nProcesando {len(pendientes)} pendientes con Gemini...\n")
ok = 0; fail = 0
for i, t in enumerate(pendientes, 1):
    path = AUDIO_DIR / t.form_code / str(t.response_id) / t.filename
    print(f"  [{i}/{len(pendientes)}] {t.form_code}/#{t.response_id}/{t.filename[:50]}...", flush=True)
    if not path.exists():
        print(f"      archivo no existe, skip")
        continue
    r = ai_hooks.transcribe_audio(path)
    t.status = r["status"]
    t.transcript = r["transcript"]
    t.language = r["language"]
    t.model = r["model"]
    t.error = r["error"]
    db.add(t); db.commit()
    if r["status"] == "done":
        chars = len(r["transcript"] or "")
        print(f"      ✓ {chars} chars")
        ok += 1
    else:
        err = (r.get("error") or "")[:120]
        print(f"      ✗ {r['status']}: {err}")
        fail += 1
        # si rate limit, esperar
        if "429" in err or "quota" in err.lower():
            print(f"      ⏸ pausa de 30s por rate limit...")
            time.sleep(30)

print(f"\n========================================")
print(f"  Resumen: ✓ {ok} transcritos · ✗ {fail} con error")
print(f"========================================")
