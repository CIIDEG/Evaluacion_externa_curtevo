"""Sembrador de datos de muestra (~20% de las metas) para validar reportes.

Uso (dentro del contenedor cutervo-app):
    docker exec cutervo-app python /code/seed_demo.py

O directamente:
    docker exec -it cutervo-app python /code/seed_demo.py
"""
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Asegurar que el paquete app sea importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database import SessionLocal, Base, engine
from app import models
from app.surveys_def import ALL_FORMS, get_form, all_question_ids, INSTITUCIONES

Base.metadata.create_all(bind=engine)

# Metas y porcentaje
METAS = {"estudiantes":196,"docentes":24,"kii":18,"fgd_jovenes":3,"fgd_docentes":3,"observacion":12,"msc":12}
PCT = 0.20

random.seed(42)

# Sets de respuestas verosímiles (sesgo positivo moderado, con minoría crítica)
def weighted(opts, weights):
    return random.choices(opts, weights=weights, k=1)[0]

def pick(opts):
    return random.choice(opts)

REL_ESTUDIANTE = [
    "Aprendí a planificar un emprendimiento desde cero. Antes no sabía cómo organizar mis ideas.",
    "Empecé a vender pollos beneficiados con mis hermanas. Hoy tenemos clientes fijos en el mercado de Cutervo.",
    "Mi cambio más significativo fue perder el miedo a hablar en público. Ahora lidero el municipio escolar.",
    "Con la formación del proyecto pude poner un pequeño negocio de impresiones cerca de la IE.",
    "Aprendí mis derechos laborales. Cuando trabajé en chacra los fines de semana ya supe qué cosas reclamar.",
    "Antes pensaba que sólo podía ser jornalero. Hoy estoy ahorrando para abrir un puesto en la feria dominical.",
    "Lo que más rescato es haber trabajado con compañeras y compañeros en equipo, respetándonos.",
]

REL_DOCENTE = [
    "Mis estudiantes ahora exponen sus proyectos de emprendimiento con seguridad. Hay un cambio actitudinal claro.",
    "He incorporado la metodología activa a mi sesión semanal de Educación para el Trabajo.",
    "Los chicos del 5° han presentado sus planes de negocio en la feria provincial.",
    "Necesitamos más capacitación en gestión digital para sostener lo aprendido.",
]

EMPREND_NOMBRES = [
    "Venta de pollos beneficiados", "Producción de quesos artesanales",
    "Imprenta escolar y tarjetas", "Cultivo y comercio de palta",
    "Crianza de cuyes para venta", "Talleres de tejido en lana",
    "Reparación de celulares", "Repostería tradicional cutervina",
    "Compostaje y biohuerto", "Comercialización de café orgánico",
]

CITAS_KII = {
    "p1_pertinencia": [
        "El proyecto respondió a una necesidad real: nuestros jóvenes terminaban la secundaria sin proyecto de vida.",
        "Era pertinente, sí, pero llegó tarde en el calendario escolar. Habría rendido más empezando en marzo.",
    ],
    "p2_coherencia": [
        "Se articuló con el PEI de cada IE y con la propuesta curricular de la UGEL Cutervo.",
    ],
    "p3_eficiencia": [
        "La coordinación IS-IPP fue muy fluida. Los desembolsos llegaron a tiempo.",
        "Tuvimos retrasos al inicio por la transferencia internacional, pero después todo fluyó.",
    ],
    "p4_eficacia": [
        "Logramos formar a los 24 docentes; el 80% aplica la metodología en aula.",
    ],
    "p5_impacto": [
        "El impacto más significativo es la convicción de las jóvenes en sus propias capacidades.",
        "Tres egresadas montaron un negocio de quesos artesanales tras la feria.",
    ],
    "p6_sostenibilidad": [
        "La red de docentes (CAD) quedará activa y eso garantiza continuidad.",
    ],
    "p7_lecciones": [
        "Hay que involucrar antes a las familias. Algunas resistieron al inicio por desconocimiento.",
    ],
}

CITAS_FGD = {
    "q1_aprendizajes": [
        "Lo más valioso fue aprender a trabajar en equipo y a presentar nuestras ideas sin vergüenza.",
        "Yo cambiaría el horario, fue muy ajustado con las clases.",
    ],
    "q2_metodologia": [
        "La metodología 'joven a joven' fue clave. Aprendimos más entre pares que con clases teóricas.",
    ],
    "q3_genero": [
        "Sí, nos respetaron como mujeres. Pero al inicio algunos chicos no querían que lideráramos.",
        "Las chicas terminaron presentando los mejores proyectos.",
    ],
    "q4_emprendimientos": [
        "Nuestro emprendimiento de cuyes sigue activo. Vendemos a tres comedores populares.",
    ],
    "q5_huella": [
        "Pediríamos que la formación llegue a 3° y 4° de secundaria, no sólo a egresados.",
    ],
}

