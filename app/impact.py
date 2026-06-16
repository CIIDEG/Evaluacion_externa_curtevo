"""Cálculo del Nivel de Impacto.

Convierte respuestas cerradas (radio, likert, select) a una escala 0-100,
agrega por dimensión (sección del cuestionario) y por instrumento.

Para instrumentos cualitativos (KII, FGD, MSC, observación) calcula
métricas proxy: cobertura, profundidad y volumen por dimensión, mientras
no se active el análisis IA semántico.
"""
from collections import defaultdict
from statistics import mean
from sqlalchemy.orm import Session

from . import models
from .surveys_def import get_form


# -----------------------------------------------------------
# Mapeos de opciones → puntaje 0-100
# -----------------------------------------------------------
SCORE_MAPS = {
    # Likert 1-5 ya viene 1..5
    "likert_1_5": {"1": 20, "2": 40, "3": 60, "4": 80, "5": 100},
    # Sí/No
    "si_no": {"Sí": 100, "No": 0, "Si": 100},
    # 3-niveles: Sí / En parte / No
    "si_enparte_no": {"Sí": 100, "En parte": 50, "No": 0},
    # 3-niveles: Siempre / A veces / Nunca
    "siempre_aveces_nunca": {"Siempre": 100, "A veces": 50, "Nunca": 0},
    # 3-niveles: Sí / Probablemente / No
    "si_probablemente_no": {"Sí": 100, "Probablemente": 60, "No": 0},
    # 3-niveles: Sí / En proceso / No
    "si_enproceso_no": {"Sí": 100, "En proceso": 60, "No": 0},
    # 4-niveles: Mucho / Algo / Poco / Nada
    "mucho_algo_poco_nada": {"Mucho": 100, "Algo": 70, "Poco": 30, "Nada": 0},
    # 4-niveles para observación: Operativo / Incipiente / Inactivo / No existe
    "operativo_4": {"Operativo": 100, "Incipiente": 60, "Inactivo": 20, "No existe": 0},
}

# Excluir del score: respuestas neutras / no clasificables
NEUTRO = {"No aplica", "Prefiero no decir", "—", "", None}


# -----------------------------------------------------------
# Asignación de mapeo a cada pregunta (por form_code → qid)
# Las preguntas no listadas son ignoradas para el score.
# -----------------------------------------------------------
QUESTION_MAP = {
    "estudiantes": {
        "b1_participo":   "si_no",
        "b2_habilidad":   "likert_1_5",
        "b3_conocer":     "mucho_algo_poco_nada",
        "b4_equipo":      "si_no",
        "b5_activo":      "si_no",                # 'No aplica' se excluye
        "c2_consulta":    "si_no",
        "c3_conoc":       "likert_1_5",
        "d1_futuro":      "mucho_algo_poco_nada",
        "d2_metas":       "si_enparte_no",
        "d3_autoempleo":  "si_no",
        "e1_igual":       "si_enparte_no",
    },
    "docentes": {
        "b1_cursos":      "si_no",
        "b2_util":        "likert_1_5",
        "b3_aplica":      "siempre_aveces_nunca",
        "b4_protocolo":   "si_no",
        "b5_digital":     "si_enparte_no",
        "c1_organ":       "si_enparte_no",
        "c2_facilita":    "si_enparte_no",
        "d1_continua":    "si_probablemente_no",
        "d2_pei":         "si_enproceso_no",
    },
    "observacion": {
        "o1_estado":      "operativo_4",
    },
}

# Etiqueta amigable de cada dimensión por formulario (para no usar el título crudo)
DIMENSION_LABELS = {
    "estudiantes": {
        "B": ("R2 · Habilidades de emprendimiento", "Capacidad de idear y emprender"),
        "C": ("R3 · Derechos económicos y sociales", "Conciencia y ejercicio de DESC"),
        "D": ("Impacto · Proyecto de vida",          "Cambio en perspectivas y autoempleo"),
        "E": ("Enfoque de género",                   "Igualdad real de oportunidades"),
    },
    "docentes": {
        "B": ("R1 · Capacidades pedagógicas",        "Formación recibida y aplicación"),
        "C": ("Eficiencia y gestión",                "Organización, plataforma y apoyos"),
        "D": ("Sostenibilidad e impacto",            "Continuidad y cambios observados"),
    },
}


def _section_letter(section_title: str) -> str:
    """Extrae la letra de la sección a partir del título (ej. 'B. Habilidades' → 'B')."""
    t = section_title.strip()
    if len(t) >= 2 and t[1] == "." and t[0].isalpha():
        return t[0].upper()
    return t[:1].upper()


