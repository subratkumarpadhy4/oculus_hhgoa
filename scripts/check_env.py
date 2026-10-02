"""
check_env.py — Verify that all required environment variables are present.
Loads from /Users/subratkumarpadhy/CSE/HHGoa/.env and reports status.
Never prints the secret value.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

ENV_PATH = Path(__file__).parent.parent / ".env"

load_dotenv(dotenv_path=ENV_PATH)

REQUIRED_VARS = ["TG_HOST", "TG_GRAPHNAME", "TG_SECRET"]

missing = []

for var in REQUIRED_VARS:
    value = os.environ.get(var)
    if var == "TG_SECRET":
        if value:
            print(f"  TG_SECRET      : present (length {len(value)})")
        else:
            print(f"  TG_SECRET      : MISSING")
            missing.append(var)
    else:
        if value:
            safe_preview = value[:8] + "..." if len(value) > 8 else value
            print(f"  {var:<14} : present  (preview: {safe_preview})")
        else:
            print(f"  {var:<14} : MISSING")
            missing.append(var)

if missing:
    print(f"\n[ERROR] Missing required environment variables: {', '.join(missing)}")
    print(f"        Copy .env.example to .env and fill in the values.")
    sys.exit(1)

print("\n[OK] All required environment variables are present.")
