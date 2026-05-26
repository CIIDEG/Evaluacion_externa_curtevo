"""Centro de Evaluación Cutervo — sistema unificado."""
import os
import shutil
import uuid
import json
from pathlib import Path
from datetime import datetime
from io import BytesIO

from fastapi import FastAPI, Request, UploadFile, File, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from openpyxl import Workbook

from .database import Base, engine, get_db
from . import models, auth, ai_hooks, results as results_mod
from .surveys_def import get_form, all_question_ids, ALL_FORMS

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR.parent / "docs"
DATA_DIR = Path("/code/data")
AUDIO_DIR = DATA_DIR / "audio"
UPLOADS_DIR = DATA_DIR / "uploads"
for d in (DATA_DIR, AUDIO_DIR, UPLOADS_DIR):
    d.mkdir(parents=True, exist_ok=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Centro de Evaluación Cutervo")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.globals["ALL_FORMS"] = ALL_FORMS

# Formularios cualitativos (solo evaluador)
PRIVATE_FORMS = {"kii", "fgd_jovenes", "fgd_docentes", "observacion", "msc"}
# Formularios públicos (todos pueden llenar)
PUBLIC_FORMS = {"estudiantes", "docentes"}


def ctx(request: Request, **extra):
    """Contexto base para todos los templates."""
    return {
        "request": request,
        "user": auth.get_user(request),
        "ai_enabled": ai_hooks.is_ai_enabled(),
        "results_token": auth.public_results_token(),
        **extra,
    }


# ============================================================
#                    PÁGINAS PÚBLICAS
# ============================================================
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", ctx(request))


@app.get("/cronograma", response_class=HTMLResponse)
def cronograma(request: Request):
    return templates.TemplateResponse("cronograma.html", ctx(request))


@app.get("/anexos", response_class=HTMLResponse)
def anexos(request: Request):
    return templates.TemplateResponse("anexos.html", ctx(request, PRIVATE_FORMS=PRIVATE_FORMS))


@app.get("/documentos", response_class=HTMLResponse)
def documentos(request: Request):
    items = []
    if DOCS_DIR.exists():
        for p in sorted(DOCS_DIR.iterdir()):
            if p.is_file():
                items.append({"name": p.name, "size_kb": round(p.stat().st_size / 1024, 1)})
    return templates.TemplateResponse("documentos.html", ctx(request, items=items))


@app.get("/documentos/{filename}")
def descargar(filename: str):
    safe = (DOCS_DIR / filename).resolve()
    if not safe.is_file():
        raise HTTPException(404)
    return FileResponse(safe, filename=filename)


# ============================================================
#                    LOGIN / LOGOUT
# ============================================================
@app.get("/login", response_class=HTMLResponse)
def login_get(request: Request, next: str = "/admin"):
    return templates.TemplateResponse("login.html", ctx(request, next=next, error=None))


@app.post("/login")
def login_post(request: Request, username: str = Form(...), password: str = Form(...), next: str = Form("/admin")):
    if auth.verify_password(username, password):
        token = auth.create_session(username)
        # validar next para evitar open redirect
        if not next.startswith("/"):
            next = "/admin"
        resp = RedirectResponse(url=next, status_code=303)
        resp.set_cookie(
            auth.COOKIE_NAME, token,
            max_age=auth.COOKIE_MAX_AGE, httponly=True, samesite="lax",
            secure=False,  # Caddy hace TLS termination
        )
        return resp
    return templates.TemplateResponse("login.html", ctx(request, next=next, error="Credenciales inválidas"), status_code=401)


@app.get("/logout")
def logout():
    resp = RedirectResponse(url="/", status_code=303)
    resp.delete_cookie(auth.COOKIE_NAME)
    return resp


# ============================================================
#                    FORMULARIOS
# ============================================================
@app.get("/encuesta/{code}", response_class=HTMLResponse)
def encuesta_get(code: str, request: Request):
    form = get_form(code)
    if not form:
        raise HTTPException(404)
    # cualitativos requieren login
    if code in PRIVATE_FORMS and not auth.get_user(request):
        return RedirectResponse(url=f"/login?next=/encuesta/{code}", status_code=303)
    return templates.TemplateResponse("encuesta.html", ctx(request, form=form, draft_id=uuid.uuid4().hex))


@app.post("/encuesta/{code}")
async def encuesta_post(code: str, request: Request, db: Session = Depends(get_db)):
    form = get_form(code)
    if not form:
        raise HTTPException(404)
    if code in PRIVATE_FORMS and not auth.get_user(request):
        return RedirectResponse(url="/login", status_code=303)
    raw = await request.form()
    data = {}
    for qid in all_question_ids(form):
        val = raw.get(qid, "")
        if hasattr(val, "filename"):
            continue
        data[qid] = val if isinstance(val, str) else str(val)
    # validación
    draft_id = raw.get("__draft_id", "")
    missing = []
    for sec in form["sections"]:
        for q in sec["questions"]:
            if q.get("required"):
                v = data.get(q["id"], "").strip()
                if q.get("type") == "audio_text":
                    audio_dir = AUDIO_DIR / code / draft_id
                    has_audio = audio_dir.exists() and any(audio_dir.glob(f"{q['id']}*.webm"))
                    if not v and not has_audio:
                        missing.append(q["label"])
                elif not v:
                    missing.append(q["label"])
    if missing:
        return templates.TemplateResponse(
            "encuesta.html",
            ctx(request, form=form, errors=missing, data=data, draft_id=draft_id or uuid.uuid4().hex),
            status_code=400,
        )
    response = models.SurveyResponse(
        form_code=code,
        institucion=data.get("institucion"),
        sexo=data.get("sexo"),
        edad=(int(data["edad"]) if str(data.get("edad", "")).isdigit() else None),
        data=data,
        user_agent=request.headers.get("user-agent", "")[:300],
        ip=request.client.host if request.client else None,
    )
    db.add(response); db.commit(); db.refresh(response)
    # mover audios de draft → carpeta definitiva con id de respuesta
    if draft_id:
        src = AUDIO_DIR / code / draft_id
        if src.exists():
            dst = AUDIO_DIR / code / str(response.id)
            dst.mkdir(parents=True, exist_ok=True)
            for f in src.iterdir():
                shutil.move(str(f), dst / f.name)
                # Registrar transcripción pendiente
                t = models.AudioTranscript(
                    response_id=response.id, form_code=code,
                    qid=f.name.split("-")[0], filename=f.name, status="pending"
                )
                db.add(t)
            db.commit()
            try: src.rmdir()
            except OSError: pass
    return templates.TemplateResponse("gracias.html", ctx(request, form=form))


# ============================================================
#                    UPLOADS (audio + archivos)
# ============================================================
@app.post("/upload-audio/{code}/{draft_id}/{qid}")
async def upload_audio(code: str, draft_id: str, qid: str, request: Request, audio: UploadFile = File(...)):
    form = get_form(code)
    if not form or qid not in all_question_ids(form):
        raise HTTPException(400)
    if code in PRIVATE_FORMS and not auth.get_user(request):
        raise HTTPException(401)
    if not draft_id.isalnum() or len(draft_id) > 64:
        raise HTTPException(400)
    dst_dir = AUDIO_DIR / code / draft_id
    dst_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{qid}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.webm"
    dst = dst_dir / fname
    content = await audio.read()
    dst.write_bytes(content)
    return JSONResponse({"ok": True, "size": len(content), "filename": fname})


@app.post("/upload-file/{code}/{draft_id}/{qid}")
async def upload_file(code: str, draft_id: str, qid: str, request: Request, file: UploadFile = File(...)):
    form = get_form(code)
    if not form or qid not in all_question_ids(form):
        raise HTTPException(400)
    if code in PRIVATE_FORMS and not auth.get_user(request):
        raise HTTPException(401)
    if not draft_id.isalnum() or len(draft_id) > 64:
        raise HTTPException(400)
    dst_dir = UPLOADS_DIR / code / draft_id
    dst_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "").suffix[:10] or ".bin"
    dst = dst_dir / f"{qid}{ext}"
    dst.write_bytes(await file.read())
    return JSONResponse({"ok": True, "filename": dst.name})


