"""Prueba de consistencia del banco de prompts.

Para cada prompt hace N llamadas REALES a la API con el mismo ejemplo y cuenta cuántas
veces la respuesta fue JSON válido con las claves esperadas. Guarda el resultado en
prompts/registro_resultados.json (esa es la evidencia que se versiona).

Uso (desde la raíz del repositorio, con el entorno virtual activo):
    python prompts/test_consistencia.py        # 3 repeticiones por prompt
    python prompts/test_consistencia.py 5      # 5 repeticiones
"""
import json
import os
import sys
import time
from datetime import datetime

RAIZ = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(RAIZ, "src"))
sys.path.insert(0, os.path.dirname(__file__))

from banco import BANCO_DE_PROMPTS  # noqa: E402
from triage_lex import (  # noqa: E402
    armar_peticion, enviar_peticion, extraer_texto, parsear_respuesta_json,
)

PAUSA_SEGUNDOS = 4  # espacia las llamadas para no chocar con el límite de uso (429)


def probar(prompt, repeticiones):
    validos, fallos = 0, []
    for i in range(1, repeticiones + 1):
        try:
            url, headers, body = armar_peticion(
                prompt["ejemplo"], prompt["system_instruction"], prompt.get("response_schema")
            )
            datos = parsear_respuesta_json(extraer_texto(enviar_peticion(url, headers, body)))
            faltan = [c for c in prompt["claves_esperadas"] if c not in datos]
            if faltan:
                raise RuntimeError(f"faltan claves: {faltan}")
            validos += 1
            print(f"  intento {i}: OK")
        except (RuntimeError, ValueError) as error:
            fallos.append(f"intento {i}: {error}")
            print(f"  intento {i}: FALLÓ -> {error}")
        time.sleep(PAUSA_SEGUNDOS)
    return validos, fallos


def main():
    repeticiones = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    modelo = os.getenv("GEMINI_MODEL", "(sin definir)")
    registro = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "modelo": modelo,
        "repeticiones_por_prompt": repeticiones,
        "resultados": [],
    }
    for prompt in BANCO_DE_PROMPTS:
        print(f"\nPrompt: {prompt['nombre']}")
        validos, fallos = probar(prompt, repeticiones)
        registro["resultados"].append({
            "prompt": prompt["nombre"],
            "validos": validos,
            "total": repeticiones,
            "consistencia": round(validos / repeticiones, 2),
            "fallos": fallos,
        })
        print(f"  => {validos}/{repeticiones} válidos")

    ruta = os.path.join(os.path.dirname(__file__), "registro_resultados.json")
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(registro, archivo, ensure_ascii=False, indent=2)
    print(f"\nRegistro guardado en {os.path.relpath(ruta, RAIZ)}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
