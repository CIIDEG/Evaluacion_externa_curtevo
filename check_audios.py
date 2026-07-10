"""Verifica el estado de los audios y transcripciones."""
from app.database import SessionLocal
from app import models
from pathlib import Path

AUDIO_DIR = Path("/code/data/audio")
db = SessionLocal()

files = list(AUDIO_DIR.rglob("*.webm")) if AUDIO_DIR.exists() else []
print(f"Audios físicos en disco: {len(files)}")

total = db.query(models.AudioTranscript).count()
done = db.query(models.AudioTranscript).filter_by(status="done").count()
pending = db.query(models.AudioTranscript).filter_by(status="pending").count()
err = db.query(models.AudioTranscript).filter_by(status="error").count()
print(f"Registros en audio_transcripts: {total}")
print(f"  - done   : {done}")
print(f"  - pending: {pending}")
print(f"  - error  : {err}")

filenames_disco = {p.name for p in files}
filenames_bd = {t.filename for t in db.query(models.AudioTranscript).all()}
sin_registro = filenames_disco - filenames_bd
if sin_registro:
    print(f"\nAudios en disco SIN registro en BD: {len(sin_registro)}")
    for f in list(sin_registro)[:8]:
        # buscar el path completo
        for p in files:
            if p.name == f:
                print(f"   - {p.parent.parent.name}/{p.parent.name}/{p.name}"); break

sin_archivo = filenames_bd - filenames_disco
if sin_archivo:
    print(f"\nRegistros en BD SIN archivo físico: {len(sin_archivo)}")

recientes = db.query(models.AudioTranscript).filter_by(status="done").order_by(models.AudioTranscript.created_at.desc()).limit(3).all()
if recientes:
    print("\nÚltimas transcripciones completas:")
    for t in recientes:
        snip = (t.transcript or "")[:120].replace("\n", " ")
        print(f"  {t.form_code}/#{t.response_id}/{t.filename[:50]}: {snip}...")

# audios pendientes y errores
pend_list = db.query(models.AudioTranscript).filter_by(status="pending").limit(5).all()
if pend_list:
    print(f"\nAudios pendientes (muestra):")
    for t in pend_list:
        print(f"  {t.form_code}/#{t.response_id}/{t.filename}")

err_list = db.query(models.AudioTranscript).filter_by(status="error").limit(5).all()
if err_list:
    print(f"\nAudios con error (muestra):")
    for t in err_list:
        print(f"  {t.form_code}/#{t.response_id}/{t.filename}: {(t.error or '')[:100]}")
