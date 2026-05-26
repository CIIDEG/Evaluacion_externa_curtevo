"""Definición de las encuestas y formularios cualitativos."""

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


# ==============================================================
#                      ANEXO 1 — ESTUDIANTES
# ==============================================================
ENCUESTA_ESTUDIANTES = {
    "code": "estudiantes",
    "title": "Anexo 1 · Cuestionario a estudiantes",
    "kind": "encuesta",
    "intro": (
        "Tu opinión es muy importante para evaluar el proyecto. "
        "Esta encuesta es anónima y dura unos 20 minutos. "
        "No hay respuestas correctas o incorrectas."
    ),
    "target": "Muestra ≥ 196 estudiantes",
    "sections": [
        {"title": "A. Datos generales", "questions": [
            {"id":"institucion","label":"Institución educativa","type":"select","options":INSTITUCIONES,"required":True},
            {"id":"sexo","label":"Sexo","type":"radio","options":["Mujer","Hombre","Prefiero no decir"],"required":True},
            {"id":"edad","label":"Edad","type":"number","required":True,"min":12,"max":25},
            {"id":"grado","label":"Grado / Condición","type":"select","options":["5° secundaria","Egresado/a"],"required":True},
            {"id":"zona","label":"Zona de residencia","type":"radio","options":["Urbana","Periurbana","Rural"],"required":True},
        ]},
        {"title": "B. Habilidades de emprendimiento (R2)", "questions": [
            {"id":"b1_participo","label":"¿Participaste en las sesiones de formación en emprendimiento?","type":"radio","options":["Sí","No"],"required":True},
            {"id":"b2_habilidad","label":"¿Cuánto mejoraron tus habilidades para idear un emprendimiento? (1=Nada · 5=Mucho)","type":"likert","required":True},
            {"id":"b3_conocer","label":"¿Conoces las ventajas e inconvenientes de crear una empresa?","type":"radio","options":["Mucho","Algo","Poco","Nada"],"required":True},
            {"id":"b4_equipo","label":"¿Participaste en un equipo de emprendimiento escolar?","type":"radio","options":["Sí","No"]},
            {"id":"b5_activo","label":"¿Tu emprendimiento sigue funcionando actualmente?","type":"radio","options":["Sí","No","No aplica"]},
        ]},
        {"title": "C. Derechos económicos y sociales (R3)", "questions": [
            {"id":"c1_derechos","label":"Menciona TRES derechos económicos o sociales que aprendiste durante el proyecto.","type":"textarea","required":True},
            {"id":"c2_consulta","label":"¿Realizaste consultas sobre empleo o autoempleo en el gabinete de orientación?","type":"radio","options":["Sí","No"]},
            {"id":"c3_conoc","label":"Valora tu conocimiento actual sobre derechos laborales (1=Nada · 5=Mucho)","type":"likert"},
        ]},
        {"title": "D. Impacto en tu proyecto de vida", "questions": [
            {"id":"d1_futuro","label":"¿El proyecto cambió la forma en que ves tu futuro laboral?","type":"radio","options":["Mucho","Algo","Poco","Nada"],"required":True},
            {"id":"d2_metas","label":"¿Tienes un proyecto de vida con metas claras?","type":"radio","options":["Sí","En parte","No"]},
            {"id":"d3_autoempleo","label":"¿Estás autoempleado o desarrollando una iniciativa productiva?","type":"radio","options":["Sí","No"]},
            {"id":"d4_relato","label":"Cuéntanos brevemente el cambio MÁS significativo que viviste con el proyecto (opcional).","type":"textarea"},
        ]},
        {"title": "E. Enfoque de género", "questions": [
            {"id":"e1_igual","label":"¿Mujeres y hombres tuvieron las mismas oportunidades de participar?","type":"radio","options":["Sí","En parte","No"],"required":True},
            {"id":"e2_dif","label":"¿Identificaste alguna dificultad para participar relacionada con tu género? (Describe)","type":"textarea"},
        ]},
    ],
}


