"""Ejecuta análisis temático Gemini sobre los instrumentos cualitativos."""
from app.database import SessionLocal
from app import models, ai_hooks
from app.surveys_def import get_form

db = SessionLocal()
print("Iniciando análisis IA por instrumento...\n")

for code in ["kii", "fgd_jovenes", "fgd_docentes", "observacion", "msc"]:
    items = []
    form = get_form(code)
    if not form: continue
    rows = db.query(models.SurveyResponse).filter_by(form_code=code).all()
    # textos escritos
    for r in rows:
        for sec in form["sections"]:
            for q in sec["questions"]:
                if q["type"] in ("textarea", "audio_text"):
                    v = ((r.data or {}).get(q["id"]) or "").strip()
                    if v and len(v) > 10:
                        items.append({"qid": q["id"], "label": q["label"], "text": v, "response_id": r.id})
    # transcripciones
    ts = db.query(models.AudioTranscript).filter_by(form_code=code, status="done").all()
    for t in ts:
        qlabel = ""
        for sec in form["sections"]:
            for q in sec["questions"]:
                if q["id"] == t.qid: qlabel = q["label"]; break
        items.append({"qid": t.qid, "label": "🎙 " + qlabel, "text": t.transcript or "", "response_id": t.response_id})

    print(f"  ▸ {code}: {len(items)} items")
    if not items:
        print(f"    (sin contenido, skip)\n"); continue
    res = ai_hooks.analyze_qualitative(code, items)
    if res["status"] == "done":
        db.query(models.FormAnalysis).filter_by(form_code=code).delete()
        fa = models.FormAnalysis(form_code=code, payload=res["data"], model=res["model"])
        db.add(fa); db.commit()
        # resumen
        n_temas = sum(len(v.get("temas", [])) for v in res["data"].values())
        print(f"    ✓ Análisis guardado · {n_temas} temas extraídos en 6 criterios\n")
    else:
        print(f"    ✗ {res['status']}: {(res.get('error') or '')[:200]}\n")

print("Listo.")
