"""Banco de prompts (versión demostrativa para el Gate 1).

Cada entrada combina un prompt de sistema, un ejemplo de entrada y el esquema JSON
esperado. Son tres tareas genéricas sobre el relato de un caso: clasificar, extraer
datos y resumir. Las versiones de producción de Lex Innova viven fuera de este repositorio.
"""

BANCO_DE_PROMPTS = [
    {
        "nombre": "clasificar_caso",
        "system_instruction": (
            "Eres un asistente de clasificación. Lee el relato y responde únicamente con un "
            "objeto JSON válido, sin texto adicional ni markdown, con las claves 'materia' "
            "(una de: civil, laboral, tributario, familia, penal, otra) y 'urgencia' "
            "(una de: baja, media, alta)."
        ),
        "ejemplo": "Llevo 3 años en mi empresa y ayer me avisaron que me despedirán sin carta ni finiquito.",
        "claves_esperadas": ["materia", "urgencia"],
        "response_schema": {
            "type": "OBJECT",
            "properties": {"materia": {"type": "STRING"}, "urgencia": {"type": "STRING"}},
            "required": ["materia", "urgencia"],
        },
    },
    {
        "nombre": "extraer_datos",
        "system_instruction": (
            "Eres un asistente de extracción. Del relato extrae los datos mencionados y responde "
            "únicamente con un objeto JSON válido, sin markdown, con las claves 'personas' "
            "(lista de roles mencionados, por ejemplo 'jefe' o 'vecino') y 'fechas_o_plazos' "
            "(lista de textos). Si no hay datos, usa listas vacías. No inventes información."
        ),
        "ejemplo": "Mi jefe me gritó el lunes frente a mis compañeros y me dieron plazo hasta el viernes para responder.",
        "claves_esperadas": ["personas", "fechas_o_plazos"],
        "response_schema": {
            "type": "OBJECT",
            "properties": {
                "personas": {"type": "ARRAY", "items": {"type": "STRING"}},
                "fechas_o_plazos": {"type": "ARRAY", "items": {"type": "STRING"}},
            },
            "required": ["personas", "fechas_o_plazos"],
        },
    },
    {
        "nombre": "resumir_caso",
        "system_instruction": (
            "Eres un asistente de resumen. Resume el relato en máximo 2 frases y responde "
            "únicamente con un objeto JSON válido, sin markdown, con la clave 'resumen' (string)."
        ),
        "ejemplo": "Arrendé un departamento hace un año, el dueño no devuelve la garantía y dice que hay daños que no existen.",
        "claves_esperadas": ["resumen"],
        "response_schema": {
            "type": "OBJECT",
            "properties": {"resumen": {"type": "STRING"}},
            "required": ["resumen"],
        },
    },
]
