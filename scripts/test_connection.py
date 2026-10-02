"""
test_connection.py — Verify live connectivity to TigerGraph Savanna.
Loads credentials from /Users/subratkumarpadhy/CSE/HHGoa/.env.
Never prints the secret value.
"""

import os
import sys
import traceback
from pathlib import Path
from dotenv import load_dotenv

ENV_PATH = Path(__file__).parent.parent / ".env"

load_dotenv(dotenv_path=ENV_PATH)

# ── 1. Validate required environment variables ────────────────────────────────

REQUIRED = ["TG_HOST", "TG_GRAPHNAME", "TG_SECRET"]
missing = [v for v in REQUIRED if not os.environ.get(v)]
if missing:
    print(f"[ERROR] Missing required environment variables: {', '.join(missing)}")
    print("        Copy .env.example to .env and fill in the values.")
    sys.exit(1)

TG_HOST      = os.environ["TG_HOST"]
TG_GRAPHNAME = os.environ["TG_GRAPHNAME"]
TG_SECRET    = os.environ["TG_SECRET"]

# ── 2. Create pyTigerGraph connection ─────────────────────────────────────────

print(f"\nConnecting to {TG_HOST} / graph '{TG_GRAPHNAME}' ...")

from pyTigerGraph import TigerGraphConnection  # pyTigerGraph 2.x renamed TigerGraph → TigerGraphConnection

conn = TigerGraphConnection(
    host=TG_HOST,
    graphname=TG_GRAPHNAME,
    gsqlSecret=TG_SECRET,
)

# ── 3. Run connection tests ───────────────────────────────────────────────────

connection_ok  = False
vertex_count   = "N/A"
edge_count     = "N/A"
tg_version     = "N/A"

try:
    # a. GSQL ls — confirm graph is present
    print("\n[a] Running conn.gsql('ls') ...")
    ls_output = conn.gsql("ls")
    print(ls_output)

    # b. Total vertex count
    print("\n[b] Running conn.getVertexCount('*') ...")
    vertex_count = conn.getVertexCount("*")
    print(f"    Vertex count: {vertex_count}")

    # c. Total edge count
    print("\n[c] Running conn.getEdgeCount('*') ...")
    edge_count = conn.getEdgeCount("*")
    print(f"    Edge count: {edge_count}")

    # d. TigerGraph version
    print("\n[d] Running conn.getVersion() ...")
    tg_version = conn.getVersion()
    print(f"    Version: {tg_version}")

    connection_ok = True

except Exception:
    print("\n[ERROR] An exception occurred during connection tests:")
    traceback.print_exc()

# ── 4. Summary ────────────────────────────────────────────────────────────────

status = "OK  " if connection_ok else "FAIL"
print(f"""
┌──────────────────────────────────┐
│  Connection:  {status}              │
│  Graph:       {TG_GRAPHNAME:<20}  │
│  Vertices:    {str(vertex_count):<20}  │
│  Edges:       {str(edge_count):<20}  │
│  Version:     {str(tg_version):<20}  │
└──────────────────────────────────┘""")

if not connection_ok:
    sys.exit(1)
