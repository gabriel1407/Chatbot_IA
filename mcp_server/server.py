"""
MCP Server – Chatbot IA
Entry point: inicializa FastMCP, registra todas las tools y arranca el servidor.
"""

import os
import logging
from mcp.server.fastmcp import FastMCP

from tools.web_search  import register as register_web_search
from tools.read_webpage import register as register_read_webpage
from tools.chatbot     import register as register_chatbot
# Fase 3: tools avanzadas
from tools.rag         import register as register_rag
from tools.tenant      import register as register_tenant
from tools.context     import register as register_context
from tools.payment     import register as register_payment


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger("mcp_server")

# ---------------------------------------------------------------------------
# Configuración de red (leída antes de instanciar FastMCP)
# ---------------------------------------------------------------------------
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8083"))

# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    name="chatbot-ia-tools",
    host=MCP_HOST,
    port=MCP_PORT,
    instructions=(
        "Servidor MCP del proyecto Chatbot IA. "
        "Expone herramientas de búsqueda web, lectura de páginas y "
        "comunicación con el chatbot principal."
    ),
)

# ---------------------------------------------------------------------------
# Registrar tools desde cada módulo
# ---------------------------------------------------------------------------
# Fase 1: tools base
register_web_search(mcp)
register_read_webpage(mcp)
register_chatbot(mcp)
# Fase 3: tools avanzadas
register_rag(mcp)
register_tenant(mcp)
register_context(mcp)
register_payment(mcp)
register_payment(mcp)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info(f"Iniciando MCP Server en {MCP_HOST}:{MCP_PORT} (transporte SSE)")
    mcp.run(transport="sse")


