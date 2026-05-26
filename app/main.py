"""Centro de Evaluación Cutervo — sistema unificado con gestor de perfiles."""
import os
import shutil
import uuid
import re
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
auth.bootstrap_admin()

app = FastAPI(title="Centro de Evaluación Cutervo")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.globals["ALL_FORMS"] = ALL_FORMS
templates.env.globals["ROLE_LABELS"] = models.ROLE_LABELS
templates.env.globals["ROLES"] = models.ROLES

PRIVATE_FORMS = {"kii", "fgd_jovenes", "fgd_docentes", "observacion", "msc"}


def ctx(request: Request, **extra):
    user = auth.current_user(request)
    return {
        "request": request,
        "user": user,
        "can": (lambda act: auth.can(user, act)),
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
def login_post(request: Request, username: str = Form(...), password: str = Form(...), next: str = Form("/admin"), db: Session = Depends(get_db)):
    u = db.query(models.User).filter_by(username=username, is_active=True).first()
    if u and auth.check_password(password, u.password_hash):
        u.last_login = datetime.utcnow()
        db.add(u); db.commit()
        token = auth.create_session(u.id, u.username)
        if not next.startswith("/"):
            next = "/admin"
        if u.must_change_password:
            next = "/perfil"
        resp = RedirectResponse(url=next, status_code=303)
        resp.set_cookie(auth.COOKIE_NAME, token, max_age=auth.COOKIE_MAX_AGE, httponly=True, samesite="lax", secure=False)
        return resp
    return templates.TemplateResponse("login.html", ctx(request, next=next, error="Credenciales inválidas o usuario inactivo"), status_code=401)


@app.get("/logout")
def logout():
    resp = RedirectResponse(url="/", status_code=303)
    resp.delete_cookie(auth.COOKIE_NAME)
    return resp


# ============================================================
#                    PERFIL PROPIO
# ============================================================
@app.get("/perfil", response_class=HTMLResponse)
def perfil_get(request: Request, ok: int = 0, err: str = ""):
    u = auth.current_user(request)
    if not u:
        return RedirectResponse("/login?next=/perfil", status_code=303)
    return templates.TemplateResponse("perfil.html", ctx(request, ok=ok, err=err))


@app.post("/perfil")
def perfil_post(request: Request,
                full_name: str = Form(""), email: str = Form(""),
                current_password: str = Form(""), new_password: str = Form(""), new_password2: str = Form(""),
                db: Session = Depends(get_db)):
    u = auth.current_user(request)
    if not u:
        return RedirectResponse("/login", status_code=303)
    u.full_name = full_name.strip(); u.email = email.strip()
    if new_password or current_password:
        if not auth.check_password(current_password, u.password_hash):
            return RedirectResponse("/perfil?err=Contrase%C3%B1a+actual+incorrecta", status_code=303)
        if len(new_password) < 8:
            return RedirectResponse("/perfil?err=M%C3%ADnimo+8+caracteres", status_code=303)
        if new_password != new_password2:
            return RedirectResponse("/perfil?err=Las+contrase%C3%B1as+no+coinciden", status_code=303)
        u.password_hash = auth.hash_password(new_password)
        u.must_change_password = False
    db.add(u); db.commit()
    return RedirectResponse("/perfil?ok=1", status_code=303)


# ============================================================
#                    GESTOR DE USUARIOS
# ============================================================
@app.get("/admin/usuarios", response_class=HTMLResponse)
def usuarios_list(request: Request, db: Session = Depends(get_db)):
    me = auth.current_user(request)
    if not me or not auth.can(me, "manage_users"):
        raise HTTPException(403)
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    return templates.TemplateResponse("admin/usuarios.html", ctx(request, users=users))


@app.get("/admin/usuarios/nuevo", response_class=HTMLResponse)
def usuario_new_get(request: Request):
    me = auth.current_user(request)
    if not me or not auth.can(me, "manage_users"):
        raise HTTPException(403)
    return templates.TemplateResponse("admin/usuario_form.html", ctx(request, edit_user=None, err=None))


@app.post("/admin/usuarios/nuevo")
def usuario_new_post(request: Request,
                     username: str = Form(...), full_name: str = Form(""), email: str = Form(""),
                     password: str = Form(...), role: str = Form("lector"),
                     db: Session = Depends(get_db)):
    me = auth.current_user(request)
    if not me or not auth.can(me, "manage_users"):
        raise HTTPException(403)
    username = username.strip().lower()
    if not re.match(r"^[a-z0-9._-]{3,40}$", username):
        return templates.TemplateResponse("admin/usuario_form.html",
            ctx(request, edit_user=None, err="Usuario inválido (3-40 caracteres: letras, números, . _ -)"), status_code=400)
    if db.query(models.User).filter_by(username=username).first():
        return templates.TemplateResponse("admin/usuario_form.html",
            ctx(request, edit_user=None, err="Ese nombre de usuario ya existe"), status_code=400)
    if role not in models.ROLES:
        role = "lector"
    if len(password) < 8:
        return templates.TemplateResponse("admin/usuario_form.html",
            ctx(request, edit_user=None, err="La contraseña debe tener mínimo 8 caracteres"), status_code=400)
    u = models.User(
        username=username, full_name=full_name.strip(), email=email.strip(),
        password_hash=auth.hash_password(password), role=role,
        is_active=True, must_change_password=True,
    )
    db.add(u); db.commit()
    return RedirectResponse("/admin/usuarios", status_code=303)


@app.get("/admin/usuarios/{uid}", response_class=HTMLResponse)
def usuario_edit_get(uid: int, request: Request, db: Session = Depends(get_db)):
    me = auth.current_user(request)
    if not me or not auth.can(me, "manage_users"):
        raise HTTPException(403)
    u = db.query(models.User).filter_by(id=uid).first()
    if not u: raise HTTPException(404)
    return templates.TemplateResponse("admin/usuario_form.html", ctx(request, edit_user=u, err=None))


@app.post("/admin/usuarios/{uid}")
def usuario_edit_post(uid: int, request: Request,
                      full_name: str = Form(""), email: str = Form(""),
                      role: str = Form("lector"), is_active: str = Form(""),
                      new_password: str = Form(""),
                      db: Session = Depends(get_db)):
    me = auth.current_user(request)
    if not me or not auth.can(me, "manage_users"):
        raise HTTPException(403)
    u = db.query(models.User).filter_by(id=uid).first()
    if not u: raise HTTPException(404)
    u.full_name = full_name.strip(); u.email = email.strip()
    if role in models.ROLES:
        if u.role == "evaluador" and role != "evaluador":
            n_eval = db.query(models.User).filter_by(role="evaluador", is_active=True).count()
            if n_eval <= 1:
                return templates.TemplateResponse("admin/usuario_form.html",
                    ctx(request, edit_user=u, err="No se puede quitar el rol al último evaluador activo"), status_code=400)
        u.role = role
    new_active = bool(is_active)
    if u.is_active and not new_active and u.role == "evaluador":
        n_eval = db.query(models.User).filter_by(role="evaluador", is_active=True).count()
        if n_eval <= 1:
            return templates.TemplateResponse("admin/usuario_form.html",
                ctx(request, edit_user=u, err="No se puede desactivar al último evaluador"), status_code=400)
    u.is_active = new_active
    if new_password:
        if len(new_password) < 8:
            return templates.TemplateResponse("admin/usuario_form.html",
                ctx(request, edit_user=u, err="Mínimo 8 caracteres en la contraseña"), status_code=400)
        u.password_hash = auth.hash_password(new_password)
        u.must_change_password = True
    db.add(u); db.commit()
    return RedirectResponse("/admin/usuarios", status_code=303)


@app.post("/admin/usuarios/{uid}/eliminar")
def usuario_delete(uid: int, request: Request, db: Session = Depends(get_db)):
    me = auth.current_user(request)
    if not me or not auth.can(me, "manage_users"):
        raise HTTPException(403)
    u = db.query(models.User).filter_by(id=uid).first()
    if not u: raise HTTPException(404)
    if u.id == me.id:
        raise HTTPException(400, "No puedes eliminar tu propia cuenta")
    if u.role == "evaluador":
        n_eval = db.query(models.User).filter_by(role="evaluador", is_active=True).count()
        if n_eval <= 1:
            raise HTTPException(400, "No se puede eliminar al último evaluador")
    db.delete(u); db.commit()
    return RedirectResponse("/admin/usuarios", status_code=303)


# ============================================================
#                    FORMULARIOS
# ============================================================
@app.get("/encuesta/{code}", response_class=HTMLResponse)
def encuesta_get(code: str, request: Request):
    form = get_form(code)
    if not form: raise HTTPException(404)
    me = auth.current_user(request)
    if code in PRIVATE_FORMS and not auth.can(me, "fill_qual"):
        return RedirectResponse(url=f"/login?next=/encuesta/{code}", status_code=303)
    return templates.TemplateResponse("encuesta.html", ctx(request, form=form, draft_id=uuid.uuid4().hex))


@app.post("/encuesta/{code}")
async def encuesta_post(code: str, request: Request, db: Session = Depends(get_db)):
    form = get_form(code)
    if not form: raise HTTPException(404)
    me = auth.current_user(request)
    if code in PRIVATE_FORMS and not auth.can(me, "fill_qual"):
        return RedirectResponse("/login", status_code=303)
    raw = await request.form()
    data = {}
    for qid in all_question_ids(form):
        val = raw.get(qid, "")
        if hasattr(val, "filename"): continue
        data[qid] = val if isinstance(val, str) else str(val)
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
        institucion=data.get("institucion"), sexo=data.get("sexo"),
        edad=(int(data["edad"]) if str(data.get("edad", "")).isdigit() else None),
        data=data,
        user_agent=request.headers.get("user-agent", "")[:300],
        ip=request.client.host if request.client else None,
    )
    db.add(response); db.commit(); db.refresh(response)
    if draft_id:
        src = AUDIO_DIR / code / draft_id
        if src.exists():
            dst = AUDIO_DIR / code / str(response.id)
            dst.mkdir(parents=True, exist_ok=True)
            for f in src.iterdir():
                shutil.move(str(f), dst / f.name)
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
#                    UPLOADS
# ============================================================
@app.post("/upload-audio/{code}/{draft_id}/{qid}")
async def upload_audio(code: str, draft_id: str, qid: str, request: Request, audio: UploadFile = File(...)):
    form = get_form(code)
    if not form or qid not in all_question_ids(form): raise HTTPException(400)
    if code in PRIVATE_FORMS and not auth.can(auth.current_user(request), "fill_qual"):
        raise HTTPException(401)
    if not draft_id.isalnum() or len(draft_id) > 64: raise HTTPException(400)
    dst_dir = AUDIO_DIR / code / draft_id; dst_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{qid}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.webm"
    content = await audio.read()
    (dst_dir / fname).write_bytes(content)
    return JSONResponse({"ok": True, "size": len(content), "filename": fname})


