"""Compara dos modelos con datos reales: latencia, tokens y costo por petición.

Uso (raíz del repositorio, entorno virtual activo):
    python scripts/comparar_modelos.py MODELO_A MODELO_B [repeticiones]

Los precios (USD por 1 millón de tokens) se leen de docs/precios.json, que TÚ completas
desde la página oficial de precios del proveedor. Escribe docs/comparacion_modelos.json
y docs/tabla_comparativa.md.
"""
import json
import os
import sys
import time
from datetime import date

RAIZ = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(RAIZ, "src"))

from dotenv import load_dotenv  # noqa: E402
from triage_lex import (  # noqa: E402
    armar_peticion, calcular_costo, enviar_peticion, extraer_texto, validar_triage,
)

CASO = "Trabajo hace 3 años en una empresa y mi jefe me grita frente a mis compañeros. Ayer me dijeron que me despedirán."
PAUSA_SEGUNDOS = 4


def medir(modelo, precios, repeticiones):
    latencias, costos, validos, tokens_in, tokens_out, version = [], [], 0, [], [], modelo
    for i in range(1, repeticiones + 1):
        try:
            url, headers, body = armar_peticion(CASO, modelo=modelo)
            inicio = time.time()
            datos = enviar_peticion(url, headers, body)
            latencias.append(time.time() - inicio)
            version = datos.get("modelVersion", version)
            uso = datos["usageMetadata"]
            tokens_in.append(uso["promptTokenCount"])
            tokens_out.append(uso["candidatesTokenCount"])
            if precios:
                costos.append(calcular_costo(datos, precios["entrada_usd_por_millon"] / 1e6,
                                             precios["salida_usd_por_millon"] / 1e6))
            validar_triage(extraer_texto(datos))
            validos += 1
            print(f"  {modelo} intento {i}: {latencias[-1]:.2f} s")
        except (RuntimeError, ValueError, KeyError) as error:
            print(f"  {modelo} intento {i}: FALLÓ -> {error}")
        time.sleep(PAUSA_SEGUNDOS)
    promedio = lambda xs: round(sum(xs) / len(xs), 6) if xs else None  # noqa: E731
    return {
        "modelo_pedido": modelo, "modelo_atendido": version, "intentos": repeticiones,
        "respuestas_validas": validos, "latencia_promedio_s": promedio(latencias),
        "tokens_entrada_promedio": promedio(tokens_in), "tokens_salida_promedio": promedio(tokens_out),
        "costo_promedio_usd": promedio(costos), "precios_usados": precios,
    }


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    modelos = [sys.argv[1], sys.argv[2]]
    repeticiones = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    ruta_precios = os.path.join(RAIZ, "docs", "precios.json")
    try:
        with open(ruta_precios, encoding="utf-8") as archivo:
            tabla_precios = json.load(archivo)
    except FileNotFoundError:
        tabla_precios = {}

    resultados = []
    for modelo in modelos:
        print(f"\nModelo: {modelo}")
        resultados.append(medir(modelo, tabla_precios.get(modelo), repeticiones))

    salida = {"fecha": date.today().isoformat(), "caso_de_prueba": CASO, "resultados": resultados}
    with open(os.path.join(RAIZ, "docs", "comparacion_modelos.json"), "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    a, b = resultados
    filas = [
        ("Precio entrada (USD/1M tokens)", lambda r: (r["precios_usados"] or {}).get("entrada_usd_por_millon", "falta en precios.json")),
        ("Precio salida (USD/1M tokens)", lambda r: (r["precios_usados"] or {}).get("salida_usd_por_millon", "falta en precios.json")),
        ("Latencia promedio (s)", lambda r: r["latencia_promedio_s"]),
        ("Tokens entrada / salida (prom.)", lambda r: f"{r['tokens_entrada_promedio']} / {r['tokens_salida_promedio']}"),
        ("Costo promedio por petición (USD)", lambda r: r["costo_promedio_usd"] if r["costo_promedio_usd"] is not None else "falta precio"),
        ("Respuestas válidas", lambda r: f"{r['respuestas_validas']}/{r['intentos']}"),
    ]
    md = [f"Tabla generada el {salida['fecha']} con {repeticiones} peticiones por modelo.", "",
          f"| Criterio | {a['modelo_pedido']} | {b['modelo_pedido']} |", "|---|---|---|"]
    md += [f"| {nombre} | {f(a)} | {f(b)} |" for nombre, f in filas]
    texto = "\n".join(md) + "\n"
    with open(os.path.join(RAIZ, "docs", "tabla_comparativa.md"), "w", encoding="utf-8") as f:
        f.write(texto)
    print("\n" + texto)


if __name__ == "__main__":
    load_dotenv()
    main()
