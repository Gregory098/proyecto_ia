# Lex Innova — Triage jurídico con IA (Gate 1)

Miniaplicación en Python que recibe el relato de un caso, lo envía a un modelo de
Gemini por API y devuelve una **clasificación estructurada** (materia, urgencia,
resumen y una orientación provisoria).

Es la primera capa de Lex Innova, una plataforma intermediaria entre personas o
empresas con un problema jurídico o administrativo y el abogado adecuado. Esta
versión **no reemplaza a un abogado**: ordena el caso para derivarlo y entrega una
orientación general, siempre acompañada de una advertencia.

## Qué hace

1. Recibe un relato de texto (por defecto, un caso de ejemplo de acoso laboral).
2. Lo envía a Gemini con un **prompt de sistema** que fija el rol, las materias
   permitidas y las reglas de prudencia.
3. Exige la respuesta en **JSON** y la valida (campos, materia y urgencia permitidas).
4. Traduce los fallos del proveedor (llave inválida, límite de uso, modelo no
   encontrado, timeout, caída de red) a mensajes claros, sin que el programa se caiga.

Ejemplo de salida:

```json
{
  "materia": "ley_karin",
  "urgencia": "alta",
  "resumen": "Un trabajador reporta hostigamiento reiterado por parte de su jefatura...",
  "orientacion_provisoria": "Es recomendable documentar todas las situaciones...",
  "advertencia": "Esta es una orientación provisoria y general que debe ser confirmada por un abogado especialista."
}
```

## Requisitos

- Python 3.10 o superior (probado con 3.12)
- Git
- Una llave de la API de Gemini (gratuita): https://aistudio.google.com/apikey

## Instalación

**Linux / macOS**

```bash
git clone https://github.com/Gregory098/proyecto_ia.git
cd proyecto_ia
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

**Windows (PowerShell)**

```powershell
git clone https://github.com/Gregory098/proyecto_ia.git
cd proyecto_ia
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

## Configuración

Abre el archivo `.env` (nunca se sube al repositorio) y completa:

```
GEMINI_API_KEY=tu_llave_real
GEMINI_MODEL=nombre_del_modelo
```

Para ver qué modelos puede usar tu llave (elige uno que diga `flash`):

```bash
curl -s -H "x-goog-api-key: $GEMINI_API_KEY" https://generativelanguage.googleapis.com/v1beta/models | jq -r '.models[] | select(.supportedGenerationMethods | index("generateContent")) | .name'
```

Si un modelo responde 404 o 429, prueba con otro de la lista.

## Ejecución

```bash
# Caso de ejemplo
python src/triage_lex.py

# Caso propio
python src/triage_lex.py "Me despidieron sin carta de aviso y no me pagaron el finiquito"
```

## Pruebas

```bash
python -m unittest discover -s tests
```

Son 19 pruebas que **no consumen la API**: simulan sus respuestas y verifican la
entrada vacía, llave ausente, errores 401 y 429, timeout, caída de conexión,
respuesta que no es JSON, campos faltantes y materia no reconocida.

## Estructura del repositorio

```
src/triage_lex.py          Módulo principal (armar, enviar, extraer, validar, costo)
tests/test_triage_lex.py   Pruebas unitarias (sin consumir la API)
prompts/                   Banco de prompts, prueba de consistencia y su registro
scripts/comparar_modelos.py  Compara dos modelos (latencia, tokens, costo)
docs/                      Diagrama, decisión de arquitectura y evidencias
.env.example               Variables de entorno necesarias (sin valores reales)
requirements.txt           Dependencias con versiones fijas
```

## Decisiones de diseño

- **Funciones pequeñas y separadas** (`armar_peticion`, `enviar_peticion`,
  `extraer_texto`, `validar_triage`): cada una hace una cosa y se puede probar sola.
- **Salida en JSON validada**: el resto de la plataforma necesita datos
  estructurados; por eso no se confía en texto libre del modelo.
- **Temperatura baja (0.2)**: se prioriza consistencia sobre creatividad.
- **Prompt con reglas de prudencia**: el modelo no debe inventar artículos, leyes ni
  plazos, ni repetir datos personales sensibles.
- **Secretos fuera del código**: la llave vive en `.env`, excluido por `.gitignore`.

## Banco de prompts y comparación de modelos

```bash
python prompts/test_consistencia.py          # 3 repeticiones por prompt
python scripts/comparar_modelos.py MODELO_A MODELO_B 5
```

## Límites conocidos

- Es una orientación **provisoria**; no constituye asesoría jurídica.
- No guarda casos ni documentos todavía.
- No debe usarse con datos personales sensibles reales mientras no existan controles
  de privacidad.
- La clasificación depende del modelo elegido y puede variar entre ejecuciones.

## Evidencias del Gate 1

- Diagrama de arquitectura: `docs/arquitectura.png`
- Decisión de modelo con datos reales: `docs/decision-arquitectura.md`
- Banco de prompts y registro de consistencia: `prompts/`
- Registro de ensayo de instalación limpia: `docs/ensayo_instalacion_limpia.md`

## Próximos pasos

Cliente modular con reintentos y registro de costo, recuperación de normativa (RAG),
API con FastAPI y contenedor Docker.

## Derechos

Entrega académica. Todos los derechos reservados (ver `NOTICE.md`).
