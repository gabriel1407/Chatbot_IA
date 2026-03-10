"""
tools/payment.py
Herramientas MCP para gestión de pagos:
  - review_payment : Permite aprobar o rechazar un comprobante de pago.
"""

import os
import logging
import httpx
from mcp.server.fastmcp import FastMCP
from middleware.auth import get_auth_headers

logger = logging.getLogger("mcp_server.payment")

APP_BASE_URL = os.getenv("APP_URL", "http://app:8082")

def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def review_payment(proof_id: int, action: str, note: str = "") -> str:
        """
        Aprueba o rechaza un comprobante de pago pendiente.
        
        Args:
            proof_id: El ID del comprobante (ej. 5)
            action: 'approve' para aprobar, o 'reject' para rechazar.
            note: (Opcional) Motivo si se rechaza, o nota adicional.
            
        Returns:
            Resultado de la operación.
        """
        logger.info(f"[review_payment] action={action} proof_id={proof_id} note={note}")
        action = action.lower().strip()
        
        if action not in ("approve", "reject"):
            return "❌ Acción inválida. Usa 'approve' o 'reject'."

        headers = await get_auth_headers()
        if not headers:
            return "❌ No se pudo autenticar. Verifica credenciales."

        endpoint = f"{APP_BASE_URL}/api/subscriptions/proof/{proof_id}/confirm" if action == "approve" else f"{APP_BASE_URL}/api/subscriptions/proof/{proof_id}/reject"
        payload = {"note": note} if note else {}

        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(endpoint, json=payload, headers=headers, timeout=10.0)
                data = r.json()
                if r.status_code == 200:
                    return f"✅ Operación exitosa: {data.get('message', 'OK')}"
                else:
                    return f"❌ Error {r.status_code}: {data.get('error', data)}"
            except Exception as e:
                logger.error(f"[review_payment] HTTP Error: {e}")
                return f"❌ Error de red al contactar servidor: {e}"