CITAS_MSC = [
    "Antes del proyecto era tímido y me daba miedo el futuro. Ahora sé que puedo emprender en mi comunidad y ya tengo metas claras a 3 años.",
    "Yo creía que mi destino era irme a Lima. Hoy estoy trabajando en el negocio de café orgánico de mi familia y aporto desde aquí.",
    "El cambio más significativo fue ver a mi hija liderando el equipo. Eso transformó toda nuestra forma de verla.",
    "Aprendí que mis derechos importan. Cuando trabajé en una tienda este verano supe pedir un acuerdo escrito.",
]

def date_recent(days_ago_max=60):
    delta = random.randint(0, days_ago_max)
    return datetime.utcnow() - timedelta(days=delta, hours=random.randint(0,23), minutes=random.randint(0,59))


def seed_estudiantes(db, n):
    inserted = 0
    for _ in range(n):
        # excluir la opción "Otra" del sample, para mantener limpieza
        ie = random.choice(INSTITUCIONES[:-1])
        sexo = weighted(["Mujer","Hombre","Prefiero no decir"], [0.52, 0.46, 0.02])
        data = {
            "institucion": ie, "institucion_otra": "",
            "sexo": sexo,
            "edad": str(random.randint(15, 18)),
            "grado": weighted(["5° secundaria","Egresado/a"], [0.6, 0.4]),
            "zona": weighted(["Urbana","Periurbana","Rural"], [0.35, 0.25, 0.40]),
            "b1_participo": weighted(["Sí","No"], [0.88, 0.12]),
            "b2_habilidad": str(weighted([1,2,3,4,5],[0.02,0.05,0.18,0.40,0.35])),
            "b3_conocer": weighted(["Mucho","Algo","Poco","Nada"], [0.30,0.45,0.18,0.07]),
            "b4_equipo": weighted(["Sí","No"], [0.72, 0.28]),
            "b5_activo": weighted(["Sí","No","No aplica"], [0.42, 0.30, 0.28]),
            "c1_derechos": pick([
                "Derecho a la educación, al trabajo digno y a la igualdad.",
                "Educación, salud, libertad de expresión.",
                "Trabajo, salud, vivienda.",
                "Igualdad, no discriminación y derecho al desarrollo.",
            ]),
            "c2_consulta": weighted(["Sí","No"], [0.55, 0.45]),
            "c3_conoc": str(weighted([1,2,3,4,5], [0.03,0.10,0.30,0.40,0.17])),
            "d1_futuro": weighted(["Mucho","Algo","Poco","Nada"], [0.45,0.35,0.15,0.05]),
            "d2_metas": weighted(["Sí","En parte","No"], [0.50,0.40,0.10]),
            "d3_autoempleo": weighted(["Sí","No"], [0.32, 0.68]),
            "d4_relato": pick(REL_ESTUDIANTE) if random.random() < 0.65 else "",
            "e1_igual": weighted(["Sí","En parte","No"], [0.55,0.35,0.10]),
            "e2_dif": pick([
                "Algunos compañeros se reían cuando lideraba. Pero seguí adelante.",
                "Mi familia no quería que viajara a las sesiones. Logré convencerla.",
                "",
                "No, todos pudimos participar.",
                "",
            ]),
        }
        edad_int = int(data["edad"]) if data["edad"].isdigit() else None
        r = models.SurveyResponse(
            form_code="estudiantes", institucion=ie, sexo=sexo, edad=edad_int,
            data=data, ip="10.0.0.%d" % random.randint(2,250),
            created_at=date_recent(45),
        )
        db.add(r); inserted += 1
    db.commit(); return inserted


def seed_docentes(db, n):
    inserted = 0
    for _ in range(n):
        ie = random.choice(INSTITUCIONES[:-1])
        sexo = weighted(["Mujer","Hombre","Prefiero no decir"], [0.55, 0.43, 0.02])
        data = {
            "institucion": ie, "institucion_otra": "",
            "sexo": sexo,
            "anios": str(random.randint(3, 28)),
            "area": pick(["Educación para el Trabajo","Comunicación","Matemática","Ciencias Sociales","CTA","Inglés"]),
            "b1_cursos": weighted(["Sí","No"], [0.92, 0.08]),
            "b2_util": str(weighted([1,2,3,4,5], [0.0,0.04,0.10,0.40,0.46])),
            "b3_aplica": weighted(["Siempre","A veces","Nunca"], [0.45,0.50,0.05]),
            "b4_protocolo": weighted(["Sí","No"], [0.68, 0.32]),
            "b5_digital": weighted(["Sí","En parte","No"], [0.50,0.40,0.10]),
            "c1_organ": weighted(["Sí","En parte","No"], [0.65,0.30,0.05]),
            "c2_facilita": weighted(["Sí","En parte","No"], [0.55,0.35,0.10]),
            "d1_continua": weighted(["Sí","Probablemente","No"], [0.62,0.32,0.06]),
            "d2_pei": weighted(["Sí","En proceso","No"], [0.40,0.45,0.15]),
            "d3_cambios": pick(REL_DOCENTE),
        }
        edad_int = 20 + int(data["anios"])
        r = models.SurveyResponse(
            form_code="docentes", institucion=ie, sexo=sexo, edad=edad_int,
            data=data, ip="10.0.0.%d" % random.randint(2,250),
            created_at=date_recent(45),
        )
        db.add(r); inserted += 1
    db.commit(); return inserted


