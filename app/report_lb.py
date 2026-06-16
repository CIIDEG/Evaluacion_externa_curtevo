"""Informe automatizado enriquecido con tablas, gráficos numerados y análisis.

Estructura:
- I. Datos generales
- II. Objetivo · III. Metodología
- IV. Resultados (4.1 Perfil · 4.2 Emprendimiento · 4.3 Derechos/Género · 4.4 Proyecto de vida · 4.5 Docentes · 4.6 Impacto y comparativos)
- V. Conclusiones (auto) · VI. Recomendaciones (condicionales)
"""
from collections import Counter, defaultdict
from datetime import datetime
from statistics import mean
from sqlalchemy.orm import Session

from . import models
from .surveys_def import get_form
from . import impact as impact_mod

FUENTE_EST = "Encuesta a estudiantes — Proyecto SOLPCD/2024/0118 (Cutervo, Cajamarca)"
FUENTE_DOC = "Encuesta a docentes — Proyecto SOLPCD/2024/0118 (Cutervo, Cajamarca)"
FUENTE_CALI = "Instrumentos cualitativos del proyecto (KII, FGD, MSC, observación)"


# ============================================================
#                       HELPERS BÁSICOS
# ============================================================
def _count_field(rows, field, exclude_otra=True):
    c = Counter()
    for r in rows:
        v = (r.data or {}).get(field) or "—"
        c[v] += 1
    total = sum(c.values()) or 1
    items = [{"label": k, "n": v, "pct": round(100 * v / total, 1)}
             for k, v in c.most_common()]
    return items, total


def _count_radio(rows, qid):
    """Cuenta opciones de un radio/select para un qid."""
    c = Counter()
    for r in rows:
        v = (r.data or {}).get(qid)
        if v: c[v] += 1
    total = sum(c.values()) or 1
    return [{"label": k, "n": v, "pct": round(100 * v / total, 1)} for k, v in c.most_common()], total


def _count_likert(rows, qid):
    """Distribución Likert 1-5."""
    c = Counter()
    for r in rows:
        v = (r.data or {}).get(qid)
        try:
            vv = int(v)
            if 1 <= vv <= 5: c[str(vv)] += 1
        except (TypeError, ValueError): continue
    total = sum(c.values()) or 1
    out = []
    LABELS = {"1": "Muy poco", "2": "Poco", "3": "Regular", "4": "Fortalecido", "5": "Muy fortalecido"}
    for n in ("1", "2", "3", "4", "5"):
        v = c.get(n, 0)
        out.append({"label": f"{n} – {LABELS[n]}", "n": v, "pct": round(100 * v / total, 1)})
    promedio = round(sum(int(k) * v for k, v in c.items()) / total, 2) if c else 0
    return out, total, promedio


def _crosstab(rows, row_field, col_field):
    """Cruza dos campos categóricos. Devuelve filas con conteos y % por fila."""
    matrix = defaultdict(Counter)
    for r in rows:
        rv = (r.data or {}).get(row_field) or "—"
        cv = (r.data or {}).get(col_field) or "—"
        matrix[rv][cv] += 1
    cols = sorted({c for v in matrix.values() for c in v.keys()})
    out = []
    for k, counter in matrix.items():
        total = sum(counter.values()) or 1
        out.append({
            "row": k, "total": total,
            "cells": [{"col": c, "n": counter.get(c, 0),
                       "pct": round(100 * counter.get(c, 0) / total, 1)} for c in cols],
        })
    return cols, out


def _pct(rows, qid, positive):
    n = 0; ok = 0
    for r in rows:
        v = (r.data or {}).get(qid)
        if v:
            n += 1
            if v in positive: ok += 1
    return round(100 * ok / n, 1) if n else 0


# ============================================================
#                INTERPRETACIONES AUTOMÁTICAS
# ============================================================
def _interp_top_bottom(items, what, total):
    """Genera interpretación: el más alto, el más bajo y dato global."""
    if not items: return ""
    items_sorted = sorted(items, key=lambda x: -x["n"])
    top = items_sorted[0]
    text = (f"Sobre un total de {total} respuestas analizadas, "
            f"el grupo más numeroso corresponde a «{top['label']}» con un {top['pct']}% ({top['n']} casos). ")
    if len(items_sorted) >= 2:
        b = items_sorted[-1]
        text += f"En el otro extremo, «{b['label']}» concentra el {b['pct']}% ({b['n']} casos). "
    text += f"Esta distribución permite visualizar la {what} de los participantes y orientar acciones diferenciadas."
    return text