# ==============================================================
#                      ANEXO 2 — DOCENTES
# ==============================================================
ENCUESTA_DOCENTES = {
    "code": "docentes",
    "title": "Anexo 2 · Cuestionario a docentes",
    "kind": "encuesta",
    "intro": (
        "Esta encuesta busca conocer su valoración del proyecto. "
        "Es anónima y dura unos 25 minutos."
    ),
    "target": "Censo · 24 docentes",
    "sections": [
        {"title": "A. Datos generales", "questions": [
            {"id":"institucion","label":"Institución educativa","type":"select","options":INSTITUCIONES,"required":True},
            {"id":"sexo","label":"Sexo","type":"radio","options":["Mujer","Hombre","Prefiero no decir"],"required":True},
            {"id":"anios","label":"Años de experiencia docente","type":"number","required":True,"min":0,"max":60},
            {"id":"area","label":"Área curricular principal","type":"text","required":True},
        ]},
        {"title": "B. Fortalecimiento de capacidades (R1)", "questions": [
            {"id":"b1_cursos","label":"¿Completaste los 2 cursos de formación híbrida en emprendimiento juvenil?","type":"radio","options":["Sí","No"],"required":True},
            {"id":"b2_util","label":"Utilidad de la formación para tu práctica pedagógica (1=Nula · 5=Muy alta)","type":"likert","required":True},
            {"id":"b3_aplica","label":"¿Aplicas metodologías activas de fomento del emprendimiento en aula?","type":"radio","options":["Siempre","A veces","Nunca"],"required":True},
            {"id":"b4_protocolo","label":"¿Tu IE cuenta con un protocolo de integración de contenidos de emprendimiento?","type":"radio","options":["Sí","No"]},
            {"id":"b5_digital","label":"¿Tuviste competencias digitales suficientes para la fase online (Moodle)?","type":"radio","options":["Sí","En parte","No"]},
        ]},
        {"title": "C. Eficiencia y gestión", "questions": [
            {"id":"c1_organ","label":"¿La organización de los cursos (tiempos, plataforma, acompañamiento) fue adecuada?","type":"radio","options":["Sí","En parte","No"]},
            {"id":"c2_facilita","label":"¿El centro educativo facilitó tu participación (flexibilización horaria)?","type":"radio","options":["Sí","En parte","No"]},
        ]},
        {"title": "D. Sostenibilidad e impacto", "questions": [
            {"id":"d1_continua","label":"¿Continuarás aplicando lo aprendido sin el apoyo del proyecto?","type":"radio","options":["Sí","Probablemente","No"]},
            {"id":"d2_pei","label":"¿El emprendimiento se ha incorporado al PEI o programación de tu IE?","type":"radio","options":["Sí","En proceso","No"]},
            {"id":"d3_cambios","label":"¿Qué cambios observas en los estudiantes tras el proyecto?","type":"textarea"},
        ]},
    ],
}


