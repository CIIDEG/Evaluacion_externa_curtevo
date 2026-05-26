"""Compilador de resultados — agrega datos cuantitativos y cualitativos."""
from collections import Counter, defaultdict
from sqlalchemy.orm import Session
from . import models
from .surveys_def import ALL_FORMS, get_form

# Mapeo formulario → criterio CAD predominante (para narrativa)
FORM_TO_CAD = {
    "estudiantes": ["EFICACIA", "IMPACTO"],
    "docentes": ["EFICACIA", "EFICIENCIA", "SOSTENIBILIDAD"],
    "kii": ["PERTINENCIA", "COHERENCIA", "EFICIENCIA", "EFICACIA", "IMPACTO", "SOSTENIBILIDAD"],
    "fgd_jovenes": ["EFICACIA", "IMPACTO"],
    "fgd_docentes": ["EFICIENCIA", "EFICACIA", "SOSTENIBILIDAD"],
    "observacion": ["EFICACIA", "SOSTENIBILIDAD"],
    "msc": ["IMPACTO"],
}


def overview_metrics(db: Session) -> dict:
    metas = {"estudiantes":196,"docentes":24,"kii":18,"fgd_jovenes":3,"fgd_docentes":3,"observacion":12,"msc":12}
    out = {"forms": [], "total_responses": 0, "total_audios": 0}
    for f in ALL_FORMS:
        code = f["code"]
        n = db.query(models.SurveyResponse).filter_by(form_code=code).count()
        meta = metas.get(code, 0) or 1
        out["forms"].append({
            "code": code, "title": f["title"], "kind": f.get("kind","encuesta"),
            "total": n, "meta": metas.get(code, "—"),
            "pct": min(100, round(100*n/meta, 1)),
        })
        out["total_responses"] += n
    out["total_audios"] = db.query(models.AudioTranscript).count()
    return out


def quantitative_analysis(db: Session, form_code: str) -> dict:
    """Tabula respuestas tipo radio/select/likert del formulario."""
    form = get_form(form_code)
    if not form:
        return {}
    rows = db.query(models.SurveyResponse).filter_by(form_code=form_code).all()
    if not rows:
        return {"n": 0, "questions": []}
    out = {"n": len(rows), "form_title": form["title"], "questions": []}
    for sec in form["sections"]:
        for q in sec["questions"]:
            if q["type"] in ("radio", "select", "likert"):
                counter = Counter()
                for r in rows:
                    v = (r.data or {}).get(q["id"], "")
                    if v:
                        counter[str(v)] += 1
                if counter:
                    total = sum(counter.values())
                    labels = q.get("options") or sorted(counter.keys())
                    if q["type"] == "likert":
                        labels = ["1","2","3","4","5"]
                    data = [{"label": L, "count": counter.get(str(L), 0),
                             "pct": round(100*counter.get(str(L),0)/total,1) if total else 0}
                            for L in labels]
                    out["questions"].append({
                        "qid": q["id"], "label": q["label"], "type": q["type"],
                        "section": sec["title"], "data": data, "total": total,
                    })
    # Desagregación por sexo (si hay)
    sex_counter = Counter()
    for r in rows:
        s = (r.data or {}).get("sexo") or r.sexo or "—"
        sex_counter[s] += 1
    out["by_sex"] = [{"label": k, "count": v} for k,v in sex_counter.items()]
    # Por institución
    inst_counter = Counter()
    for r in rows:
        i = (r.data or {}).get("institucion") or r.institucion or "—"
        inst_counter[i] += 1
    out["by_institucion"] = [{"label": k, "count": v} for k,v in sorted(inst_counter.items(), key=lambda x:-x[1])]
    return out


def qualitative_excerpts(db: Session, form_code: str) -> list:
    """Devuelve fragmentos textuales con metadatos para el análisis cualitativo."""
    form = get_form(form_code)
    if not form:
        return []
    rows = db.query(models.SurveyResponse).filter_by(form_code=form_code).all()
    text_qids = []
    for sec in form["sections"]:
        for q in sec["questions"]:
            if q["type"] in ("textarea", "audio_text"):
                text_qids.append({"qid": q["id"], "label": q["label"]})
    out = []
    for r in rows:
        for tq in text_qids:
            val = (r.data or {}).get(tq["qid"], "").strip()
            if val and len(val) > 10:
                out.append({
                    "response_id": r.id,
                    "form_code": form_code,
                    "qid": tq["qid"],
                    "label": tq["label"],
                    "text": val,
                    "institucion": r.institucion,
                    "sexo": r.sexo,
                    "created_at": r.created_at.isoformat(),
                })
    return out


def all_audios(db: Session) -> list:
    """Lista todos los audios capturados con su respuesta."""
    from pathlib import Path
    AUDIO_DIR = Path("/code/data/audio")
    out = []
    if not AUDIO_DIR.exists():
        return out
    for form_dir in sorted(AUDIO_DIR.iterdir()):
        if not form_dir.is_dir():
            continue
        for resp_dir in sorted(form_dir.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 0):
            if not resp_dir.is_dir() or not resp_dir.name.isdigit():
                continue
            for audio_file in sorted(resp_dir.glob("*.webm")):
                qid = audio_file.name.split("-")[0]
                # buscar transcript si existe
                t = db.query(models.AudioTranscript).filter_by(
                    form_code=form_dir.name, response_id=int(resp_dir.name),
                    filename=audio_file.name,
                ).first()
                out.append({
                    "form_code": form_dir.name,
                    "response_id": int(resp_dir.name),
                    "qid": qid,
                    "filename": audio_file.name,
                    "size_kb": round(audio_file.stat().st_size / 1024, 1),
                    "transcript": (t.transcript if t else None),
                    "status": (t.status if t else "no_record"),
                })
    return out


def build_full_results(db: Session, include_audios: bool = False) -> dict:
    """Construye el payload completo para la página de resultados.

    Si include_audios=True (evaluador logueado), incluye la lista completa de audios.
    """
    out = {
        "overview": overview_metrics(db),
        "quantitative": {},
        "qualitative": {},
        "cad_index": defaultdict(list),
        "audios": [],
    }
    for f in ALL_FORMS:
        code = f["code"]
        if f.get("kind") == "encuesta":
            out["quantitative"][code] = quantitative_analysis(db, code)
        out["qualitative"][code] = qualitative_excerpts(db, code)
        for crit in FORM_TO_CAD.get(code, []):
            out["cad_index"][crit].append(code)
    out["cad_index"] = dict(out["cad_index"])
    if include_audios:
        out["audios"] = all_audios(db)
    return out
