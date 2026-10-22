"""Pruebas del módulo de triage. No llaman a la API real: simulan sus respuestas."""
import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import triage_lex  # noqa: E402

TRIAGE_OK = {
    "materia": "ley_karin",
    "urgencia": "alta",
    "resumen": "Posible acoso laboral y amenaza de despido.",
    "orientacion_provisoria": "Conviene reunir evidencia y consultar a un especialista.",
    "advertencia": "Orientación provisoria, debe confirmarla un abogado.",
}


def respuesta_falsa(codigo=200, cuerpo=None, json_invalido=False):
    r = MagicMock()
    r.status_code = codigo
    if json_invalido:
        r.json.side_effect = ValueError("no es json")
    else:
        r.json.return_value = cuerpo
    return r


def cuerpo_gemini(texto):
    return {"candidates": [{"content": {"parts": [{"text": texto}]}}]}


class PruebasTriage(unittest.TestCase):
    def setUp(self):
        patcher = patch.dict(os.environ, {"GEMINI_API_KEY": "clave-falsa", "GEMINI_MODEL": "models/modelo-falso"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_caso_valido(self):
        with patch("triage_lex.requests.post", return_value=respuesta_falsa(200, cuerpo_gemini(json.dumps(TRIAGE_OK)))):
            self.assertEqual(triage_lex.clasificar_caso("Mi jefe me acosa"), TRIAGE_OK)

    def test_url_sin_prefijo_models_duplicado(self):
        url, headers, _ = triage_lex.armar_peticion("hola")
        self.assertTrue(url.endswith("/models/modelo-falso:generateContent"))
        self.assertEqual(headers["x-goog-api-key"], "clave-falsa")

    def test_entrada_vacia(self):
        with self.assertRaises(ValueError):
            triage_lex.clasificar_caso("   ")

    def test_falta_llave(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "tu_llave_aqui"}):
            with self.assertRaises(RuntimeError):
                triage_lex.armar_peticion("hola")

    def test_credencial_rechazada(self):
        with patch("triage_lex.requests.post", return_value=respuesta_falsa(401, {})):
            with self.assertRaisesRegex(RuntimeError, "Credencial"):
                triage_lex.clasificar_caso("hola")

    def test_limite_de_uso(self):
        with patch("triage_lex.requests.post", return_value=respuesta_falsa(429, {})):
            with self.assertRaisesRegex(RuntimeError, "429"):
                triage_lex.clasificar_caso("hola")

    def test_error_de_conexion(self):
        with patch("triage_lex.requests.post", side_effect=requests.exceptions.ConnectionError()):
            with self.assertRaisesRegex(RuntimeError, "conexión"):
                triage_lex.clasificar_caso("hola")

    def test_timeout(self):
        with patch("triage_lex.requests.post", side_effect=requests.exceptions.Timeout()):
            with self.assertRaisesRegex(RuntimeError, "timeout"):
                triage_lex.clasificar_caso("hola")

    def test_respuesta_no_json(self):
        with patch("triage_lex.requests.post", return_value=respuesta_falsa(200, json_invalido=True)):
            with self.assertRaisesRegex(RuntimeError, "JSON"):
                triage_lex.clasificar_caso("hola")

    def test_modelo_devuelve_texto_no_json(self):
        with patch("triage_lex.requests.post", return_value=respuesta_falsa(200, cuerpo_gemini("esto no es json"))):
            with self.assertRaisesRegex(RuntimeError, "JSON válido"):
                triage_lex.clasificar_caso("hola")

    def test_faltan_campos(self):
        incompleto = json.dumps({"materia": "civil"})
        with patch("triage_lex.requests.post", return_value=respuesta_falsa(200, cuerpo_gemini(incompleto))):
            with self.assertRaisesRegex(RuntimeError, "faltan campos"):
                triage_lex.clasificar_caso("hola")

    def test_materia_invalida(self):
        malo = dict(TRIAGE_OK, materia="astrologia")
        with patch("triage_lex.requests.post", return_value=respuesta_falsa(200, cuerpo_gemini(json.dumps(malo)))):
            with self.assertRaisesRegex(RuntimeError, "Materia"):
                triage_lex.clasificar_caso("hola")

    def test_respuesta_sin_candidatos(self):
        with patch("triage_lex.requests.post", return_value=respuesta_falsa(200, {"promptFeedback": {}})):
            with self.assertRaisesRegex(RuntimeError, "texto generado"):
                triage_lex.clasificar_caso("hola")


if __name__ == "__main__":
    unittest.main()