@app.post("/upload-file/{code}/{draft_id}/{qid}")
async def upload_file(code: str, draft_id: str, qid: str, request: Request, file: UploadFile = File(...)):
    form = get_form(code)
    if not form or qid not in all_question_ids(form): raise HTTPException(400)
    if code in PRIVATE_FORMS and not auth.can(auth.current_user(request), "fill_qual"):
        raise HTTPException(401)
    if not draft_id.isalnum() or len(draft_id) > 64: raise HTTPException(400)
    dst_dir = UPLOADS_DIR / code / draft_id; dst_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "").suffix[:10] or ".bin"
    (dst_dir / f"{qid}{ext}").write_bytes(await file.read())
    return JSONResponse({"ok": True})


# ============================================================
#                    PÁGINA DE RESULTADOS
# ============================================================
@app.get("/resultados", response_class=HTMLResponse)
def resultados(request: Request, token: str = "", db: Session = Depends(get_db)):
    me = auth.current_user(request)
    if not me and not auth.verify_public_results_token(token):
        return templates.TemplateResponse("resultados_acceso.html", ctx(request,
            results_url=f"/resultados?token={auth.public_results_token()}"))
    is_internal = bool(me) and auth.can(me, "view_admin")
    payload = results_mod.build_full_results(db, include_audios=is_internal)
    return templates.TemplateResponse("resultados.html", ctx(request,
        payload=payload, token=token, is_evaluator=is_internal,
        ai_status=("activo" if ai_hooks.is_ai_enabled() else "pendiente"),
    ))


