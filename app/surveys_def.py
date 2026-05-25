"""Definición de las encuestas. Edita aquí para cambiar preguntas."""

INSTITUCIONES = [
    "IE Toribio Casanova",
    "IE Andrés Avelino Cáceres",
    "IE Juan Pablo II",
    "IE Cristo Rey",
    "IE Inmaculada Concepción",
    "IE San Juan",
    "IE Santo Tomás",
    "IE Mariscal Castilla",
    "IE Nuestra Señora del Carmen",
    "IE Antonio Raimondi",
    "IE José Carlos Mariátegui",
    "IE José Olaya",
]


ENCUESTA_ESTUDIANTES = {
    "code": "estudiantes",
    "title": "Cuestionario a estudiantes — Evaluación Final",
    "intro": (
        "Tu opinión es muy importante para evaluar el proyecto. "
        "Esta encuesta es anónima y dura unos 20 minutos. "
        "No hay respuestas correctas o incorrectas."
    ),
    "sections": [
        {
            "title": "A. Datos generales",
            "questions": [
                {"id":"institucion","label":"Institución educativa","type":"select","options":INSTITUCIONES,"required":True},
                {"id":"sexo","label":"Sexo","type":"radio","options":["Mujer","Hombre","Prefiero no decir"],"required":True},
                {"id":"edad","label":"Edad","type":"number","required":True,"min":12,"max":25},
                {"id":"grado","label":"Grado / Condición","type":"select","options":["5° secundaria","Egresado/a"],"required":True},
                {"id":"zona","label":"Zona de residencia","type":"radio","options":["Urbana","Periurbana","Rural"],"required":True},
            ],
        },
        {
            "title": "B. Habilidades de emprendimiento (R2)",
            "questions": [
                {"id":"b1_participo","label":"¿Participaste en las sesiones de formación en emprendimiento?","type":"radio","options":["Sí","No"],"required":True},
                {"id":"b2_habilidad","label":"¿Cuánto mejoraron tus habilidades para idear un emprendimiento? (1=Nada a 5=Mucho)","type":"likert","required":True},
                {"id":"b3_conocer","label":"¿Conoces las ventajas e inconvenientes de crear una empresa?","type":"radio","options":["Mucho","Algo","Poco","Nada"],"required":True},
                {"id":"b4_equipo","label":"¿Participaste en un equipo de emprendimiento escolar?","type":"radio","options":["Sí","No"]},
                {"id":"b5_activo","label":"¿Tu emprendimiento sigue funcionando actualmente?","type":"radio","options":["Sí","No","No aplica"]},
            ],
        },
        {
            "title": "C. Derechos económicos y sociales (R3)",
            "questions": [
                {"id":"c1_derechos","label":"Menciona TRES derechos económicos o sociales que aprendiste durante el proyecto.","type":"textarea","required":True},
                {"id":"c2_consulta","label":"¿Realizaste consultas sobre empleo o autoempleo en el gabinete de orientación?","type":"radio","options":["Sí","No"]},
                {"id":"c3_conoc","label":"Valora tu conocimiento actual sobre derechos laborales (1=Nada a 5=Mucho)","type":"likert"},
            ],
        },
        {
            "title": "D. Impacto en tu proyecto de vida",
            "questions": [
                {"id":"d1_futuro","label":"¿El proyecto cambió la forma en que ves tu futuro laboral?","type":"radio","options":["Mucho","Algo","Poco","Nada"],"required":True},
                {"id":"d2_metas","label":"¿Tienes un proyecto de vida con metas claras?","type":"radio","options":["Sí","En parte","No"]},
                {"id":"d3_autoempleo","label":"¿Estás autoempleado o desarrollando una iniciativa productiva?","type":"radio","options":["Sí","No"]},
                {"id":"d4_relato","label":"Cuéntanos brevemente el cambio MÁS significativo que viviste con el proyecto (opcional).","type":"textarea"},
            ],
        },
        {
            "title": "E. Enfoque de género",
            "questions": [
                {"id":"e1_igual","label":"¿Mujeres y hombres tuvieron las mismas oportunidades de participar?","type":"radio","options":["Sí","En parte","No"],"required":True},
                {"id":"e2_dif","label":"¿Identificaste alguna dificultad para participar relacionada con tu género? (Describe)","type":"textarea"},
            ],
        },
    ],
}


ENCUESTA_DOCENTES = {
    "code": "docentes",
    "title": "Cuestionario a docentes — Evaluación Final",
    "intro": (
        "Esta encuesta busca conocer su valoración del proyecto. "
        "Es anónima y dura unos 25 minutos."
    ),
    "sections": [
        {
            "title": "A. Datos generales",
            "questions": [
                {"id":"institucion","label":"Institución educativa","type":"select","options":INSTITUCIONES,"required":True},
                {"id":"sexo","label":"Sexo","type":"radio","options":["Mujer","Hombre","Prefiero no decir"],"required":True},
                {"id":"anios","label":"Años de experiencia docente","type":"number","required":True,"min":0,"max":60},
                {"id":"area","label":"Área curricular principal","type":"text","required":True},
            ],
        },
        {
            "title": "B. Fortalecimiento de capacidades (R1)",
            "questions": [
                {"id":"b1_cursos","label":"¿Completaste los 2 cursos de formación híbrida en emprendimiento juvenil?","type":"radio","options":["Sí","No"],"required":True},
                {"id":"b2_util","label":"Utilidad de la formación para tu práctica pedagógica (1=Nula a 5=Muy alta)","type":"likert","required":True},
                {"id":"b3_aplica","label":"¿Aplicas metodologías activas de fomento del emprendimiento en aula?","type":"radio","options":["Siempre","A veces","Nunca"],"required":True},
                {"id":"b4_protocolo","label":"¿Tu IE cuenta con un protocolo de integración de contenidos de emprendimiento?","type":"radio","options":["Sí","No"]},
                {"id":"b5_digital","label":"¿Tuviste competencias digitales suficientes para la fase online (Moodle)?","type":"radio","options":["Sí","En parte","No"]},
            ],
        },
        {
            "title": "C. Eficiencia y gestión",
            "questions": [
                {"id":"c1_organ","label":"¿La organización de los cursos (tiempos, plataforma, acompañamiento) fue adecuada?","type":"radio","options":["Sí","En parte","No"]},
                {"id":"c2_facilita","label":"¿El centro educativo facilitó tu participación (flexibilización horaria)?","type":"radio","options":["Sí","En parte","No"]},
            ],
        },
        {
            "title": "D. Sostenibilidad e impacto",
            "questions": [
                {"id":"d1_continua","label":"¿Continuarás aplicando lo aprendido sin el apoyo del proyecto?","type":"radio","options":["Sí","Probablemente","No"]},
                {"id":"d2_pei","label":"¿El emprendimiento se ha incorporado al PEI o programación de tu IE?","type":"radio","options":["Sí","En proceso","No"]},
                {"id":"d3_cambios","label":"¿Qué cambios observas en los estudiantes tras el proyecto?","type":"textarea"},
            ],
        },
    ],
}


def get_form(code: str):
    return {"estudiantes": ENCUESTA_ESTUDIANTES, "docentes": ENCUESTA_DOCENTES}.get(code)


def all_question_ids(form: dict):
    ids = []
    for sec in form["sections"]:
        for q in sec["questions"]:
            ids.append(q["id"])
    return ids