def score_value(qmap_key: str, raw_value):
    """Devuelve puntaje 0-100 o None si no se puede mapear."""
    if raw_value in NEUTRO or raw_value is None:
        return None
    mapping = SCORE_MAPS.get(qmap_key, {})
    raw_str = str(raw_value).strip()
    return mapping.get(raw_str)


# -----------------------------------------------------------
# Cálculo cuantitativo (estudiantes / docentes / observación)
# -----------------------------------------------------------
def compute_impact(db: Session, form_code: str) -> dict:
    form = get_form(form_code)
    if not form:
        return {}
    qmap = QUESTION_MAP.get(form_code, {})
    rows = db.query(models.SurveyResponse).filter_by(form_code=form_code).all()
    n = len(rows)
    if n == 0:
        return {"n": 0, "global": None, "dimensions": [], "form_title": form["title"]}

    # Para cada pregunta scoreable: lista de puntajes
    per_question_scores = defaultdict(list)  # qid → [scores 0-100]
    # Y por respondiente: lista de scores de TODAS sus respuestas (para promedio global)
    per_respondent = []  # list of mean per respondent

    for r in rows:
        scores_r = []
        for qid, kind in qmap.items():
            raw = (r.data or {}).get(qid, "")
            s = score_value(kind, raw)
            if s is not None:
                per_question_scores[qid].append(s)
                scores_r.append(s)
        if scores_r:
            per_respondent.append(mean(scores_r))

    # Reunir por dimensión (sección)
    dims_acc = defaultdict(lambda: {"scores": [], "qids": []})
    qid_to_label = {}
    for sec in form["sections"]:
        letter = _section_letter(sec["title"])
        for q in sec["questions"]:
            if q["id"] in qmap:
                qid_to_label[q["id"]] = q["label"]
                # añadir scores de esta pregunta a la dim
                qscores = per_question_scores.get(q["id"], [])
                dims_acc[letter]["scores"].extend(qscores)
                dims_acc[letter]["qids"].append({
                    "qid": q["id"],
                    "label": q["label"],
                    "n": len(qscores),
                    "score": round(mean(qscores), 1) if qscores else None,
                })

    label_dict = DIMENSION_LABELS.get(form_code, {})
    dimensions = []
    for letter, acc in sorted(dims_acc.items()):
        scores = acc["scores"]
        avg = round(mean(scores), 1) if scores else None
        lbl_name, lbl_desc = label_dict.get(letter, (f"Sección {letter}", ""))
        dimensions.append({
            "letter": letter,
            "title": lbl_name,
            "subtitle": lbl_desc,
            "score": avg,
            "n_answers": len(scores),
            "questions": acc["qids"],
            "color": _level_color(avg),
            "level": _level_label(avg),
        })

    global_score = round(mean(per_respondent), 1) if per_respondent else None
    return {
        "form_code": form_code,
        "form_title": form["title"],
        "n": n,
        "global": global_score,
        "global_color": _level_color(global_score),
        "global_level": _level_label(global_score),
        "dimensions": dimensions,
    }


def compute_impact_by_ie(db: Session, form_code: str) -> dict:
    """Calcula score de impacto agrupado por institución educativa.

    Devuelve {'ies': [{ie, n, global, B, C, D, E}], 'dim_keys': ['B','C','D','E']}
    """
    form = get_form(form_code)
    if not form: return {"ies": [], "dim_keys": []}
    qmap = QUESTION_MAP.get(form_code, {})
    if not qmap: return {"ies": [], "dim_keys": []}

    # Indexar qid → letter
    qid_to_letter = {}
    for sec in form["sections"]:
        letter = _section_letter(sec["title"])
        for q in sec["questions"]:
            if q["id"] in qmap:
                qid_to_letter[q["id"]] = letter

    rows = db.query(models.SurveyResponse).filter_by(form_code=form_code).all()
    by_ie = defaultdict(lambda: {"global": [], "dims": defaultdict(list)})

    for r in rows:
        ie = (r.data or {}).get("institucion") or r.institucion or "—"
        respondent_scores = []
        per_dim = defaultdict(list)
        for qid, kind in qmap.items():
            v = (r.data or {}).get(qid)
            s = score_value(kind, v)
            if s is not None:
                respondent_scores.append(s)
                per_dim[qid_to_letter.get(qid, "?")].append(s)
        if respondent_scores:
            by_ie[ie]["global"].append(sum(respondent_scores) / len(respondent_scores))
            for L, sc in per_dim.items():
                by_ie[ie]["dims"][L].extend(sc)

    dim_keys = sorted({l for v in by_ie.values() for l in v["dims"].keys()})
    out_rows = []
    for ie, d in by_ie.items():
        if not d["global"]: continue
        row = {
            "ie": ie,
            "n": len(d["global"]),
            "global": round(sum(d["global"]) / len(d["global"]), 1),
        }
        for L in dim_keys:
            scores = d["dims"].get(L, [])
            row[L] = round(sum(scores) / len(scores), 1) if scores else None
        row["color"] = _level_color(row["global"])
        out_rows.append(row)
    out_rows.sort(key=lambda x: -x["global"])
    return {"ies": out_rows, "dim_keys": dim_keys}