# ============================================================
#                    PANEL ADMIN
# ============================================================
@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    me = auth.current_user(request)
    if not me or not auth.can(me, "view_admin"):
        return RedirectResponse("/login?next=/admin", status_code=303)
    overview = results_mod.overview_metrics(db)
    n_users = db.query(models.User).count() if auth.can(me, "manage_users") else None
    return templates.TemplateResponse("admin/dashboard.html", ctx(request,
        overview=overview, n_users=n_users,
        public_results_url=f"/resultados?token={auth.public_results_token()}",
    ))


@app.get("/admin/respuestas/{code}", response_class=HTMLResponse)
def admin_respuestas(code: str, request: Request, db: Session = Depends(get_db)):
    me = auth.current_user(request)
    if not me or not auth.can(me, "view_admin"):
        return RedirectResponse("/login", status_code=303)
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
    me = auth.current_user(request)
    if not me or not auth.can(me, "view_admin"):
        return RedirectResponse("/login", status_code=303)
    form = get_form(code)
    if not form: raise HTTPException(404)
    r = db.query(models.SurveyResponse).filter_by(form_code=code, id=rid).first()
    if not r: raise HTTPException(404)
    audio_dir = AUDIO_DIR / code / str(rid)
    audios = sorted([p.name for p in audio_dir.glob("*.webm")]) if audio_dir.exists() else []
    transcripts = {t.filename: t for t in db.query(models.AudioTranscript).filter_by(response_id=rid).all()}
    return templates.TemplateResponse("admin/respuesta_detalle.html", ctx(request,
        form=form, r=r, audios=audios, transcripts=transcripts,
    ))