def _interp_likert(items, total, promedio, dimension):
    nivel = "alto" if promedio >= 4 else "intermedio" if promedio >= 3 else "bajo"
    alto = (items[3]["pct"] + items[4]["pct"]) if len(items) >= 5 else 0
    bajo = (items[0]["pct"] + items[1]["pct"]) if len(items) >= 5 else 0
    return (f"El promedio de autopercepción en «{dimension}» es {promedio}/5, lo que indica un nivel {nivel}. "
            f"Un {round(alto,1)}% se ubica en niveles fortalecido/muy fortalecido (4–5) y un {round(bajo,1)}% en niveles bajos (1–2). "
            f"{'Se recomienda mantener y profundizar el trabajo en esta dimensión.' if promedio >= 4 else 'Es prioritario reforzar esta dimensión con sesiones específicas.' if promedio < 3 else 'Existe oportunidad clara de mejora con acciones complementarias.'}")


def _interp_si_no(items, qid_label):
    if not items: return ""
    si = next((i["pct"] for i in items if i["label"] == "Sí"), 0)
    no = next((i["pct"] for i in items if i["label"] == "No"), 0)
    return (f"En relación a «{qid_label}», el {si}% responde afirmativamente y el {no}% negativamente. "
            + (f"Este resultado evidencia un alcance significativo de la intervención." if si >= 70 else
               f"Aún hay un margen importante de población por incorporar." if si < 50 else
               f"La cobertura es moderada y conviene revisar las barreras de acceso."))


def _interp_equidad(rows_est, eq_por_sexo):
    si = _pct(rows_est, "e1_igual", {"Sí"})
    parte = _pct(rows_est, "e1_igual", {"En parte"})
    no = _pct(rows_est, "e1_igual", {"No"})
    txt = (f"En la percepción global de equidad, el {si}% considera que sí hubo igualdad de oportunidades, "
           f"un {parte}% lo percibe parcialmente y un {no}% lo niega. ")
    if eq_por_sexo and "Mujer" in eq_por_sexo and "Hombre" in eq_por_sexo:
        m_no = eq_por_sexo["Mujer"]["no"]; h_no = eq_por_sexo["Hombre"]["no"]
        if m_no > h_no:
            txt += (f"Desagregado por sexo, las estudiantes mujeres reportan en mayor proporción la ausencia de equidad "
                    f"({m_no}% vs {h_no}% hombres), lo que evidencia una brecha de género en la experiencia del proyecto.")
        else:
            txt += "La percepción es similar entre sexos."
    return txt


def _interp_impact_by_ie(by_ie):
    if not by_ie["ies"]: return ""
    top = by_ie["ies"][0]
    bot = by_ie["ies"][-1]
    text = (f"La IE «{top['ie']}» alcanza el mejor score global de impacto ({top['global']}/100, n={top['n']}), "
            f"mientras que «{bot['ie']}» registra el menor ({bot['global']}/100, n={bot['n']}). ")
    diff = top["global"] - bot["global"]
    if diff >= 20:
        text += (f"La diferencia de {round(diff,1)} puntos entre ambos extremos sugiere heterogeneidad en la implementación "
                 f"o en las condiciones contextuales de cada IE. Recomendable: profundizar análisis cualitativo en las IIEE con menor score "
                 f"para identificar factores limitantes.")
    else:
        text += (f"La diferencia de {round(diff,1)} puntos entre ambos extremos es moderada, lo que indica una implementación bastante homogénea entre IIEE.")
    return text