# ==============================================================
#               ANEXO 3 — ENTREVISTA KII (cualitativo)
# ==============================================================
ENTREVISTA_KII = {
    "code": "kii",
    "title": "Anexo 3 · Guía de entrevista a informantes clave (KII)",
    "kind": "cualitativo",
    "intro": (
        "Entrevista semiestructurada dirigida a coordinadores IS-IPP, directores de IIEE, "
        "representantes de la UGEL Cutervo y líderes docentes. Dura 45–60 minutos. "
        "Para cada pregunta puede escribir la respuesta y/o grabar el audio."
    ),
    "target": "15 a 18 entrevistas",
    "sections": [
        {"title": "Identificación del entrevistado", "questions": [
            {"id":"entrevistado","label":"Nombre del entrevistado/a (puede ser iniciales)","type":"text","required":True},
            {"id":"cargo","label":"Cargo / rol institucional","type":"text","required":True},
            {"id":"institucion","label":"Institución / Entidad","type":"text","required":True},
            {"id":"sexo","label":"Sexo","type":"radio","options":["Mujer","Hombre","Prefiero no decir"]},
            {"id":"fecha","label":"Fecha de la entrevista","type":"date","required":True},
            {"id":"lugar","label":"Lugar de la entrevista","type":"text"},
            {"id":"consentimiento","label":"¿Se obtuvo consentimiento informado?","type":"radio","options":["Sí","No"],"required":True},
        ]},
        {"title": "Preguntas (responda escribiendo y/o grabando audio)", "questions": [
            {"id":"p1_pertinencia","label":"1. PERTINENCIA · Desde su rol, ¿en qué medida el proyecto respondió a las necesidades reales de la juventud de Cutervo?","type":"audio_text","required":True},
            {"id":"p2_coherencia","label":"2. COHERENCIA · ¿Cómo se articuló la intervención con las políticas educativas locales y regionales y con otros actores del territorio?","type":"audio_text"},
            {"id":"p3_eficiencia","label":"3. EFICIENCIA · ¿Cómo valora la gestión del consorcio IS-IPP: comunicación, toma de decisiones y cumplimiento de plazos y presupuesto?","type":"audio_text"},
            {"id":"p4_eficacia","label":"4. EFICACIA · ¿Qué resultados concretos observa en docentes y estudiantes? ¿Se lograron con equidad de género?","type":"audio_text"},
            {"id":"p5_impacto","label":"5. IMPACTO · ¿Qué transformaciones significativas —esperadas o no— atribuye al proyecto?","type":"audio_text"},
            {"id":"p6_sostenibilidad","label":"6. SOSTENIBILIDAD · ¿Qué capacidades, recursos o redes quedan instaladas para dar continuidad sin apoyo externo?","type":"audio_text"},
            {"id":"p7_lecciones","label":"7. LECCIONES APRENDIDAS · ¿Qué factores facilitaron u obstaculizaron la ejecución? ¿Qué recomendaciones destacaría?","type":"audio_text"},
        ]},
        {"title": "Notas del evaluador", "questions": [
            {"id":"notas","label":"Observaciones, lenguaje no verbal, contexto","type":"textarea"},
        ]},
    ],
}


# ==============================================================
#              ANEXO 4 — GRUPOS FOCALES (cualitativo)
# ==============================================================
FGD_JOVENES = {
    "code": "fgd_jovenes",
    "title": "Anexo 4a · Grupo focal con jóvenes (FGD)",
    "kind": "cualitativo",
    "intro": (
        "Protocolo de grupo focal con 6–10 estudiantes / jóvenes. Duración: 60–90 minutos. "
        "Espacio seguro y diferenciado. Para cada pregunta puede escribir la síntesis y/o grabar el audio del grupo."
    ),
    "target": "3 grupos focales con jóvenes",
    "sections": [
        {"title": "Identificación del grupo focal", "questions": [
            {"id":"institucion","label":"Institución educativa / sede","type":"select","options":INSTITUCIONES,"required":True},
            {"id":"fecha","label":"Fecha","type":"date","required":True},
            {"id":"n_part","label":"Número total de participantes","type":"number","required":True,"min":3,"max":30},
            {"id":"n_mujeres","label":"De los anteriores, número de mujeres","type":"number","required":True,"min":0,"max":30},
            {"id":"facilitador","label":"Facilitador/a","type":"text"},
            {"id":"consentimiento","label":"¿Se obtuvo consentimiento informado del grupo?","type":"radio","options":["Sí","No"],"required":True},
        ]},
        {"title": "Apertura y reglas", "questions": [
            {"id":"apertura","label":"Apertura · presentación, consentimiento y reglas de confidencialidad. (Notas)","type":"textarea"},
        ]},
        {"title": "Preguntas (síntesis escrita y/o audio)", "questions": [
            {"id":"q1_aprendizajes","label":"¿Qué fue lo más valioso que aprendieron en el proyecto? ¿Qué cambiarían?","type":"audio_text","required":True},
            {"id":"q2_metodologia","label":"¿Cómo funcionó la metodología «joven a joven» y los municipios escolares?","type":"audio_text"},
            {"id":"q3_genero","label":"¿Tuvieron las chicas y los chicos las mismas oportunidades de participar y liderar?","type":"audio_text"},
            {"id":"q4_emprendimientos","label":"¿Qué emprendimientos surgieron y cuáles siguen activos? ¿Qué los sostiene o los limita?","type":"audio_text"},
            {"id":"q5_huella","label":"¿Qué recomiendan para que el proyecto deje huella duradera?","type":"audio_text"},
        ]},
        {"title": "Notas del evaluador", "questions": [
            {"id":"notas","label":"Observaciones, dinámica del grupo, lenguaje no verbal","type":"textarea"},
        ]},
    ],
}

