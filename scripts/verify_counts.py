"""
verify_counts.py
----------------
Verifies vertex and edge counts in TigerGraph graph HHGoa.
"""

import os
import pyTigerGraph as tg

ENV_PATH = r"C:\HHGoa\.env"

env = {}
if os.path.exists(ENV_PATH):
    with open(ENV_PATH, encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()

conn = tg.TigerGraphConnection(
    host=env.get("TG_HOST", "http://localhost"),
    graphname=env.get("TG_GRAPHNAME", "HHGoa"),
    username=env.get("TG_USERNAME", "tigergraph"),
    password=env.get("TG_PASSWORD", "tigergraph"),
)

try:
    conn.getToken(conn.createSecret())
except Exception:
    pass

schema = conn.getSchema()
print("=" * 60)
print("TIGERGRAPH HHGoa GRAPH COUNTS")
print("=" * 60)
print("\n--- VERTEX COUNTS ---")
for vt in schema.get("VertexTypes", []):
    vname = vt["Name"]
    try:
        cnt = conn.getVertexCount(vname)
        print(f"  {vname:<25}: {cnt}")
    except Exception as e:
        print(f"  {vname:<25}: Error ({e})")

print("\n--- EDGE COUNTS ---")
for et in schema.get("EdgeTypes", []):
    ename = et["Name"]
    try:
        cnt = conn.getEdgeCount(ename)
        print(f"  {ename:<25}: {cnt}")
    except Exception as e:
        print(f"  {ename:<25}: Error ({e})")
print("=" * 60)