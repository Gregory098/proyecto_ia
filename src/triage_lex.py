"""Lex Innova - Miniaplicación de triage jurídico (Gate 1).

Recibe el relato de un caso, lo envía a un modelo de Gemini mediante su API REST
y devuelve una clasificación estructurada (materia, urgencia, resumen y una
orientación provisoria). Es la primera capa de la plataforma: no reemplaza a un
abogado, solo ordena el caso para que el especialista adecuado lo tome.
"""
import json
import os
import re
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
TIMEOUT_SEGUNDOS = 30

MATERIAS = ["civil", "laboral", "tributario", "ley_karin", "familia", "penal", "otra"]
URGENCIAS = ["baja", "media", "alta"]
CAMPOS_ESPERADOS = ("materia", "urgencia", "resumen", "orientacion_provisoria", "advertencia")

PROMPT_SISTEMA = """Eres el asistente de triage de Lex Innova, una firma de abogados en Chile.
Tu tarea NO es dar asesoría jurídica definitiva: es ordenar el caso para derivarlo al
especialista correcto y entregar una orientación provisoria, prudente y general.

Responde SIEMPRE con un único objeto JSON, sin texto adicional, con exactamente estas claves:
- "materia": una de ["civil", "laboral", "tributario", "ley_karin", "familia", "penal", "otra"].
  Usa "ley_karin" para acoso laboral, acoso sexual o violencia en el trabajo.
- "urgencia": una de ["baja", "media", "alta"]. Usa "alta" si hay plazos cercanos,
  riesgo para la integridad de la persona o pérdida inminente de derechos.
- "resumen": máximo 2 frases con los hechos relevantes.
- "orientacion_provisoria": 2 a 4 frases con una orientación general y prudente.
- "advertencia": recuerda que es una orientación provisoria que debe confirmar un abogado.

Reglas:
- No inventes números de artículos, leyes, plazos ni jurisprudencia. Si no estás seguro, dilo.
- Si el texto no describe un caso jurídico, usa materia "otra" y urgencia "baja".
- No pidas ni repitas datos personales sensibles (RUT, direcciones, cuentas bancarias).
"""


def armar_peticion(relato, system_instruction=PROMPT_SISTEMA, response_schema=None, modelo=None):
    """Valida la entrada y construye la URL, los headers y el cuerpo de la petición.

    El prompt de sistema viaja en un canal separado ("systemInstruction"), nunca
    mezclado con el texto del usuario. `modelo` permite comparar modelos sin tocar el .env.
    """
    if not relato or not relato.strip():
        raise ValueError("El relato del caso no puede estar vacío.")

    api_key = os.getenv("GEMINI_API_KEY")
    modelo = modelo or os.getenv("GEMINI_MODEL")
    if not api_key or api_key == "tu_llave_aqui":
        raise RuntimeError("Falta GEMINI_API_KEY: revisa tu archivo .env.")
    if not modelo:
        raise RuntimeError("Falta GEMINI_MODEL: agrégalo a tu archivo .env.")

    modelo = modelo.removeprefix("models/")
    url = f"{BASE_URL}/{modelo}:generateContent"
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
    config = {"temperature": 0.2, "responseMimeType": "application/json"}
    if response_schema:
        config["responseSchema"] = response_schema
    body = {
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"role": "user", "parts": [{"text": relato.strip()}]}],
        "generationConfig": config,
    }
    return url, headers, body


def enviar_peticion(url, headers, body):
    """Envía la petición y traduce los fallos más comunes a mensajes claros."""
    try:
        respuesta = requests.post(url, headers=headers, json=body, timeout=TIMEOUT_SEGUNDOS)
    except requests.exceptions.Timeout:
        raise RuntimeError("El servicio tardó demasiado en responder (timeout). Intenta de nuevo.")
    except requests.exceptions.ConnectionError:
        raise RuntimeError("No hay conexión con el servicio. Revisa tu internet.")

    codigo = respuesta.status_code
    if codigo in (401, 403):
        raise RuntimeError(f"Credencial rechazada ({codigo}). Revisa GEMINI_API_KEY en tu .env.")
    if codigo == 404:
        raise RuntimeError("Modelo no encontrado (404). Revisa GEMINI_MODEL en tu .env.")
    if codigo == 429:
        raise RuntimeError("Límite de uso excedido (429). Espera un momento y reintenta.")
    if codigo >= 500:
        raise RuntimeError(f"Error del servidor del proveedor ({codigo}). Reintenta más tarde.")
    if codigo != 200:
        raise RuntimeError(f"La petición falló con código {codigo}.")

    try:
        return respuesta.json()
    except ValueError:
        raise RuntimeError("La respuesta del servicio no llegó en formato JSON.")


def extraer_texto(datos):
    """Obtiene el texto generado desde la estructura de respuesta de Gemini."""
    try:
        return datos["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError("La respuesta no trae texto generado (posible bloqueo o formato inesperado).")


def calcular_costo(datos, precio_entrada, precio_salida):
    """Costo en USD de una petición: tokens de entrada x precio + tokens de salida x precio.

    Los precios se reciben como parámetros (USD por token) porque cambian con el tiempo.
    """
    try:
        uso = datos["usageMetadata"]
        return uso["promptTokenCount"] * precio_entrada + uso["candidatesTokenCount"] * precio_salida
    except (KeyError, TypeError):
        raise RuntimeError("La respuesta no trae 'usageMetadata' para calcular el costo.")


def parsear_respuesta_json(texto):
    """Limpia posibles marcas de markdown (```json) y convierte el texto en un diccionario."""
    limpio = re.sub(r"^\s*```(?:json)?\s*", "", texto.strip())
    limpio = re.sub(r"\s*```\s*$", "", limpio)
    try:
        datos = json.loads(limpio)
    except json.JSONDecodeError:
        raise RuntimeError("El modelo no devolvió un JSON válido.")
    if not isinstance(datos, dict):
        raise RuntimeError("El JSON del modelo no tiene la estructura esperada.")
    return datos


def validar_triage(texto):
    """Convierte el texto del modelo en un diccionario y valida su estructura."""
    triage = parsear_respuesta_json(texto)
    faltantes = [campo for campo in CAMPOS_ESPERADOS if campo not in triage]
    if faltantes:
        raise RuntimeError(f"Al JSON del modelo le faltan campos: {', '.join(faltantes)}.")
    if triage["materia"] not in MATERIAS:
        raise RuntimeError(f"Materia no reconocida: {triage['materia']!r}.")
    if triage["urgencia"] not in URGENCIAS:
        raise RuntimeError(f"Urgencia no reconocida: {triage['urgencia']!r}.")
    return triage


def clasificar_caso(relato):
    """Flujo completo: armar -> enviar -> extraer -> validar."""
    url, headers, body = armar_peticion(relato)
    datos = enviar_peticion(url, headers, body)
    texto = extraer_texto(datos)
    return validar_triage(texto)


if __name__ == "__main__":
    relato_demo = (
        "Trabajo hace 3 años en una empresa y mi jefe me grita frente a mis compañeros "
        "y me dejó fuera de los correos importantes. Ayer me dijeron que me van a despedir."
    )
    relato = sys.argv[1] if len(sys.argv) > 1 else relato_demo
    try:
        resultado = clasificar_caso(relato)
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
    except (ValueError, RuntimeError) as error:
        print(f"No se pudo completar el triage: {error}")
        sys.exit(1)
