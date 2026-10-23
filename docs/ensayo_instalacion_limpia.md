# Registro de ensayo de instalación limpia

| Fecha | Qué se hizo | Qué se encontró | Qué se corrigió | Resultado |
|---|---|---|---|---|
| 2026-10-22 | Clon nuevo, venv, pip install, pruebas | El .env.example tenía el nombre de variable distinto al que lee el código (GEMINI_API_KEY) | Se corrigió el .env.example (commit 8edbc52) | 13 pruebas OK |
| 2026-10-23 | Clon nuevo en carpeta temporal, venv nuevo, pip install -r requirements.txt, copia de .env, pruebas y ejecución real | Nada falló; el .env no viene en el repo, por diseño, y se crea desde .env.example | Sin cambios necesarios | 19 pruebas OK y JSON de triage válido, sin Traceback |
