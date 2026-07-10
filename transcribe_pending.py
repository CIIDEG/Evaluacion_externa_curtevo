"""Procesa audios pendientes de transcripción con Gemini."""
from app.database import SessionLocal
from app import models, ai_hooks
from pathlib import Path

AUDIO_DIR = Path("/code/data/audio")
db = SessionLocal()

pendientes = db.query(models.AudioTranscript).filter_by(status="pending").all()
print(f"Audios pendientes: {len(pendientes)}")

ok = 0; fail = 0
for t in pendientes:
    path = AUDIO_DIR / t.form_code / str(t.response_id) / t.filename
    print(f"  → {t.form_code}/#{t.response_id}/{t.filename}", flush=True)
    if not path.exists():
        print(f"    archivo no existe, skip")
        continue
    r = ai_hooks.transcribe_audio(path)
    t.status = r["status"]
    t.transcript = r["transcript"]
    t.language = r["language"]
    t.model = r["model"]
    t.error = r["error"]
    db.add(t); db.commit()
    if r["status"] == "done":
        snip = (r["transcript"] or "")[:300].replace("\n", " ")
        print(f"    ✓ {len(r['transcript'] or '')} chars · «{snip}...»")
        ok += 1
    else:
        print(f"    ✗ {r['status']}: {r['error']}")
        fail += 1

print(f"\nResumen: ✓ {ok} transcritos · ✗ {fail} con error")