def seed_kii(db, n):
    nombres = ["L.D.","M.A.","J.C.","V.R.","R.S.","P.O.","E.G.","C.M."]
    cargos = ["Director IE","Coordinador IPP","Especialista UGEL","Líder docente CAD","Representante IS"]
    inserted = 0
    for i in range(n):
        ie = random.choice(INSTITUCIONES[:-1])
        sexo = weighted(["Mujer","Hombre"], [0.45, 0.55])
        data = {
            "entrevistado": pick(nombres),
            "cargo": pick(cargos),
            "institucion": ie, "institucion_otra": "",
            "sexo": sexo,
            "fecha": date_recent(30).strftime("%Y-%m-%d"),
            "lugar": pick(["Sala de docentes IE Fe y Alegría","Oficina IPP Cutervo","UGEL Cutervo","Sede de la red CAD"]),
            "consentimiento": "Sí",
        }
        for qid in CITAS_KII:
            data[qid] = pick(CITAS_KII[qid])
        data["notas"] = pick([
            "Entrevistado se mostró muy reflexivo. Se extendió en la pregunta de impacto.",
            "Tensión cuando se preguntó por gestión. Mostró frustración con tiempos.",
            "Muy positivo. Lenguaje no verbal asertivo.",
        ])
        r = models.SurveyResponse(
            form_code="kii", institucion=ie, sexo=sexo, edad=None,
            data=data, ip="10.0.0.%d" % random.randint(2,250),
            created_at=date_recent(30),
        )
        db.add(r); inserted += 1
    db.commit(); return inserted


def seed_fgd(db, code, n):
    inserted = 0
    for _ in range(n):
        ie = random.choice(INSTITUCIONES[:-1])
        n_part = random.randint(6, 10)
        n_muj = random.randint(3, n_part-2)
        data = {
            "institucion": ie, "institucion_otra": "",
            "fecha": date_recent(30).strftime("%Y-%m-%d"),
            "n_part": str(n_part),
            "n_mujeres": str(n_muj),
            "facilitador": "Dr. Segundo S. Pérez Pérez",
            "consentimiento": "Sí",
            "apertura": "Apertura con dinámica de presentación. Acuerdos de confidencialidad firmados.",
            "notas": pick([
                "Grupo dinámico, participación alta. Algunas resistencias iniciales superadas.",
                "Buen clima. Mujeres jóvenes lideraron varias intervenciones.",
            ]),
        }
        for qid in CITAS_FGD:
            if code == "fgd_docentes" and qid not in ("q1_practica","q2_apoyos","q3_sostenibilidad"):
                continue
            data[qid] = pick(CITAS_FGD[qid])
        # Para fgd_docentes mapear claves específicas
        if code == "fgd_docentes":
            data["q1_practica"] = pick(REL_DOCENTE)
            data["q2_apoyos"] = "La dirección facilitó horarios. UGEL respaldó con disposición."
            data["q3_sostenibilidad"] = "Se requiere acompañamiento técnico al menos un año más."
        r = models.SurveyResponse(
            form_code=code, institucion=ie, sexo=None, edad=None,
            data=data, ip="10.0.0.%d" % random.randint(2,250),
            created_at=date_recent(30),
        )
        db.add(r); inserted += 1
    db.commit(); return inserted