FGD_DOCENTES = {
    "code": "fgd_docentes",
    "title": "Anexo 4b · Grupo focal con docentes (FGD)",
    "kind": "cualitativo",
    "intro": (
        "Protocolo de grupo focal con docentes capacitados/as. Duración 60–90 minutos. "
        "Para cada pregunta puede escribir la síntesis y/o grabar el audio del grupo."
    ),
    "target": "3 grupos focales con docentes",
    "sections": [
        {"title": "Identificación del grupo focal", "questions": [
            {"id":"institucion","label":"Institución educativa / sede","type":"select","options":INSTITUCIONES,"required":True},
            {"id":"fecha","label":"Fecha","type":"date","required":True},
            {"id":"n_part","label":"Número total de participantes","type":"number","required":True,"min":3,"max":30},
            {"id":"n_mujeres","label":"De los anteriores, número de mujeres","type":"number","required":True,"min":0,"max":30},
            {"id":"facilitador","label":"Facilitador/a","type":"text"},
            {"id":"consentimiento","label":"¿Se obtuvo consentimiento informado del grupo?","type":"radio","options":["Sí","No"],"required":True},
        ]},
        {"title": "Preguntas (síntesis escrita y/o audio)", "questions": [
            {"id":"q1_practica","label":"¿Cómo cambió su práctica pedagógica tras la formación en emprendimiento?","type":"audio_text","required":True},
            {"id":"q2_apoyos","label":"¿Qué apoyos institucionales (dirección, UGEL) facilitaron o limitaron la aplicación?","type":"audio_text"},
            {"id":"q3_sostenibilidad","label":"¿Qué condiciones se necesitan para sostener lo logrado tras el cierre del proyecto?","type":"audio_text"},
        ]},
        {"title": "Notas del evaluador", "questions": [
            {"id":"notas","label":"Observaciones, consensos, disensos, clima del grupo","type":"textarea"},
        ]},
    ],
}


# ==============================================================
#                ANEXO 5 — OBSERVACIÓN DE CAMPO
# ==============================================================
OBSERVACION = {
    "code": "observacion",
    "title": "Anexo 5 · Pauta de observación de campo",
    "kind": "observacion",
    "intro": (
        "Pauta de observación directa en las instituciones educativas. "
        "Permite registrar evidencias tangibles del estado de los emprendimientos y de las dinámicas de participación. "
        "Puede registrar texto, fotos y/o audio."
    ),
    "target": "8 a 12 IIEE visitadas",
    "sections": [
        {"title": "Identificación", "questions": [
            {"id":"institucion","label":"Institución educativa visitada","type":"select","options":INSTITUCIONES,"required":True},
            {"id":"fecha","label":"Fecha","type":"date","required":True},
            {"id":"observador","label":"Observador/a","type":"text"},
            {"id":"hora","label":"Hora de la visita","type":"text"},
        ]},
        {"title": "Aspectos observados", "questions": [
            {"id":"o1_emprend","label":"1. Existencia y estado de los emprendimientos escolares.","type":"audio_text"},
            {"id":"o1_estado","label":"   Estado del emprendimiento","type":"radio","options":["Operativo","Incipiente","Inactivo","No existe"]},
            {"id":"o2_recursos","label":"2. Recursos y materiales pedagógicos instalados en la IE.","type":"audio_text"},
            {"id":"o3_municipio","label":"3. Espacios y funcionamiento del municipio escolar.","type":"audio_text"},
            {"id":"o4_aula","label":"4. Visibilidad de contenidos de emprendimiento y derechos en aula.","type":"audio_text"},
            {"id":"o5_dinamicas","label":"5. Dinámicas de participación y liderazgo (con enfoque de género).","type":"audio_text"},
        ]},
        {"title": "Evidencia fotográfica y audio resumen", "questions": [
            {"id":"foto","label":"Fotografía representativa de la visita (opcional)","type":"file"},
            {"id":"resumen_audio","label":"Resumen general de la visita (audio o texto)","type":"audio_text"},
        ]},
    ],
}


