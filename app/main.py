"""Centro de Evaluación Cutervo — entry point."""
import os
import secrets
from pathlib import Path
from datetime import datetime
from io import BytesIO

from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from openpyxl import Workbook

from .database import Base, engine, get_db
from . import models
from .surveys_def import get_form, all_question_ids, ENCUESTA_ESTUDIANTES, ENCUESTA_DOCENTES

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR.parent / "docs"

# crear tablas
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Centro de Evaluación Cutervo")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

security = HTTPBasic()


def require_admin(credentials: HTTPBasicCredentials = Depends(security)):
    user = os.getenv("ADMIN_USER", "admin")
    pwd = os.getenv("ADMIN_PASS", "admin")
    ok_user = secrets.compare_digest(credentials.username, user)
    ok_pwd = secrets.compare_digest(credentials.password, pwd)
    if not (ok_user and ok_pwd):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# ---------------------- Páginas públicas ----------------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/cronograma", response_class=HTMLResponse)
def cronograma(request: Request):
    return templates.TemplateResponse("cronograma.html", {"request": request})


@app.get("/documentos", response_class=HTMLResponse)
def documentos(request: Request):
    items = []
    if DOCS_DIR.exists():
        for p in sorted(DOCS_DIR.iterdir()):
            if p.is_file():
                items.append({"name": p.name, "size_kb": round(p.stat().st_size / 1024, 1)})
    return templates.TemplateResponse("documentos.html", {"request": request, "items": items})


@app.get("/documentos/{filename}")
def descargar(filename: str):
    safe = (DOCS_DIR / filename).resolve()
    if not safe.is_file() or DOCS_DIR.resolve() not in safe.parents:
        raise HTTPException(404)
    return FileResponse(safe, filename=filename)


# ---------------------- Encuestas ----------------------
@app.get("/encuesta/{code}", response_class=HTMLResponse)
def encuesta_get(code: str, request: Request):
    form = get_form(code)
    if not form:
        raise HTTPException(404)
    return templates.TemplateResponse("encuesta.html", {"request": request, "form": form})


@app.post("/encuesta/{code}")
async def encuesta_post(code: str, request: Request, db: Session = Depends(get_db)):
    form = get_form(code)
    if not form:
        raise HTTPException(404)
    raw = await request.form()
    data = {k: raw.get(k, "") for k in all_question_ids(form)}
    # validación mínima
    missing = []
    for sec in form["sections"]:
        for q in sec["questions"]:
            if q.get("required") and not data.get(q["id"]):
                missing.append(q["label"])
    if missing:
        return templates.TemplateResponse(
            "encuesta.html",
            {"request": request, "form": form, "errors": missing, "data": data},
            status_code=400,
        )
    response = models.SurveyResponse(
        form_code=code,
        institucion=data.get("institucion"),
        sexo=data.get("sexo"),
        edad=(int(data["edad"]) if str(data.get("edad", "")).isdigit() else None),
        data=dict(data),
        user_agent=request.headers.get("user-agent", "")[:300],
        ip=request.client.host if request.client else None,
    )
    db.add(response)
    db.commit()
    return templates.TemplateResponse(
        "gracias.html", {"request": request, "form": form}
    )


# ---------------------- Admin ----------------------
@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, user: str = Depends(require_admin), db: Session = Depends(get_db)):
    total_est = db.query(models.SurveyResponse).filter_by(form_code="estudiantes").count()
    total_doc = db.query(models.SurveyResponse).filter_by(form_code="docentes").count()
    META_EST = 196
    META_DOC = 24
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "total_est": total_est, "total_doc": total_doc,
        "meta_est": META_EST, "meta_doc": META_DOC,
        "pct_est": min(100, round(100*total_est/META_EST, 1) if META_EST else 0),
        "pct_doc": min(100, round(100*total_doc/META_DOC, 1) if META_DOC else 0),
    })


@app.get("/admin/respuestas/{code}", response_class=HTMLResponse)
def admin_respuestas(code: str, request: Request, user: str = Depends(require_admin), db: Session = Depends(get_db)):
    form = get_form(code)
    if not form:
        raise HTTPException(404)
    rows = db.query(models.SurveyResponse).filter_by(form_code=code).order_by(models.SurveyResponse.created_at.desc()).limit(500).all()
    return templates.TemplateResponse("admin/respuestas.html", {
        "request": request, "form": form, "rows": rows,
    })


@app.get("/admin/export/{code}.xlsx")
def admin_export(code: str, user: str = Depends(require_admin), db: Session = Depends(get_db)):
    form = get_form(code)
    if not form:
        raise HTTPException(404)
    rows = db.query(models.SurveyResponse).filter_by(form_code=code).order_by(models.SurveyResponse.created_at.asc()).all()
    wb = Workbook(); ws = wb.active; ws.title = code[:30]
    headers = ["id", "created_at"] + all_question_ids(form)
    ws.append(headers)
    for r in rows:
        ws.append([r.id, r.created_at.isoformat()] + [str(r.data.get(k, "")) for k in all_question_ids(form)])
    buf = BytesIO(); wb.save(buf); buf.seek(0)
    fname = f"respuestas_{code}_{datetime.utcnow():%Y%m%d_%H%M}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@app.get("/health")
def health():
    return {"ok": True, "service": "cutervo-eval-portal", "now": datetime.utcnow().isoformat()}