def seed_observacion(db, n):
    inserted = 0
    for _ in range(n):
        ie = random.choice(INSTITUCIONES[:-1])
        data = {
            "institucion": ie, "institucion_otra": "",
            "fecha": date_recent(30).strftime("%Y-%m-%d"),
            "observador": "Dr. Segundo S. Pérez Pérez",
            "hora": pick(["09:00","10:30","14:00","15:30"]),
            "o1_emprend": pick([
                "Se observa un puesto de comercio escolar operativo, con productos lácteos producidos por las y los estudiantes.",
                "Emprendimiento de impresiones funcionando en horario de descanso. Estudiantes atienden en turnos.",
                "Iniciativa de biohuerto incipiente, todavía en preparación del terreno.",
            ]),
            "o1_estado": weighted(["Operativo","Incipiente","Inactivo","No existe"], [0.40,0.40,0.15,0.05]),
            "o2_recursos": "Aula equipada con materiales de la formación: rotafolios, manuales y maqueta de modelo de negocio.",
            "o3_municipio": "Espacio del municipio escolar visible, con asambleas semanales agendadas.",
            "o4_aula": "Programación trimestral incluye unidad de emprendimiento. Productos visibles en pasillo.",
            "o5_dinamicas": pick([
                "Participación equilibrada por género. Las chicas lideran la sesión observada.",
                "Liderazgo compartido. Se nota confianza entre pares.",
            ]),
            "resumen_audio": "Visita de 90 minutos. IE muestra apropiación del enfoque. Recomendación: documentar mejor.",
        }
        r = models.SurveyResponse(
            form_code="observacion", institucion=ie, sexo=None, edad=None,
            data=data, ip="10.0.0.%d" % random.randint(2,250),
            created_at=date_recent(30),
        )
        db.add(r); inserted += 1
    db.commit(); return inserted


def seed_msc(db, n):
    inserted = 0
    for _ in range(n):
        ie = random.choice(INSTITUCIONES[:-1])
        sexo = weighted(["Mujer","Hombre"], [0.55, 0.45])
        data = {
            "narrador": pick(["A.M.","R.C.","E.V.","J.L.","K.S.","D.T."]),
            "sexo": sexo,
            "edad": str(random.randint(16, 20)),
            "institucion": ie, "institucion_otra": "",
            "fecha": date_recent(30).strftime("%Y-%m-%d"),
            "consentimiento": "Sí",
            "r1_antes_despues": pick(CITAS_MSC),
            "r2_cambio": pick(CITAS_MSC),
            "r3_actividad": "La sesión de proyecto de vida y el acompañamiento posterior con docente líder.",
            "r4_familia": "Mi familia ha empezado a involucrarse en el negocio. Es un cambio que va más allá de mí.",
            "r5_aprendizaje": "Que mis sueños son válidos y puedo hacerlos realidad sin migrar.",
            "notas": "Relato emotivo, lenguaje firme. Confianza creciente durante la entrevista.",
        }
        edad_int = int(data["edad"])
        r = models.SurveyResponse(
            form_code="msc", institucion=ie, sexo=sexo, edad=edad_int,
            data=data, ip="10.0.0.%d" % random.randint(2,250),
            created_at=date_recent(30),
        )
        db.add(r); inserted += 1
    db.commit(); return inserted


def main():
    db = SessionLocal()
    try:
        plan = {
            "estudiantes": max(1, int(METAS["estudiantes"] * PCT)),     # 39
            "docentes":    max(1, int(METAS["docentes"] * PCT)),        # 4-5
            "kii":         max(1, int(METAS["kii"] * PCT)),             # 3-4
            "fgd_jovenes": max(1, int(METAS["fgd_jovenes"] * PCT)),     # 1
            "fgd_docentes":max(1, int(METAS["fgd_docentes"] * PCT)),    # 1
            "observacion": max(1, int(METAS["observacion"] * PCT)),     # 2
            "msc":         max(1, int(METAS["msc"] * PCT)),             # 2
        }
        print("=" * 56)
        print("  SEEDING DEMO DATA (~20% de las metas)")
        print("=" * 56)
        for code, n in plan.items():
            print(f"  · {code:14s} → meta {METAS[code]:3d} | a insertar: {n}")
        print("-" * 56)

        total = 0
        total += seed_estudiantes(db, plan["estudiantes"]); print(f"  ✓ estudiantes ({plan['estudiantes']})")
        total += seed_docentes(db, plan["docentes"]);       print(f"  ✓ docentes ({plan['docentes']})")
        total += seed_kii(db, plan["kii"]);                 print(f"  ✓ kii ({plan['kii']})")
        total += seed_fgd(db, "fgd_jovenes", plan["fgd_jovenes"]); print(f"  ✓ fgd_jovenes ({plan['fgd_jovenes']})")
        total += seed_fgd(db, "fgd_docentes", plan["fgd_docentes"]); print(f"  ✓ fgd_docentes ({plan['fgd_docentes']})")
        total += seed_observacion(db, plan["observacion"]); print(f"  ✓ observacion ({plan['observacion']})")
        total += seed_msc(db, plan["msc"]);                 print(f"  ✓ msc ({plan['msc']})")
        print("-" * 56)
        print(f"  TOTAL insertado: {total} registros")
        print("=" * 56)
        print("\n  ▶ Revisa la página de resultados ahora:")
        print("     https://evafinal.metacalidad.cloud/resultados\n")
    finally:
        db.close()


if __name__ == "__main__":
    main()
