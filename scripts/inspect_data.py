import csv

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 – transactions.csv  (first 100 rows)
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 70)
print("SECTION 1: transactions.csv")
print("=" * 70)

TRANSACTIONS_PATH = r"C:\HHGoa\data\transactions.csv"
COLS_OF_INTEREST = [
    "TransactionID", "card1", "card2", "card3", "card4", "card5", "card6",
    "customer_id", "channel",
]

with open(TRANSACTIONS_PATH, newline="", encoding="utf-8") as fh:
    reader = csv.DictReader(fh)

    # --- 1a: Column names ---
    rows = []
    for i, row in enumerate(reader):
        if i == 0:
            print("\n--- 1a: Column Names (header) ---")
            for col in reader.fieldnames:
                print(f"  {col}")

        rows.append(row)
        if i >= 99:          # read first 100 rows (0-indexed)
            break

    # --- 1b: First 5 rows, selected columns ---
    print("\n--- 1b: First 5 rows – selected columns ---")
    present_cols = [c for c in COLS_OF_INTEREST if c in (reader.fieldnames or [])]
    missing_cols = [c for c in COLS_OF_INTEREST if c not in (reader.fieldnames or [])]

    if missing_cols:
        print(f"  [WARNING] These columns were NOT found in the file: {missing_cols}")

    # Header line
    print("  " + " | ".join(present_cols))
    print("  " + "-" * (sum(len(c) for c in present_cols) + 3 * (len(present_cols) - 1)))

    for row in rows[:5]:
        values = [row.get(c, "N/A") for c in present_cols]
        print("  " + " | ".join(values))

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 – closed_cases_history.csv  (first 20 rows)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SECTION 2: closed_cases_history.csv")
print("=" * 70)

CLOSED_CASES_PATH = r"C:\HHGoa\data\closed_cases_history.csv"

with open(CLOSED_CASES_PATH, newline="", encoding="utf-8") as fh:
    reader = csv.DictReader(fh)

    print("\n--- 2a: customer_id and card_id for first 20 rows ---")

    rows_cc = []
    for i, row in enumerate(reader):
        if i >= 20:
            break
        rows_cc.append(row)

    # Warn if expected columns are missing
    for col in ("customer_id", "card_id"):
        if col not in (reader.fieldnames or []):
            print(f"  [WARNING] Column '{col}' NOT found. Available: {reader.fieldnames}")

    print(f"  {'Row':<5} {'customer_id':<30} {'card_id'}")
    print("  " + "-" * 60)
    for i, row in enumerate(rows_cc, start=1):
        cust = row.get("customer_id", "N/A")
        card = row.get("card_id", "N/A")
        print(f"  {i:<5} {cust:<30} {card}")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 – case_pack.csv  (all rows)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SECTION 3: case_pack.csv")
print("=" * 70)

CASE_PACK_PATH = r"C:\HHGoa\data\case_pack.csv"
CASE_COLS = ["case_id", "card_id", "customer_id", "flagged_txn_id"]

with open(CASE_PACK_PATH, newline="", encoding="utf-8") as fh:
    reader = csv.DictReader(fh)

    rows_cp = list(reader)

print(f"\n--- 3a: All {len(rows_cp)} rows – case_id | card_id | customer_id | flagged_txn_id ---")

# Warn about missing columns
for col in CASE_COLS:
    if col not in (reader.fieldnames or []):
        print(f"  [WARNING] Column '{col}' NOT found. Available: {reader.fieldnames}")

header_line = " | ".join(f"{c}" for c in CASE_COLS)
print("  " + header_line)
print("  " + "-" * (len(header_line) + 2))

for row in rows_cp:
    values = [row.get(c, "N/A") for c in CASE_COLS]
    print("  " + " | ".join(values))

print("\n" + "=" * 70)
print("Done.")
print("=" * 70)