# ==============================================================
#           ANEXO 6 — HISTORIAS DE CAMBIO MÁS SIGNIFICATIVO
# ==============================================================
MSC = {
    "code": "msc",
    "title": "Anexo 6 · Historias de Cambio Más Significativo (MSC)",
    "kind": "cualitativo",
    "intro": (
        "Técnica narrativa para capturar transformaciones en los proyectos de vida de los adolescentes y jóvenes. "
        "Duración 45 minutos. Para cada pregunta puede escribir la respuesta y/o grabar el audio."
    ),
    "target": "8 a 12 relatos",
    "sections": [
        {"title": "Identificación", "questions": [
            {"id":"narrador","label":"Nombre del narrador/a (puede ser iniciales)","type":"text","required":True},
            {"id":"sexo","label":"Sexo","type":"radio","options":["Mujer","Hombre","Prefiero no decir"],"required":True},
            {"id":"edad","label":"Edad","type":"number","min":12,"max":30},
            {"id":"institucion","label":"Institución educativa","type":"select","options":INSTITUCIONES},
            {"id":"fecha","label":"Fecha del relato","type":"date","required":True},
            {"id":"consentimiento","label":"¿Se obtuvo consentimiento informado?","type":"radio","options":["Sí","No"],"required":True},
        ]},
        {"title": "Relato (texto y/o audio)", "questions": [
            {"id":"r1_antes_despues","label":"1. Cuéntame tu historia: ¿cómo eras antes del proyecto y cómo eres ahora?","type":"audio_text","required":True},
            {"id":"r2_cambio","label":"2. De todos los cambios que viviste, ¿cuál consideras el más significativo y por qué?","type":"audio_text","required":True},
            {"id":"r3_actividad","label":"3. ¿Qué actividad o momento del proyecto provocó ese cambio?","type":"audio_text"},
            {"id":"r4_familia","label":"4. ¿Cómo ha influido ese cambio en tu familia o en tu comunidad?","type":"audio_text"},
            {"id":"r5_aprendizaje","label":"5. Si pudieras conservar una sola cosa de lo aprendido, ¿cuál sería?","type":"audio_text"},
        ]},
        {"title": "Notas del evaluador", "questions": [
            {"id":"notas","label":"Observaciones, gestualidad, énfasis","type":"textarea"},
        ]},
    ],
}


# Registro central de todos los formularios
ALL_FORMS = [
    ENCUESTA_ESTUDIANTES,
    ENCUESTA_DOCENTES,
    ENTREVISTA_KII,
    FGD_JOVENES,
    FGD_DOCENTES,
    OBSERVACION,
    MSC,
]

FORMS_BY_CODE = {f["code"]: f for f in ALL_FORMS}


def get_form(code: str):
    return FORMS_BY_CODE.get(code)


def all_question_ids(form: dict):
    ids = []
    for sec in form["sections"]:
        for q in sec["questions"]:
            ids.append(q["id"])
    return ids
