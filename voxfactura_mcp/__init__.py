"""voxfactura_mcp : serveur MCP VoxFactura.

Branche ton business VoxFactura sur ton assistant IA (Claude Desktop / Code, ou
tout client MCP). Client léger (httpx) au-dessus de l'API publique
`/api/v1/pub/*` ; le serveur (`server.py`) expose ces données comme des outils
appelables en langage naturel. Lecture, plus des écritures gated qui ne font
jamais d'envoi client.
"""

__version__ = "0.1.0"