@app.get("/admin/audio/{code}/{rid}/{filename}")
def admin_audio(code: str, rid: int, filename: str, request: Request):
    me = auth.current_user(request)
    if not me or not auth.can(me, "view_admin"):
        raise HTTPException(401)
    p = (AUDIO_DIR / code / str(rid) / filename).resolve()
    if not str(p).startswith(str(AUDIO_DIR.resolve())) or not p.is_file():
        raise HTTPException(404)
    return FileResponse(p, media_type="audio/webm", filename=filename)


@app.get("/admin/export/{code}.xlsx")
def admin_export(code: str, request: Request, db: Session = Depends(get_db)):
    me = auth.current_user(request)
    if not me or not auth.can(me, "view_admin"):
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
    me = auth.current_user(request)
    if not me or not auth.can(me, "download_db"):
        raise HTTPException(403)
    db_path = DATA_DIR / "cutervo.db"
    if not db_path.is_file(): raise HTTPException(404)
    fname = f"cutervo_backup_{datetime.utcnow():%Y%m%d_%H%M}.db"
    return FileResponse(db_path, media_type="application/octet-stream", filename=fname)


@app.post("/admin/ai/transcribe-all")
def admin_transcribe_all(request: Request, db: Session = Depends(get_db)):
    me = auth.current_user(request)
    if not me or not auth.can(me, "ai_run"):
        raise HTTPException(403)
    if not ai_hooks.is_ai_enabled():
        return JSONResponse({"ok": False, "msg": "Configura OPENAI_API_KEY"})
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
    return JSONResponse({"ok": True, "procesados": procesados})


@app.get("/health")
def health():
    return {"ok": True, "service": "cutervo-eval-portal", "now": datetime.utcnow().isoformat(), "ai": ai_hooks.is_ai_enabled()}