# ============================================================
#                    PÁGINA DE RESULTADOS
# ============================================================
@app.get("/resultados", response_class=HTMLResponse)
def resultados(request: Request, token: str = "", db: Session = Depends(get_db)):
    """Pública si se accede con token. También accesible si está logueado."""
    user = auth.get_user(request)
    if not user and not auth.verify_public_results_token(token):
        # mostrar página de acceso con instrucción
        return templates.TemplateResponse("resultados_acceso.html", ctx(request, results_url=f"/resultados?token={auth.public_results_token()}"))
    is_evaluator = bool(user)
    payload = results_mod.build_full_results(db, include_audios=is_evaluator)
    return templates.TemplateResponse("resultados.html", ctx(request,
        payload=payload, token=token, is_evaluator=is_evaluator,
        ai_status=("activo" if ai_hooks.is_ai_enabled() else "pendiente"),
    ))


# ============================================================
#                    ADMIN (login)
# ============================================================
@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    user = auth.get_user(request)
    if not user:
        return RedirectResponse(url="/login?next=/admin", status_code=303)
    overview = results_mod.overview_metrics(db)
    return templates.TemplateResponse("admin/dashboard.html", ctx(request,
        overview=overview,
        public_results_url=f"/resultados?token={auth.public_results_token()}",
    ))


