"""
services/payment_analysis_service.py

Analiza imágenes de comprobantes de transferencia bancaria usando Gemini Vision.
Modelo: gemini-2.5-flash-lite (económico, soporta imágenes).
"""
import base64
import json
import logging
import os
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger("application")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = "gemini-2.5-flash-lite"
GEMINI_URL     = (
    f"https://generativelanguage.googleapis.com/v1beta/models"
    f"/{GEMINI_MODEL}:generateContent"
)

_PROMPT = """
Eres un asistente que analiza comprobantes de transferencia bancaria.

Analiza la imagen y extrae ÚNICAMENTE la siguiente información en formato JSON:
{
  "amount":    <monto numérico pagado, o null si no se puede leer>,
  "currency":  <moneda detectada, ej: "USD", "VES", "EUR", null>,
  "reference": <número de referencia/transacción, o null>,
  "bank":      <nombre del banco origen, o null>,
  "date":      <fecha de la transacción en formato YYYY-MM-DD, o null>,
  "recipient": <nombre o cuenta del beneficiario, o null>,
  "is_valid_proof": <true si parece un comprobante bancario real, false si no>
}

Responde ÚNICAMENTE con el JSON, sin texto adicional.
""".strip()


class PaymentAnalysisService:
    """Servicio de análisis de comprobantes de pago via Gemini Vision."""

    def analyze(self, image_path: str) -> dict:
        """
        Analiza un comprobante de pago en imagen.

        Args:
            image_path: Ruta absoluta al archivo de imagen.

        Returns:
            dict con campos: amount, currency, reference, bank, date,
                             recipient, is_valid_proof, raw_response, error
        """
        if not GEMINI_API_KEY:
            logger.error("[PaymentAnalysis] GEMINI_API_KEY no configurada")
            return self._error("GEMINI_API_KEY no está configurada en el servidor")

        # Leer y codificar imagen
        try:
            img_bytes = Path(image_path).read_bytes()
            img_b64   = base64.b64encode(img_bytes).decode("utf-8")
            mime_type = self._detect_mime(image_path)
        except Exception as e:
            logger.error(f"[PaymentAnalysis] Error leyendo imagen: {e}")
            return self._error(f"No se pudo leer la imagen: {e}")

        # Construir payload para Gemini
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": _PROMPT},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": img_b64,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.0,   # Máxima precisión para extracción
                "maxOutputTokens": 512,
            },
        }

        try:
            resp = httpx.post(
                GEMINI_URL,
                params={"key": GEMINI_API_KEY},
                json=payload,
                timeout=30,
            )
        except httpx.RequestError as e:
            logger.error(f"[PaymentAnalysis] Error de red: {e}")
            return self._error(f"Error de conexión con Gemini: {e}")

        if resp.status_code != 200:
            logger.error(f"[PaymentAnalysis] Gemini HTTP {resp.status_code}: {resp.text[:300]}")
            return self._error(f"Gemini respondió HTTP {resp.status_code}")

        # Parsear respuesta
        try:
            raw_text = (
                resp.json()
                ["candidates"][0]["content"]["parts"][0]["text"]
                .strip()
            )
            # Limpiar posible markdown code block
            raw_text = raw_text.strip("`").removeprefix("json").strip()
            analysis = json.loads(raw_text)
            analysis["raw_response"] = raw_text
            analysis["error"] = None
            logger.info(f"[PaymentAnalysis] Análisis OK — monto={analysis.get('amount')} ref={analysis.get('reference')}")
            return analysis
        except Exception as e:
            logger.error(f"[PaymentAnalysis] Error parseando respuesta Gemini: {e} | raw: {resp.text[:200]}")
            return self._error(f"No se pudo parsear la respuesta de Gemini: {e}")

    @staticmethod
    def _detect_mime(path: str) -> str:
        ext = Path(path).suffix.lower()
        return {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }.get(ext, "image/jpeg")

    @staticmethod
    def _error(msg: str) -> dict:
        return {
            "amount":         None,
            "currency":       None,
            "reference":      None,
            "bank":           None,
            "date":           None,
            "recipient":      None,
            "is_valid_proof": False,
            "raw_response":   None,
            "error":          msg,
        }
