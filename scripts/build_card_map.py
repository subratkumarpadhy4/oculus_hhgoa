"""
build_card_map.py
-----------------
Reads closed_cases_history.csv and case_pack.csv, builds a
customer_id -> card_id dictionary, and writes it to card_id_map.json.

Collision rule: case_pack takes precedence over closed_cases_history
(it is the exam case).
"""

import csv
import json
import os

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR             = r"C:\HHGoa\data"
CLOSED_CASES_PATH    = os.path.join(BASE_DIR, "closed_cases_history.csv")
CASE_PACK_PATH       = os.path.join(BASE_DIR, "case_pack.csv")
OUTPUT_PATH          = os.path.join(BASE_DIR, "card_id_map.json")

# ── Step 1: seed from closed_cases_history ────────────────────────────────────
card_map: dict[str, str] = {}

print("Reading closed_cases_history.csv ...")
with open(CLOSED_CASES_PATH, newline="", encoding="utf-8") as fh:
    reader = csv.DictReader(fh)
    for row in reader:
        cust = row["customer_id"].strip()
        card = row["card_id"].strip()
        if cust and card:
            card_map[cust] = card

print(f"  -> {len(card_map)} entries after closed_cases_history")

# ── Step 2: overlay with case_pack (overrides on collision) ───────────────────
print("Reading case_pack.csv ...")
with open(CASE_PACK_PATH, newline="", encoding="utf-8") as fh:
    reader = csv.DictReader(fh)
    overrides = 0
    additions = 0
    for row in reader:
        cust = row["customer_id"].strip()
        card = row["card_id"].strip()
        if cust and card:
            if cust in card_map and card_map[cust] != card:
                overrides += 1
            elif cust not in card_map:
                additions += 1
            card_map[cust] = card

print(f"  -> {additions} new entries added, {overrides} entries overridden from case_pack")
print(f"  -> Total entries: {len(card_map)}")

# ── Step 3: Save to JSON ──────────────────────────────────────────────────────
with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
    json.dump(card_map, fh, indent=2)

print(f"\nSaved to: {OUTPUT_PATH}")

# ── Step 4: Print first 10 entries ───────────────────────────────────────────
print("\nFirst 10 entries:")
print(f"  {'customer_id':<20} {'card_id'}")
print("  " + "-" * 40)
for i, (cust, card) in enumerate(card_map.items()):
    if i >= 10:
        break
    print(f"  {cust:<20} {card}")