@app.get("/admin/respuestas/{code}", response_class=HTMLResponse)
def admin_respuestas(code: str, request: Request, db: Session = Depends(get_db)):
    if not auth.get_user(request):
        return RedirectResponse(url="/login?next=/admin/respuestas/"+code, status_code=303)
    form = get_form(code)
    if not form: raise HTTPException(404)
    rows = db.query(models.SurveyResponse).filter_by(form_code=code).order_by(models.SurveyResponse.created_at.desc()).limit(500).all()
    rows_data = []
    for r in rows:
        audio_dir = AUDIO_DIR / code / str(r.id)
        n_audios = len(list(audio_dir.glob("*.webm"))) if audio_dir.exists() else 0
        rows_data.append({"r": r, "n_audios": n_audios})
    return templates.TemplateResponse("admin/respuestas.html", ctx(request, form=form, rows=rows_data))


@app.get("/admin/respuesta/{code}/{rid}", response_class=HTMLResponse)
def admin_respuesta_detalle(code: str, rid: int, request: Request, db: Session = Depends(get_db)):
    if not auth.get_user(request):
        return RedirectResponse(url="/login", status_code=303)
    form = get_form(code)
    if not form: raise HTTPException(404)
    r = db.query(models.SurveyResponse).filter_by(form_code=code, id=rid).first()
    if not r: raise HTTPException(404)
    audio_dir = AUDIO_DIR / code / str(rid)
    audios = sorted([p.name for p in audio_dir.glob("*.webm")]) if audio_dir.exists() else []
    # transcripts si los hubiera
    transcripts = {t.filename: t for t in db.query(models.AudioTranscript).filter_by(response_id=rid).all()}
    return templates.TemplateResponse("admin/respuesta_detalle.html", ctx(request,
        form=form, r=r, audios=audios, transcripts=transcripts,
    ))


@app.get("/admin/audio/{code}/{rid}/{filename}")
def admin_audio(code: str, rid: int, filename: str, request: Request):
    if not auth.get_user(request):
        raise HTTPException(401)
    p = (AUDIO_DIR / code / str(rid) / filename).resolve()
    if not str(p).startswith(str(AUDIO_DIR.resolve())) or not p.is_file():
        raise HTTPException(404)
    return FileResponse(p, media_type="audio/webm", filename=filename)


@app.get("/admin/export/{code}.xlsx")
def admin_export(code: str, request: Request, db: Session = Depends(get_db)):
    if not auth.get_user(request):
        raise HTTPException(401)
    form = get_form(code)
    if not form: raise HTTPException(404)
    rows = db.query(models.SurveyResponse).filter_by(form_code=code).order_by(models.SurveyResponse.created_at.asc()).all()
    wb = Workbook(); ws = wb.active; ws.title = code[:30]
    headers = ["id", "created_at"] + all_question_ids(form) + ["audios_count"]
    ws.append(headers)
    for r in rows:
        audio_dir = AUDIO_DIR / code / str(r.id)
        n_audios = len(list(audio_dir.glob("*.webm"))) if audio_dir.exists() else 0
        ws.append([r.id, r.created_at.isoformat()] + [str((r.data or {}).get(k, "")) for k in all_question_ids(form)] + [n_audios])
    buf = BytesIO(); wb.save(buf); buf.seek(0)
    fname = f"respuestas_{code}_{datetime.utcnow():%Y%m%d_%H%M}.xlsx"
    return StreamingResponse(buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@app.get("/admin/download-db")
def admin_download_db(request: Request):
    if not auth.get_user(request):
        raise HTTPException(401)
    db_path = DATA_DIR / "cutervo.db"
    if not db_path.is_file():
        raise HTTPException(404)
    fname = f"cutervo_backup_{datetime.utcnow():%Y%m%d_%H%M}.db"
    return FileResponse(db_path, media_type="application/octet-stream", filename=fname)


# Hook IA (devuelve estado actual)
@app.post("/admin/ai/transcribe-all")
def admin_transcribe_all(request: Request, db: Session = Depends(get_db)):
    if not auth.get_user(request):
        raise HTTPException(401)
    if not ai_hooks.is_ai_enabled():
        return JSONResponse({"ok": False, "msg": "Configura OPENAI_API_KEY en .env y reinicia."})
    # cuando se active, iterar transcripts pendientes y procesarlas
    pendientes = db.query(models.AudioTranscript).filter_by(status="pending").all()
    procesados = 0
    for t in pendientes:
        path = AUDIO_DIR / t.form_code / str(t.response_id) / t.filename
        if not path.is_file(): continue
        r = ai_hooks.transcribe_audio(path)
        if r["status"] == "done":
            t.transcript = r["transcript"]; t.language = r["language"]; t.model = r["model"]; t.status = "done"
            procesados += 1
        else:
            t.status = r["status"]; t.error = r["error"]
        db.add(t)
    db.commit()
    return JSONResponse({"ok": True, "procesados": procesados, "pendientes_iniciales": len(pendientes)})


@app.get("/health")
def health():
    return {"ok": True, "service": "cutervo-eval-portal", "now": datetime.utcnow().isoformat(), "ai": ai_hooks.is_ai_enabled()}
