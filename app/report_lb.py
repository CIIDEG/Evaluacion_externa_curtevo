"""Generador del Informe Línea de Base / Final automatizado.

Replica la estructura del informe del IPP:
I. Datos generales · II. Objetivo · III. Metodología · IV. Resultados
(4.1 Perfil · 4.2 Contexto · 4.3 Emprendimiento · 4.4 Derechos y género · 5. Proyecto de vida)
VI. Conclusiones (auto) · VII. Recomendaciones (auto, condicionales)
"""
from collections import Counter
from datetime import datetime
from statistics import mean
from sqlalchemy.orm import Session

from . import models
from .surveys_def import get_form
from . import impact as impact_mod


def _count_by_data_field(rows, field):
    c = Counter()
    for r in rows:
        v = (r.data or {}).get(field) or "—"
        c[v] += 1
    total = sum(c.values()) or 1
    return [{"label": k, "n": v, "pct": round(100 * v / total, 1)} for k, v in c.most_common()]


def _pct_in(rows, qid, positive_values):
    n = 0; ok = 0
    for r in rows:
        v = (r.data or {}).get(qid)
        if v:
            n += 1
            if v in positive_values:
                ok += 1
    return round(100 * ok / n, 1) if n else 0, n


def _likert_avg(rows, qid):
    vals = []
    for r in rows:
        v = (r.data or {}).get(qid)
        try:
            vv = int(v)
            if 1 <= vv <= 5:
                vals.append(vv)
        except (TypeError, ValueError):
            continue
    return round(mean(vals), 2) if vals else None, len(vals)