def _level_color(score):
    if score is None: return "#B5BDC9"  # gris
    if score >= 80:   return "#2EC4B6"  # aqua = alto
    if score >= 60:   return "#F7C559"  # gold = medio
    return "#FF5C4D"                    # coral = bajo


def _level_label(score):
    if score is None: return "—"
    if score >= 80:   return "Alto"
    if score >= 60:   return "Medio"
    if score >= 40:   return "Bajo"
    return "Muy bajo"


# -----------------------------------------------------------
# Métricas cualitativas (KII, FGD, MSC, observación-texto)
# -----------------------------------------------------------
def compute_qualitative_metrics(db: Session, form_code: str) -> dict:
    form = get_form(form_code)
    if not form:
        return {}
    rows = db.query(models.SurveyResponse).filter_by(form_code=form_code).all()
    n = len(rows)
    if n == 0:
        return {"n": 0, "dimensions": [], "form_title": form["title"]}

    dims_acc = defaultdict(lambda: {"qids": [], "covered_total": 0, "words_total": 0, "answers_total": 0})

    for sec in form["sections"]:
        letter = _section_letter(sec["title"])
        for q in sec["questions"]:
            if q["type"] not in ("textarea", "audio_text"):
                continue
            covered = 0
            word_total = 0
            for r in rows:
                v = ((r.data or {}).get(q["id"]) or "").strip()
                if len(v) >= 10:  # consideramos respuesta válida con >=10 caracteres
                    covered += 1
                    word_total += len(v.split())
            dims_acc[letter]["qids"].append({
                "qid": q["id"], "label": q["label"],
                "covered": covered, "total": n,
                "coverage_pct": round(100*covered/n, 1) if n else 0,
                "avg_words": round(word_total/covered, 1) if covered else 0,
            })
            dims_acc[letter]["covered_total"] += covered
            dims_acc[letter]["answers_total"] += n
            dims_acc[letter]["words_total"] += word_total

    dimensions = []
    for letter, acc in sorted(dims_acc.items()):
        cov = round(100 * acc["covered_total"] / acc["answers_total"], 1) if acc["answers_total"] else 0
        avg_words = round(acc["words_total"] / acc["covered_total"], 1) if acc["covered_total"] else 0
        dimensions.append({
            "letter": letter,
            "title": f"Sección {letter}",
            "coverage_pct": cov,
            "avg_words": avg_words,
            "volume": acc["covered_total"],
            "questions": acc["qids"],
            "color": _level_color(cov),
            "level": _level_label(cov),
        })

    # Score "global" = cobertura promedio entre dimensiones
    if dimensions:
        global_cov = round(mean([d["coverage_pct"] for d in dimensions]), 1)
    else:
        global_cov = 0

    return {
        "form_code": form_code,
        "form_title": form["title"],
        "n": n,
        "global": global_cov,
        "global_color": _level_color(global_cov),
        "global_level": _level_label(global_cov),
        "dimensions": dimensions,
    }


# -----------------------------------------------------------
# Resumen global de impacto a través de TODOS los instrumentos
# -----------------------------------------------------------
def build_impact_overview(db: Session) -> dict:
    """Construye el panel de Nivel de Impacto para todos los instrumentos."""
    cuanti_forms = ["estudiantes", "docentes"]
    quali_forms  = ["kii", "fgd_jovenes", "fgd_docentes", "observacion", "msc"]

    out = {"cuantitativos": [], "cualitativos": []}

    for code in cuanti_forms:
        out["cuantitativos"].append(compute_impact(db, code))
    for code in quali_forms:
        out["cualitativos"].append(compute_qualitative_metrics(db, code))

    # Promedio global = media de los globales de cuanti
    cuanti_globals = [c["global"] for c in out["cuantitativos"] if c.get("global") is not None]
    out["global_cuanti"] = round(mean(cuanti_globals), 1) if cuanti_globals else None
    out["global_cuanti_color"] = _level_color(out["global_cuanti"])
    out["global_cuanti_level"] = _level_label(out["global_cuanti"])

    quali_globals = [c["global"] for c in out["cualitativos"] if c.get("global") is not None]
    out["global_quali"] = round(mean(quali_globals), 1) if quali_globals else None
    out["global_quali_color"] = _level_color(out["global_quali"])
    out["global_quali_level"] = _level_label(out["global_quali"])

    return out