# ============================================================
#                    BUILDER PRINCIPAL
# ============================================================
def build_report(db: Session) -> dict:
    rows_est = db.query(models.SurveyResponse).filter_by(form_code="estudiantes").all()
    rows_doc = db.query(models.SurveyResponse).filter_by(form_code="docentes").all()

    n_est = len(rows_est); n_doc = len(rows_doc)
    fechas = [r.created_at for r in (rows_est + rows_doc) if r.created_at]
    fecha_min = min(fechas).strftime("%B %Y") if fechas else "—"
    fecha_max = max(fechas).strftime("%B %Y") if fechas else "—"
    iiee_set = {(r.data or {}).get("institucion") for r in rows_est if (r.data or {}).get("institucion")}
    iiee_set.discard(None)
    n_iiee = len(iiee_set)

    # ---------- PERFIL ----------
    ie_items, ie_total = _count_field(rows_est, "institucion")
    sexo_items, _ = _count_field(rows_est, "sexo")
    zona_items, _ = _count_field(rows_est, "zona")
    grado_items, _ = _count_field(rows_est, "grado")
    edades = [r.edad for r in rows_est if r.edad]
    edad_avg = round(mean(edades), 1) if edades else None

    # ---------- EMPRENDIMIENTO ----------
    e_participo, _ = _count_radio(rows_est, "b1_participo")
    e_habilidad, _, prom_hab = _count_likert(rows_est, "b2_habilidad")
    e_conoce, _ = _count_radio(rows_est, "b3_conocer")
    e_equipo, _ = _count_radio(rows_est, "b4_equipo")
    e_activo, _ = _count_radio(rows_est, "b5_activo")

    # ---------- DERECHOS Y GÉNERO ----------
    e_consulta, _ = _count_radio(rows_est, "c2_consulta")
    e_conoc_der, _, prom_conoc = _count_likert(rows_est, "c3_conoc")
    e_equidad, _ = _count_radio(rows_est, "e1_igual")

    # Equidad por sexo
    eq_por_sexo = {}
    for sx in ("Mujer", "Hombre"):
        sx_rows = [r for r in rows_est if (r.data or {}).get("sexo") == sx]
        if sx_rows:
            eq_por_sexo[sx] = {
                "si": _pct(sx_rows, "e1_igual", {"Sí"}),
                "parte": _pct(sx_rows, "e1_igual", {"En parte"}),
                "no": _pct(sx_rows, "e1_igual", {"No"}),
                "n": len(sx_rows),
            }

    # ---------- PROYECTO DE VIDA ----------
    e_futuro, _ = _count_radio(rows_est, "d1_futuro")
    e_metas, _ = _count_radio(rows_est, "d2_metas")
    e_autoempleo, _ = _count_radio(rows_est, "d3_autoempleo")

    # ---------- DOCENTES ----------
    d_cursos, _ = _count_radio(rows_doc, "b1_cursos")
    d_util, _, prom_util = _count_likert(rows_doc, "b2_util")
    d_aplica, _ = _count_radio(rows_doc, "b3_aplica")
    d_protocolo, _ = _count_radio(rows_doc, "b4_protocolo")
    d_digital, _ = _count_radio(rows_doc, "b5_digital")
    d_organiza, _ = _count_radio(rows_doc, "c1_organ")
    d_continua, _ = _count_radio(rows_doc, "d1_continua")
    d_pei, _ = _count_radio(rows_doc, "d2_pei")

    # ---------- IMPACTO ----------
    imp_est = impact_mod.compute_impact(db, "estudiantes")
    imp_doc = impact_mod.compute_impact(db, "docentes")
    imp_est_by_ie = impact_mod.compute_impact_by_ie(db, "estudiantes")
    imp_doc_by_ie = impact_mod.compute_impact_by_ie(db, "docentes")

    DIM_NAME_EST = {"B": "R2 · Emprendimiento", "C": "R3 · Derechos", "D": "Impacto · Proyecto vida", "E": "Enfoque género"}
    DIM_NAME_DOC = {"B": "R1 · Capacidades docentes", "C": "Eficiencia y gestión", "D": "Sostenibilidad e impacto"}

    # ============================================================
    #            ARMADO DE ITEMS (tablas + gráficos)
    # ============================================================
    items = []

    # ---------- BLOQUE 4.1 PERFIL ----------
    # T1 + G1 — IE
    items.append({
        "kind": "section", "title": "4.1 · Perfil de los encuestados",
        "intro": (f"La encuesta se aplicó en {n_iiee} instituciones educativas con un total de {n_est} estudiantes. "
                  f"Edad promedio {edad_avg or '—'} años. "
                  f"A continuación se presenta el perfil sociodemográfico de la muestra."),
    })
    items.append({
        "kind": "table", "num": "T1",
        "title": "Distribución de estudiantes encuestados según institución educativa",
        "headers": ["Institución Educativa", "N°", "%"],
        "rows": [[i["label"], i["n"], f"{i['pct']}"] for i in ie_items],
        "total_row": ["Total general", ie_total, "100.0"],
        "fuente": FUENTE_EST,
        "interp": _interp_top_bottom(ie_items, "concentración geográfica", ie_total),
    })
    items.append({
        "kind": "chart", "num": "G1",
        "title": "Porcentaje de estudiantes encuestados según institución educativa",
        "chart_type": "doughnut",
        "labels": [i["label"] for i in ie_items],
        "data": [i["pct"] for i in ie_items],
        "fuente": FUENTE_EST,
    })
    # T2 + G2 — sexo
    items.append({
        "kind": "table", "num": "T2",
        "title": "Distribución de estudiantes encuestados según sexo",
        "headers": ["Sexo", "N°", "%"],
        "rows": [[i["label"], i["n"], f"{i['pct']}"] for i in sexo_items],
        "fuente": FUENTE_EST,
        "interp": _interp_top_bottom(sexo_items, "composición por sexo", n_est),
    })
    items.append({
        "kind": "chart", "num": "G2",
        "title": "Porcentaje de estudiantes encuestados según sexo",
        "chart_type": "doughnut",
        "labels": [i["label"] for i in sexo_items],
        "data": [i["pct"] for i in sexo_items],
        "fuente": FUENTE_EST,
    })
    # T3 — zona
    items.append({
        "kind": "table", "num": "T3",
        "title": "Distribución por zona de residencia",
        "headers": ["Zona", "N°", "%"],
        "rows": [[i["label"], i["n"], f"{i['pct']}"] for i in zona_items],
        "fuente": FUENTE_EST,
        "interp": _interp_top_bottom(zona_items, "distribución territorial", n_est),
    })
    items.append({
        "kind": "chart", "num": "G3",
        "title": "Distribución por zona de residencia",
        "chart_type": "bar",
        "labels": [i["label"] for i in zona_items],
        "data": [i["pct"] for i in zona_items],
        "fuente": FUENTE_EST,
    })

    # ---------- BLOQUE 4.2 EMPRENDIMIENTO ----------
    items.append({
        "kind": "section", "title": "4.2 · Habilidades de emprendimiento (R2)",
        "intro": ("Bloque B del cuestionario: explora la participación en sesiones de emprendimiento, "
                  "la autopercepción de mejora de habilidades y la formación de equipos productivos."),
    })
    items.append({
        "kind": "table", "num": "T4",
        "title": "Participación de estudiantes en las sesiones de formación en emprendimiento",
        "headers": ["Respuesta", "N°", "%"],
        "rows": [[i["label"], i["n"], f"{i['pct']}"] for i in e_participo],
        "fuente": FUENTE_EST,
        "interp": _interp_si_no(e_participo, "Participación en sesiones de emprendimiento"),
    })
    items.append({
        "kind": "table", "num": "T5",
        "title": "Autopercepción de mejora de habilidades para idear un emprendimiento (Likert 1-5)",
        "headers": ["Nivel", "N°", "%"],
        "rows": [[i["label"], i["n"], f"{i['pct']}"] for i in e_habilidad],
        "fuente": FUENTE_EST,
        "interp": _interp_likert(e_habilidad, n_est, prom_hab, "Habilidades de emprendimiento"),
        "extra": f"Promedio Likert: {prom_hab}/5",
    })
    items.append({
        "kind": "chart", "num": "G4",
        "title": "Autopercepción de habilidades de emprendimiento (Likert 1-5)",
        "chart_type": "bar",
        "labels": [i["label"] for i in e_habilidad],
        "data": [i["pct"] for i in e_habilidad],
        "fuente": FUENTE_EST,
    })
    items.append({
        "kind": "table", "num": "T6",
        "title": "Conocimiento sobre ventajas e inconvenientes de crear una empresa",
        "headers": ["Nivel", "N°", "%"],
        "rows": [[i["label"], i["n"], f"{i['pct']}"] for i in e_conoce],
        "fuente": FUENTE_EST,
        "interp": _interp_top_bottom(e_conoce, "claridad sobre el emprendimiento", n_est),
    })
    items.append({
        "kind": "table", "num": "T7",
        "title": "Participación en equipos de emprendimiento escolar",
        "headers": ["Respuesta", "N°", "%"],
        "rows": [[i["label"], i["n"], f"{i['pct']}"] for i in e_equipo],
        "fuente": FUENTE_EST,
        "interp": _interp_si_no(e_equipo, "Participación en un equipo de emprendimiento"),
    })
    items.append({
        "kind": "table", "num": "T8",
        "title": "Estado actual del emprendimiento escolar",
        "headers": ["Estado", "N°", "%"],
        "rows": [[i["label"], i["n"], f"{i['pct']}"] for i in e_activo],
        "fuente": FUENTE_EST,
        "interp": _interp_top_bottom(e_activo, "sostenibilidad de los emprendimientos", n_est),
    })

    # ---------- BLOQUE 4.3 DERECHOS Y GÉNERO ----------
    items.append({
        "kind": "section", "title": "4.3 · Derechos económicos y sociales · Enfoque de género (R3 + transversal)",
        "intro": ("Bloque C y E del cuestionario: explora el conocimiento sobre derechos, "
                  "la consulta a servicios de orientación y la percepción de equidad de género en la participación."),
    })
    items.append({
        "kind": "table", "num": "T9",
        "title": "Consultas realizadas en el gabinete de orientación de la IE",
        "headers": ["Respuesta", "N°", "%"],
        "rows": [[i["label"], i["n"], f"{i['pct']}"] for i in e_consulta],
        "fuente": FUENTE_EST,
        "interp": _interp_si_no(e_consulta, "Consultas sobre empleo/autoempleo"),
    })
    items.append({
        "kind": "table", "num": "T10",
        "title": "Autopercepción de conocimientos sobre derechos laborales (Likert 1-5)",
        "headers": ["Nivel", "N°", "%"],
        "rows": [[i["label"], i["n"], f"{i['pct']}"] for i in e_conoc_der],
        "fuente": FUENTE_EST,
        "interp": _interp_likert(e_conoc_der, n_est, prom_conoc, "Conocimiento de derechos laborales"),
        "extra": f"Promedio Likert: {prom_conoc}/5",
    })
    items.append({
        "kind": "table", "num": "T11",
        "title": "Percepción de equidad de género en la participación",
        "headers": ["Respuesta", "N°", "%"],
        "rows": [[i["label"], i["n"], f"{i['pct']}"] for i in e_equidad],
        "fuente": FUENTE_EST,
        "interp": _interp_equidad(rows_est, eq_por_sexo),
    })
    if eq_por_sexo:
        items.append({
            "kind": "table", "num": "T12",
            "title": "Percepción de equidad de género desagregada por sexo del respondiente",
            "headers": ["Sexo", "Sí hay equidad", "En parte", "No hay equidad", "N"],
            "rows": [[sx, f"{v['si']}%", f"{v['parte']}%", f"{v['no']}%", v["n"]] for sx, v in eq_por_sexo.items()],
            "fuente": FUENTE_EST,
            "interp": ("La desagregación por sexo permite detectar brechas de percepción. "
                       "Cuando las mujeres reportan ausencia de equidad en mayor proporción que los hombres, "
                       "se confirma la presencia de un sesgo en la experiencia del proyecto que conviene corregir mediante medidas específicas."),
        })
        items.append({
            "kind": "chart", "num": "G5",
            "title": "Comparación de la percepción de equidad de género según sexo",
            "chart_type": "stacked_bar",
            "labels": list(eq_por_sexo.keys()),
            "datasets": [
                {"label": "Sí hay equidad", "data": [v["si"] for v in eq_por_sexo.values()]},
                {"label": "En parte",       "data": [v["parte"] for v in eq_por_sexo.values()]},
                {"label": "No hay equidad", "data": [v["no"] for v in eq_por_sexo.values()]},
            ],
            "fuente": FUENTE_EST,
        })

    # ---------- BLOQUE 4.4 PROYECTO DE VIDA ----------
    items.append({
        "kind": "section", "title": "4.4 · Impacto en proyecto de vida",
        "intro": ("Bloque D del cuestionario: mide cambios en la visión del futuro, "
                  "la claridad del proyecto de vida y la inserción autoempleada."),
    })
    items.append({
        "kind": "table", "num": "T13",
        "title": "Cambio percibido en la visión del futuro laboral atribuible al proyecto",
        "headers": ["Nivel de cambio", "N°", "%"],
        "rows": [[i["label"], i["n"], f"{i['pct']}"] for i in e_futuro],
        "fuente": FUENTE_EST,
        "interp": _interp_top_bottom(e_futuro, "intensidad del impacto en la visión del futuro", n_est),
    })
    items.append({
        "kind": "chart", "num": "G6",
        "title": "Cambio en la visión del futuro laboral",
        "chart_type": "bar",
        "labels": [i["label"] for i in e_futuro],
        "data": [i["pct"] for i in e_futuro],
        "fuente": FUENTE_EST,
    })
    items.append({
        "kind": "table", "num": "T14",
        "title": "Estudiantes que declaran un proyecto de vida con metas claras",
        "headers": ["Respuesta", "N°", "%"],
        "rows": [[i["label"], i["n"], f"{i['pct']}"] for i in e_metas],
        "fuente": FUENTE_EST,
        "interp": _interp_top_bottom(e_metas, "definición de un proyecto de vida", n_est),
    })
    items.append({
        "kind": "table", "num": "T15",
        "title": "Inserción en autoempleo o desarrollo de iniciativa productiva",
        "headers": ["Respuesta", "N°", "%"],
        "rows": [[i["label"], i["n"], f"{i['pct']}"] for i in e_autoempleo],
        "fuente": FUENTE_EST,
        "interp": _interp_si_no(e_autoempleo, "Autoempleo / iniciativa productiva"),
    })

    # ---------- BLOQUE 4.5 DOCENTES ----------
    if n_doc:
        items.append({
            "kind": "section", "title": "4.5 · Capacidades docentes (R1) y sostenibilidad",
            "intro": (f"Encuesta aplicada a {n_doc} docentes capacitados/as. "
                      "Bloque B y D: completitud de cursos, utilidad pedagógica y sostenibilidad."),
        })
        items.append({
            "kind": "table", "num": "T16",
            "title": "Docentes que completaron los dos cursos de formación híbrida",
            "headers": ["Respuesta", "N°", "%"],
            "rows": [[i["label"], i["n"], f"{i['pct']}"] for i in d_cursos],
            "fuente": FUENTE_DOC,
            "interp": _interp_si_no(d_cursos, "Cursos completados"),
        })
        items.append({
            "kind": "table", "num": "T17",
            "title": "Utilidad pedagógica autopercibida de la formación recibida (Likert 1-5)",
            "headers": ["Nivel", "N°", "%"],
            "rows": [[i["label"], i["n"], f"{i['pct']}"] for i in d_util],
            "fuente": FUENTE_DOC,
            "interp": _interp_likert(d_util, n_doc, prom_util, "Utilidad pedagógica"),
            "extra": f"Promedio Likert: {prom_util}/5",
        })
        items.append({
            "kind": "chart", "num": "G7",
            "title": "Utilidad pedagógica de la formación recibida",
            "chart_type": "bar",
            "labels": [i["label"] for i in d_util],
            "data": [i["pct"] for i in d_util],
            "fuente": FUENTE_DOC,
        })
        items.append({
            "kind": "table", "num": "T18",
            "title": "Aplicación en aula de metodologías activas de emprendimiento",
            "headers": ["Frecuencia", "N°", "%"],
            "rows": [[i["label"], i["n"], f"{i['pct']}"] for i in d_aplica],
            "fuente": FUENTE_DOC,
            "interp": _interp_top_bottom(d_aplica, "aplicación pedagógica efectiva", n_doc),
        })
        items.append({
            "kind": "table", "num": "T19",
            "title": "IIEE con protocolo de integración curricular de emprendimiento",
            "headers": ["Respuesta", "N°", "%"],
            "rows": [[i["label"], i["n"], f"{i['pct']}"] for i in d_protocolo],
            "fuente": FUENTE_DOC,
            "interp": _interp_si_no(d_protocolo, "Protocolo en la IE"),
        })
        items.append({
            "kind": "table", "num": "T20",
            "title": "Incorporación del emprendimiento al PEI / programación curricular",
            "headers": ["Estado", "N°", "%"],
            "rows": [[i["label"], i["n"], f"{i['pct']}"] for i in d_pei],
            "fuente": FUENTE_DOC,
            "interp": _interp_top_bottom(d_pei, "institucionalización del enfoque", n_doc),
        })

    # ---------- BLOQUE 4.6 IMPACTO Y COMPARATIVO POR IE ----------
    items.append({
        "kind": "section", "title": "4.6 · Nivel de impacto: score global y comparativos por IE",
        "intro": ("Esta sección sintetiza el nivel de impacto en una escala 0-100, calculada desde la percepción de cada respondiente y agregada por dimensión e institución educativa. "
                  "Permite identificar las IIEE con mayor y menor avance, y orientar acciones de refuerzo focalizadas."),
    })

    # Tabla 21 — impacto global y por dimensión (estudiantes)
    if imp_est.get("dimensions"):
        items.append({
            "kind": "table", "num": "T21",
            "title": "Score de impacto por dimensión – Anexo 1 Estudiantes",
            "headers": ["Dimensión", "Score (0-100)", "Nivel", "N° valoraciones"],
            "rows": [[d["title"], d["score"] or "—", d["level"], d["n_answers"]] for d in imp_est["dimensions"]],
            "total_row": ["GLOBAL ESTUDIANTES", imp_est["global"] or "—", imp_est["global_level"], imp_est["n"]],
            "fuente": FUENTE_EST,
            "interp": (f"El impacto global en estudiantes es {imp_est['global']}/100 (nivel «{imp_est['global_level'].lower()}»). "
                       f"La dimensión más fuerte y la más débil orientan dónde sostener y dónde reforzar la intervención. "
                       f"Una diferencia mayor a 15 puntos entre dimensiones sugiere desigualdad en los componentes."),
        })
    # Tabla 22 — impacto por IE x dimensión (cross-tab)
    if imp_est_by_ie["ies"]:
        headers = ["Institución educativa", "N", "Global"] + [DIM_NAME_EST.get(L, L) for L in imp_est_by_ie["dim_keys"]]
        rows = []
        for r in imp_est_by_ie["ies"]:
            row = [r["ie"], r["n"], r["global"]] + [r.get(L, "—") for L in imp_est_by_ie["dim_keys"]]
            rows.append(row)
        items.append({
            "kind": "table", "num": "T22",
            "title": "Score de impacto comparado por institución educativa y dimensión (estudiantes)",
            "headers": headers,
            "rows": rows,
            "fuente": FUENTE_EST,
            "interp": _interp_impact_by_ie(imp_est_by_ie),
        })
        items.append({
            "kind": "chart", "num": "G8",
            "title": "Score global de impacto por institución educativa (estudiantes)",
            "chart_type": "horizontal_bar",
            "labels": [r["ie"] for r in imp_est_by_ie["ies"]],
            "data": [r["global"] for r in imp_est_by_ie["ies"]],
            "fuente": FUENTE_EST,
        })

    # Tabla 23 — docentes
    if imp_doc.get("dimensions"):
        items.append({
            "kind": "table", "num": "T23",
            "title": "Score de impacto por dimensión – Anexo 2 Docentes",
            "headers": ["Dimensión", "Score (0-100)", "Nivel", "N° valoraciones"],
            "rows": [[d["title"], d["score"] or "—", d["level"], d["n_answers"]] for d in imp_doc["dimensions"]],
            "total_row": ["GLOBAL DOCENTES", imp_doc["global"] or "—", imp_doc["global_level"], imp_doc["n"]],
            "fuente": FUENTE_DOC,
            "interp": (f"El impacto global desde los docentes es {imp_doc['global']}/100 (nivel «{imp_doc['global_level'].lower()}»). "
                       f"Las dimensiones con score más bajo son señales para reforzar acompañamiento técnico."),
        })
    if imp_doc_by_ie["ies"]:
        headers = ["Institución educativa", "N", "Global"] + [DIM_NAME_DOC.get(L, L) for L in imp_doc_by_ie["dim_keys"]]
        rows = []
        for r in imp_doc_by_ie["ies"]:
            row = [r["ie"], r["n"], r["global"]] + [r.get(L, "—") for L in imp_doc_by_ie["dim_keys"]]
            rows.append(row)
        items.append({
            "kind": "table", "num": "T24",
            "title": "Score de impacto comparado por institución educativa y dimensión (docentes)",
            "headers": headers,
            "rows": rows,
            "fuente": FUENTE_DOC,
            "interp": _interp_impact_by_ie(imp_doc_by_ie),
        })

    # ============================================================
    #                    CONCLUSIONES
    # ============================================================
    conclusiones = []
    if n_est:
        conclusiones.append({"titulo": "Cobertura muestral",
            "texto": f"Se procesaron {n_est} respuestas de estudiantes y {n_doc} de docentes en {n_iiee} IIEE del proyecto. Período: {fecha_min} – {fecha_max}."})
    if prom_hab:
        conclusiones.append({"titulo": "Habilidades de emprendimiento (R2)",
            "texto": f"Promedio Likert {prom_hab}/5. {_pct(rows_est, 'b1_participo', {'Sí'})}% participó en sesiones; {_pct(rows_est, 'b4_equipo', {'Sí'})}% formó equipo; {_pct(rows_est, 'b5_activo', {'Sí'})}% mantiene su iniciativa activa."})
    if e_equidad:
        conclusiones.append({"titulo": "Equidad de género",
            "texto": _interp_equidad(rows_est, eq_por_sexo)})
    if e_futuro:
        conclusiones.append({"titulo": "Proyecto de vida",
            "texto": f"{_pct(rows_est, 'd1_futuro', {'Mucho','Algo'})}% afirma que el proyecto cambió su visión del futuro. {_pct(rows_est, 'd2_metas', {'Sí'})}% tiene metas claras; {_pct(rows_est, 'd3_autoempleo', {'Sí'})}% reporta autoempleo."})
    if n_doc:
        conclusiones.append({"titulo": "Capacidades docentes (R1)",
            "texto": f"{_pct(rows_doc, 'b1_cursos', {'Sí'})}% completó los cursos (Likert utilidad: {prom_util}/5). {_pct(rows_doc, 'b3_aplica', {'Siempre','A veces'})}% aplica metodologías activas; {_pct(rows_doc, 'b4_protocolo', {'Sí'})}% cuenta con protocolo en su IE."})
    if imp_est.get("global"):
        conclusiones.append({"titulo": "Score global de impacto",
            "texto": f"Estudiantes: {imp_est['global']}/100 ({imp_est['global_level'].lower()}). Docentes: {imp_doc.get('global','—')}/100 ({imp_doc.get('global_level','—').lower()})."})
    if imp_est_by_ie["ies"]:
        top = imp_est_by_ie["ies"][0]; bot = imp_est_by_ie["ies"][-1]
        conclusiones.append({"titulo": "Heterogeneidad entre IIEE",
            "texto": f"Mayor score: {top['ie']} ({top['global']}); menor score: {bot['ie']} ({bot['global']}). Diferencia: {round(top['global']-bot['global'],1)} puntos."})

    # ============================================================
    #                    RECOMENDACIONES
    # ============================================================
    recs = []
    for d in imp_est.get("dimensions", []):
        if d.get("score") is not None and d["score"] < 70:
            recs.append(f"Reforzar la dimensión «{d['title']}» (score actual {d['score']}/100): diseñar talleres específicos y acompañamiento personalizado.")
    pct_no_eq = _pct(rows_est, "e1_igual", {"No"})
    if pct_no_eq >= 15:
        recs.append(f"Profundizar el trabajo en equidad de género: el {pct_no_eq}% de estudiantes percibe ausencia de equidad, brecha que debe abordarse con sesiones diferenciadas.")
    pct_activo = _pct(rows_est, "b5_activo", {"Sí"})
    if pct_activo < 35 and n_est >= 10:
        recs.append(f"Sólo el {pct_activo}% mantiene su emprendimiento activo: asesoría técnica continuada y vinculación con redes locales (municipalidad, COPALE).")
    if imp_est_by_ie["ies"] and len(imp_est_by_ie["ies"]) >= 2:
        bottom_ies = [r["ie"] for r in imp_est_by_ie["ies"] if r["global"] < 65]
        if bottom_ies:
            recs.append(f"Focalizar acompañamiento en las IIEE con menor score (<65): {', '.join(bottom_ies)}.")
    if n_doc and _pct(rows_doc, "b1_cursos", {"Sí"}) < 85:
        recs.append("Completar la formación docente pendiente con sesiones asincrónicas de refuerzo.")
    if n_doc and _pct(rows_doc, "b4_protocolo", {"Sí"}) < 70:
        recs.append("Impulsar formalización del enfoque de emprendimiento en los PEI de las IIEE participantes.")
    recs.extend([
        "Sostener un sistema de monitoreo activo durante todo el ciclo, recogiendo voces cualitativas en cada IE.",
        "Articular los resultados con la UGEL Cutervo y la Mesa de Concertación para escalar buenas prácticas.",
        "Vincular los emprendimientos con problemáticas locales (agua, alimentación, ambiente) para reforzar pertinencia.",
    ])

    return {
        "n_est": n_est, "n_doc": n_doc, "n_iiee": n_iiee,
        "fecha_min": fecha_min, "fecha_max": fecha_max,
        "generated_at": datetime.utcnow().strftime("%d/%m/%Y %H:%M"),
        "items": items,
        "conclusiones": conclusiones,
        "recomendaciones": recs,
    }