def build_report(db: Session) -> dict:
    """Construye el informe completo a partir de los datos de estudiantes y docentes."""
    rows_est = db.query(models.SurveyResponse).filter_by(form_code="estudiantes").all()
    rows_doc = db.query(models.SurveyResponse).filter_by(form_code="docentes").all()

    n_est = len(rows_est)
    n_doc = len(rows_doc)
    fechas = [r.created_at for r in (rows_est + rows_doc) if r.created_at]
    fecha_min = min(fechas).strftime("%B %Y") if fechas else "—"
    fecha_max = max(fechas).strftime("%B %Y") if fechas else "—"

    # I — DATOS GENERALES
    iiee_set = {(r.data or {}).get("institucion") for r in rows_est if (r.data or {}).get("institucion")}
    iiee_set.discard(None)
    n_iiee = len(iiee_set)

    # 4.1 — PERFIL
    perfil_ie = _count_by_data_field(rows_est, "institucion")
    perfil_sexo = _count_by_data_field(rows_est, "sexo")
    perfil_zona = _count_by_data_field(rows_est, "zona")
    perfil_grado = _count_by_data_field(rows_est, "grado")
    # edades
    edades = [r.edad for r in rows_est if r.edad]
    edad_avg = round(mean(edades), 1) if edades else None
    edad_min, edad_max = (min(edades), max(edades)) if edades else (None, None)

    # 4.3 — EMPRENDIMIENTO
    pct_participo, n_p = _pct_in(rows_est, "b1_participo", {"Sí"})
    pct_equipo, _ = _pct_in(rows_est, "b4_equipo", {"Sí"})
    pct_activo, _ = _pct_in(rows_est, "b5_activo", {"Sí"})
    avg_habil, _ = _likert_avg(rows_est, "b2_habilidad")
    pct_conoce_emp = _pct_in(rows_est, "b3_conocer", {"Mucho", "Algo"})[0]

    # 4.4 — DERECHOS Y GÉNERO
    pct_consulta, _ = _pct_in(rows_est, "c2_consulta", {"Sí"})
    avg_conoc_derechos, _ = _likert_avg(rows_est, "c3_conoc")
    pct_equidad_alta = _pct_in(rows_est, "e1_igual", {"Sí"})[0]
    pct_equidad_parcial = _pct_in(rows_est, "e1_igual", {"En parte"})[0]
    pct_equidad_no = _pct_in(rows_est, "e1_igual", {"No"})[0]
    # desagregado por sexo en e1_igual
    eq_por_sexo = {}
    for sx in ("Mujer", "Hombre"):
        sx_rows = [r for r in rows_est if (r.data or {}).get("sexo") == sx]
        if sx_rows:
            eq_por_sexo[sx] = {
                "si":     _pct_in(sx_rows, "e1_igual", {"Sí"})[0],
                "parte":  _pct_in(sx_rows, "e1_igual", {"En parte"})[0],
                "no":     _pct_in(sx_rows, "e1_igual", {"No"})[0],
                "n":      len(sx_rows),
            }

    # 5 — PROYECTO DE VIDA
    pct_futuro_mucho = _pct_in(rows_est, "d1_futuro", {"Mucho", "Algo"})[0]
    pct_metas, _ = _pct_in(rows_est, "d2_metas", {"Sí"})
    pct_autoempleo, _ = _pct_in(rows_est, "d3_autoempleo", {"Sí"})

    # Docentes — síntesis
    pct_curso_completo = _pct_in(rows_doc, "b1_cursos", {"Sí"})[0]
    avg_utilidad, _ = _likert_avg(rows_doc, "b2_util")
    pct_aplica = _pct_in(rows_doc, "b3_aplica", {"Siempre", "A veces"})[0]
    pct_protocolo = _pct_in(rows_doc, "b4_protocolo", {"Sí"})[0]
    pct_pei = _pct_in(rows_doc, "d2_pei", {"Sí", "En proceso"})[0]

    # IMPACT SCORES (los reutilizamos)
    imp_est = impact_mod.compute_impact(db, "estudiantes")
    imp_doc = impact_mod.compute_impact(db, "docentes")

    # ====================== CONCLUSIONES AUTOMÁTICAS ======================
    conclusiones = []

    if n_est:
        conclusiones.append({
            "titulo": "Cobertura muestral alcanzada",
            "texto": (f"Se recogieron {n_est} respuestas de estudiantes en {n_iiee} instituciones educativas "
                      f"del proyecto, junto con {n_doc} respuestas de docentes. Período: {fecha_min} – {fecha_max}."),
        })

    if avg_habil is not None:
        nivel = "alto" if avg_habil >= 4 else "intermedio" if avg_habil >= 3 else "bajo"
        conclusiones.append({
            "titulo": "Habilidades de emprendimiento (R2)",
            "texto": (f"El {pct_participo}% de estudiantes reporta haber participado en sesiones de emprendimiento. "
                      f"La autopercepción promedio de mejora de habilidades es {avg_habil}/5 ({nivel}). "
                      f"El {pct_equipo}% formó parte de un equipo y el {pct_activo}% mantiene un emprendimiento activo."),
        })

    if pct_equidad_alta:
        conclusiones.append({
            "titulo": "Percepción de equidad de género",
            "texto": (f"El {pct_equidad_alta}% de estudiantes percibe que mujeres y hombres tuvieron las mismas "
                      f"oportunidades de participar; un {pct_equidad_parcial}% lo percibe «en parte» y un "
                      f"{pct_equidad_no}% lo niega."
                      + (f" Entre mujeres: {eq_por_sexo.get('Mujer',{}).get('si','—')}% sí · "
                         f"{eq_por_sexo.get('Mujer',{}).get('parte','—')}% en parte · "
                         f"{eq_por_sexo.get('Mujer',{}).get('no','—')}% no." if eq_por_sexo else "")),
        })

    if pct_futuro_mucho:
        conclusiones.append({
            "titulo": "Impacto en proyecto de vida",
            "texto": (f"El {pct_futuro_mucho}% afirma que el proyecto cambió su forma de ver el futuro laboral. "
                      f"El {pct_metas}% tiene un proyecto de vida con metas claras y el {pct_autoempleo}% "
                      f"está desarrollando una iniciativa productiva."),
        })

    if n_doc:
        conclusiones.append({
            "titulo": "Fortalecimiento de capacidades docentes (R1)",
            "texto": (f"El {pct_curso_completo}% de docentes completó los cursos de formación híbrida, "
                      f"con utilidad percibida promedio de {avg_utilidad or '—'}/5. El {pct_aplica}% aplica "
                      f"metodologías activas de emprendimiento en aula y el {pct_protocolo}% de sus IIEE "
                      f"cuenta con protocolo de integración curricular. {pct_pei}% reporta incorporación "
                      f"al PEI / programación de aula (incluye «en proceso»)."),
        })

    if imp_est.get("global") is not None:
        conclusiones.append({
            "titulo": "Score global de impacto (estudiantes)",
            "texto": (f"El nivel de impacto global desde la percepción de estudiantes es "
                      f"{imp_est['global']}/100 (nivel «{imp_est['global_level'].lower()}»). "
                      "Dimensiones: " + ", ".join(
                          [f"{d['title'].split('·')[0].strip()} {d['score']}" for d in imp_est["dimensions"] if d["score"] is not None]
                      ) + "."),
        })
    if imp_doc.get("global") is not None:
        conclusiones.append({
            "titulo": "Score global de impacto (docentes)",
            "texto": (f"El nivel de impacto global desde la percepción docente es "
                      f"{imp_doc['global']}/100 (nivel «{imp_doc['global_level'].lower()}»)."),
        })

    # ====================== RECOMENDACIONES CONDICIONALES ======================
    recomendaciones = []

    # Estudiantes — habilidades
    if imp_est.get("dimensions"):
        for d in imp_est["dimensions"]:
            if d.get("score") is not None and d["score"] < 70:
                recomendaciones.append(
                    f"Reforzar el componente «{d['title']}»: el puntaje actual ({d['score']}/100) "
                    f"está por debajo del umbral recomendado (70). Considerar talleres adicionales o "
                    f"acompañamiento personalizado."
                )
    # Género
    if pct_equidad_no >= 15:
        recomendaciones.append(
            f"Profundizar el trabajo en equidad de género: el {pct_equidad_no}% del estudiantado percibe que "
            f"no hubo igualdad de oportunidades. Diseñar sesiones específicas y revisar dinámicas en aula."
        )
    # Emprendimiento activo
    if pct_activo < 35 and n_est >= 10:
        recomendaciones.append(
            f"Sólo el {pct_activo}% mantiene su emprendimiento activo: brindar asesoría técnica, "
            f"conectar con redes locales (municipalidad, COPALE) y crear espacios de seguimiento posterior."
        )
    # Autoempleo
    if pct_autoempleo < 30 and n_est >= 10:
        recomendaciones.append(
            f"El {pct_autoempleo}% reporta autoempleo: ampliar enlaces con orientación vocacional y "
            f"alianzas con instituciones locales de empleo y emprendimiento."
        )
    # Docentes
    if pct_curso_completo and pct_curso_completo < 85:
        recomendaciones.append(
            f"Completar la formación docente: aún hay un {round(100 - pct_curso_completo,1)}% de docentes "
            f"sin completar los cursos. Programar refuerzos asincrónicos."
        )
    if pct_protocolo and pct_protocolo < 70:
        recomendaciones.append(
            f"Impulsar la formalización del enfoque de emprendimiento en los PEI de las IIEE: solo el "
            f"{pct_protocolo}% cuenta con protocolo."
        )

    # Recomendaciones siempre incluidas (transversales)
    recomendaciones.extend([
        "Mantener el sistema de monitoreo activo durante todo el ciclo, recogiendo voces cualitativas (KII, FGD, MSC) en cada IE.",
        "Vincular los emprendimientos escolares con problemáticas locales (agua, alimentación, ambiente) para reforzar pertinencia.",
        "Articular los resultados con la UGEL Cutervo y la Mesa de Concertación para escalar buenas prácticas.",
    ])

    return {
        "n_est": n_est,
        "n_doc": n_doc,
        "n_iiee": n_iiee,
        "fecha_min": fecha_min,
        "fecha_max": fecha_max,
        "generated_at": datetime.utcnow().strftime("%d/%m/%Y %H:%M"),
        # Perfil
        "perfil_ie": perfil_ie,
        "perfil_sexo": perfil_sexo,
        "perfil_zona": perfil_zona,
        "perfil_grado": perfil_grado,
        "edad_avg": edad_avg, "edad_min": edad_min, "edad_max": edad_max,
        # Emprendimiento
        "pct_participo": pct_participo,
        "pct_equipo": pct_equipo,
        "pct_activo": pct_activo,
        "avg_habil": avg_habil,
        "pct_conoce_emp": pct_conoce_emp,
        # Derechos
        "pct_consulta": pct_consulta,
        "avg_conoc_derechos": avg_conoc_derechos,
        "pct_equidad_alta": pct_equidad_alta,
        "pct_equidad_parcial": pct_equidad_parcial,
        "pct_equidad_no": pct_equidad_no,
        "eq_por_sexo": eq_por_sexo,
        # Proyecto de vida
        "pct_futuro_mucho": pct_futuro_mucho,
        "pct_metas": pct_metas,
        "pct_autoempleo": pct_autoempleo,
        # Docentes
        "pct_curso_completo": pct_curso_completo,
        "avg_utilidad": avg_utilidad,
        "pct_aplica": pct_aplica,
        "pct_protocolo": pct_protocolo,
        "pct_pei": pct_pei,
        # Impact
        "imp_est": imp_est,
        "imp_doc": imp_doc,
        # Auto-generadas
        "conclusiones": conclusiones,
        "recomendaciones": recomendaciones,
    }
