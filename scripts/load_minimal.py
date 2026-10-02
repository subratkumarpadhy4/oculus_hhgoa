"""
load_minimal.py
---------------
Loads a targeted dataset for the 20 benchmark cases and all historical closed cases
into TigerGraph (graph: HHGoa).

Dataset loaded:
  1. Full 6-month transaction history for the 20 benchmark customers (from case_pack.csv)
  2. Matching device profiles from identity.csv for online transactions
  3. All 5,565 closed cases from closed_cases_history.csv with their associated edges
  4. customer_id -> card_id mapping loaded from card_id_map.json

Vertices upserted:
  Customer, Card, Transaction, EmailDomain, BillingRegion, DeviceProfile, ClosedCase

Edges upserted:
  Customer   -[OWNS]->              Card
  Card       -[MADE]->              Transaction
  Transaction-[FROM_DEVICE]->       DeviceProfile  (online only)
  Transaction-[PURCHASER_EMAIL]->   EmailDomain
  Transaction-[BILLED_IN]->         BillingRegion
  Transaction-[NEXT]->              Transaction    (chain per card, sorted by ts)
  ClosedCase -[INVOLVES_TXN]->      Transaction
  ClosedCase -[ON_CARD]->           Card
  ClosedCase -[CONNECTED_TO]->      Card
  ClosedCase -[INVOLVES_CUSTOMER]-> Customer

Requires: csv, json, os, hashlib, pyTigerGraph (no pandas)
"""

import csv
import hashlib
import json
import os
import traceback
from collections import defaultdict

import pyTigerGraph as tg

# ── 1. Paths ──────────────────────────────────────────────────────────────────
BASE_DIR         = r"C:\HHGoa\data"
ENV_PATH         = r"C:\HHGoa\.env"
CARD_MAP_PATH    = os.path.join(BASE_DIR, "card_id_map.json")
CASE_PACK_CSV    = os.path.join(BASE_DIR, "case_pack.csv")
TRANSACTIONS_CSV = os.path.join(BASE_DIR, "transactions.csv")
IDENTITY_CSV     = os.path.join(BASE_DIR, "identity.csv")
CLOSED_CASES_CSV = os.path.join(BASE_DIR, "closed_cases_history.csv")

# ── 2. Type-safe coercion helpers ─────────────────────────────────────────────
def to_double(val: str, default: float = 0.0) -> float:
    """Return float; fall back to default for empty / non-numeric strings."""
    v = val.strip()
    try:
        return float(v) if v else default
    except ValueError:
        return default

def to_int(val: str, default: int = 0) -> int:
    v = val.strip()
    try:
        return int(float(v)) if v else default
    except ValueError:
        return default

def to_bool(val: str) -> bool:
    v = val.strip().lower()
    return v in ("yes", "true", "1", "t")

# ── 3. Load .env (BOM-safe) ───────────────────────────────────────────────────
print("Loading .env ...")
env = {}
with open(ENV_PATH, encoding="utf-8-sig") as fh:
    for line in fh:
        line = line.strip()
        if line and "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()

TG_HOST      = env["TG_HOST"]
TG_GRAPHNAME = env["TG_GRAPHNAME"]
TG_USERNAME  = env["TG_USERNAME"]
TG_PASSWORD  = env["TG_PASSWORD"]
print(f"  host={TG_HOST}  graph={TG_GRAPHNAME}  user={TG_USERNAME}")

# ── 4. Load card_id_map.json ──────────────────────────────────────────────────
print(f"Loading card_id_map.json ...")
with open(CARD_MAP_PATH, encoding="utf-8") as fh:
    card_map: dict = json.load(fh)
print(f"  {len(card_map)} entries in card map")

# ── 5. Connect to TigerGraph ──────────────────────────────────────────────────
print("Connecting to TigerGraph ...")
conn = tg.TigerGraphConnection(
    host=TG_HOST,
    graphname=TG_GRAPHNAME,
    username=TG_USERNAME,
    password=TG_PASSWORD,
)
try:
    conn.getToken(conn.createSecret())
    print("  Connected and token acquired.")
except Exception as e:
    print(f"  WARNING: Token acquisition failed ({e}). Continuing without token ...")

# ── 6. Clear existing graph data (keep schema intact) ────────────────────────
print("\nClearing graph store (CLEAR GRAPH STORE -HARD) ...")
try:
    result = conn.gsql(f"USE GRAPH {TG_GRAPHNAME}\nCLEAR GRAPH STORE -HARD")
    print(f"  Graph cleared. Response: {result.splitlines()[-1] if result else 'OK'}")
except Exception as e:
    print(f"  WARNING: Could not clear graph store ({e}). Proceeding anyway ...")

# ── 7. Read benchmark cases from case_pack.csv ────────────────────────────────
print("\nReading benchmark cases from case_pack.csv ...")
benchmark_customers = set()
benchmark_cards = set()
benchmark_flagged_txns = set()

with open(CASE_PACK_CSV, newline="", encoding="utf-8") as fh:
    reader = csv.DictReader(fh)
    for row in reader:
        c_id = row["customer_id"].strip()
        card = row["card_id"].strip()
        f_txn = row["flagged_txn_id"].strip()
        if c_id:
            benchmark_customers.add(c_id)
        if card:
            benchmark_cards.add(card)
        if f_txn:
            benchmark_flagged_txns.add(f_txn)

print(f"  Found {len(benchmark_customers)} benchmark customers, {len(benchmark_cards)} cards, {len(benchmark_flagged_txns)} flagged txns")

# ── 8. Load identity CSV into a lookup dict keyed by TransactionID ────────────
print("\nLoading identity.csv ...")
identity_map: dict[str, dict] = {}
with open(IDENTITY_CSV, newline="", encoding="utf-8") as fh:
    reader = csv.DictReader(fh)
    for row in reader:
        identity_map[row["TransactionID"].strip()] = row
print(f"  {len(identity_map)} identity rows loaded")

# Deterministic device_id via MD5
def make_device_id(device_info: str, os_: str, browser: str, screen: str) -> str:
    raw = f"{device_info}|{os_}|{browser}|{screen}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

# ── 9. Read matching transactions for the 20 benchmark customers ──────────────
print("\nFiltering transactions.csv for the 20 benchmark customers ...")
benchmark_txn_rows = []
with open(TRANSACTIONS_CSV, newline="", encoding="utf-8") as fh:
    reader = csv.DictReader(fh)
    for row in reader:
        if row["customer_id"].strip() in benchmark_customers:
            benchmark_txn_rows.append(row)
print(f"  {len(benchmark_txn_rows)} matching transactions found")

# ── 10. Entity accumulators & batch lists ─────────────────────────────────────
customers_seen:     dict[str, dict] = {}
cards_seen:         dict[str, dict] = {}
transactions_seen:  dict[str, dict] = {}
email_domains_seen: dict[str, dict] = {}
billing_seen:       dict[str, dict] = {}
devices_seen:       dict[str, dict] = {}
closed_cases_seen:  dict[str, dict] = {}

edge_pairs: dict[str, set] = {
    "OWNS":              set(),
    "MADE":              set(),
    "FROM_DEVICE":       set(),
    "PURCHASER_EMAIL":   set(),
    "BILLED_IN":         set(),
    "NEXT":              set(),
    "INVOLVES_TXN":      set(),
    "ON_CARD":           set(),
    "CONNECTED_TO":      set(),
    "INVOLVES_CUSTOMER": set(),
}

# For NEXT edges: accumulate (ts, txn_id) per card then sort
card_txn_timeline: dict[str, list] = defaultdict(list)

# ── 11. Process Benchmark Transactions ────────────────────────────────────────
print("\nProcessing transactions and building graph entities ...")
for row in benchmark_txn_rows:
    txn_id         = row["TransactionID"].strip()
    customer_id    = row["customer_id"].strip()
    transaction_dt = to_int(row["TransactionDT"])
    amount         = to_double(row["TransactionAmt"])
    product_cd     = row["ProductCD"].strip()
    channel        = row["channel"].strip()
    ts_str         = row["ts"].strip()          # "YYYY-MM-DD HH:MM:SS"
    risk_score     = to_double(row["risk_score"])

    addr1          = row["addr1"].strip()
    addr2          = row["addr2"].strip()
    p_email        = row["P_emaildomain"].strip()
    r_email        = row["R_emaildomain"].strip()
    dist1          = to_double(row["dist1"])
    dist2          = to_double(row["dist2"])

    card1 = row["card1"].strip()
    card2 = row["card2"].strip()
    card3 = row["card3"].strip()
    card4 = row["card4"].strip()   # network, e.g. "mastercard"
    card5 = row["card5"].strip()
    card6 = row["card6"].strip()   # type, e.g. "credit"

    # card_id lookup
    card_id = card_map.get(customer_id, customer_id + "-K1")

    # Customer
    if customer_id not in customers_seen:
        customers_seen[customer_id] = {"card_count": 1}

    # Card
    if card_id not in cards_seen:
        cards_seen[card_id] = {
            "customer_id":  customer_id,
            "card1":        card1,
            "card2":        card2,
            "card3":        card3,
            "card4":        card4,
            "card5":        card5,
            "card6":        card6,
            "card_network": card4,
            "card_type":    card6,
        }

    # Transaction
    transactions_seen[txn_id] = {
        "transaction_dt": transaction_dt,
        "ts":             ts_str,
        "amount":         amount,
        "product_cd":     product_cd,
        "channel":        channel,
        "risk_score":     risk_score,
        "addr1":          addr1,
        "addr2":          addr2,
        "p_emaildomain":  p_email,
        "r_emaildomain":  r_email,
        "dist1":          dist1,
        "dist2":          dist2,
    }
    card_txn_timeline[card_id].append((ts_str, txn_id))

    # Edges: Customer -[OWNS]-> Card, Card -[MADE]-> Transaction
    edge_pairs["OWNS"].add((customer_id, card_id))
    edge_pairs["MADE"].add((card_id, txn_id))

    # EmailDomain
    for domain in (p_email, r_email):
        if domain:
            if domain not in email_domains_seen:
                email_domains_seen[domain] = {}
            edge_pairs["PURCHASER_EMAIL"].add((txn_id, domain))

    # BillingRegion
    if addr1:
        if addr1 not in billing_seen:
            billing_seen[addr1] = {"country_code": addr2}
        edge_pairs["BILLED_IN"].add((txn_id, addr1))

    # DeviceProfile (online only)
    if channel == "online" and txn_id in identity_map:
        id_row      = identity_map[txn_id]
        device_info = id_row.get("DeviceInfo", "")
        os_         = id_row.get("id_30", "")
        browser     = id_row.get("id_31", "")
        screen      = id_row.get("id_33", "")
        device_type = id_row.get("DeviceType", "")
        id_15       = id_row.get("id_15", "")
        id_23       = id_row.get("id_23", "")

        device_id = make_device_id(device_info, os_, browser, screen)

        if device_id not in devices_seen:
            devices_seen[device_id] = {
                "device_info":        device_info,
                "os":                 os_,
                "browser":            browser,
                "screen":             screen,
                "device_type":        device_type,
                "is_new_for_account": (id_15 == "New"),
                "proxy_type":         id_23,
            }

        edge_pairs["FROM_DEVICE"].add((txn_id, device_id))

# NEXT edges (sort per card by ts, then chain)
for card_id, entries in card_txn_timeline.items():
    if len(entries) < 2:
        continue
    sorted_entries = sorted(entries, key=lambda x: x[0])
    for i in range(len(sorted_entries) - 1):
        src_txn = sorted_entries[i][1]
        tgt_txn = sorted_entries[i + 1][1]
        edge_pairs["NEXT"].add((src_txn, tgt_txn))

# ── 12. Process Closed Cases History (5,565 cases) ────────────────────────────
print("\nProcessing closed_cases_history.csv ...")
with open(CLOSED_CASES_CSV, newline="", encoding="utf-8") as fh:
    reader = csv.DictReader(fh)
    for row in reader:
        case_id            = row["case_id"].strip()
        customer_id        = row["customer_id"].strip()
        card_id            = row["card_id"].strip()
        opened_at          = row["opened_at"].strip()
        closed_at          = row["closed_at"].strip()
        outcome            = row["outcome"].strip()
        pattern            = row["pattern"].strip()
        first_fraud_txn_id = row["first_fraud_txn_id"].strip()
        txn_ids_raw        = row["txn_ids"].strip()
        n_txns             = to_int(row["n_txns"])
        exposure_usd       = to_double(row["exposure_usd"])
        connected_cards    = row["connected_card_ids"].strip()
        actions_taken      = row["actions_taken"].strip()
        report_filed       = to_bool(row["report_filed"])
        analyst_notes      = row["analyst_notes"].strip()

        closed_cases_seen[case_id] = {
            "customer_id":        customer_id,
            "card_id":            card_id,
            "opened_at":          opened_at,
            "closed_at":          closed_at,
            "outcome":            outcome,
            "pattern":            pattern,
            "first_fraud_txn_id": first_fraud_txn_id,
            "n_txns":             n_txns,
            "exposure_usd":       exposure_usd,
            "actions_taken":      actions_taken,
            "report_filed":       report_filed,
            "analyst_notes":      analyst_notes,
        }

        # Customer vertex placeholder if not yet seen
        if customer_id and customer_id not in customers_seen:
            customers_seen[customer_id] = {"card_count": 1}

        # Card vertex placeholder if not yet seen
        if card_id and card_id not in cards_seen:
            cards_seen[card_id] = {
                "customer_id":  customer_id,
                "card1":        "",
                "card2":        "",
                "card3":        "",
                "card4":        "",
                "card5":        "",
                "card6":        "",
                "card_network": "",
                "card_type":    "",
            }

        # Edge: INVOLVES_CUSTOMER
        if customer_id:
            edge_pairs["INVOLVES_CUSTOMER"].add((case_id, customer_id))

        # Edge: ON_CARD
        if card_id:
            edge_pairs["ON_CARD"].add((case_id, card_id))

        # Edge: CONNECTED_TO
        if connected_cards:
            for c_card in connected_cards.split("|"):
                c_card = c_card.strip()
                if c_card:
                    if c_card not in cards_seen:
                        cards_seen[c_card] = {
                            "customer_id":  "",
                            "card1":        "",
                            "card2":        "",
                            "card3":        "",
                            "card4":        "",
                            "card5":        "",
                            "card6":        "",
                            "card_network": "",
                            "card_type":    "",
                        }
                    edge_pairs["CONNECTED_TO"].add((case_id, c_card))

        # Edge: INVOLVES_TXN
        if txn_ids_raw:
            for t_id in txn_ids_raw.split("|"):
                t_id = t_id.strip()
                if t_id:
                    edge_pairs["INVOLVES_TXN"].add((case_id, t_id))

# ── 13. Batch Upsert Helpers ──────────────────────────────────────────────────
def batch_upsert_vertices(tg_conn, vertex_type: str, vertex_dict: dict, batch_size: int = 2000):
    items = list(vertex_dict.items())
    total = len(items)
    if total == 0:
        return
    print(f"  Upserting {total} {vertex_type} vertices in batches of {batch_size} ...")
    for i in range(0, total, batch_size):
        chunk = items[i : i + batch_size]
        tg_conn.upsertVertices(vertex_type, chunk)

def batch_upsert_edges(tg_conn, src_type: str, edge_type: str, tgt_type: str, edge_set: set, batch_size: int = 5000):
    items = list(edge_set)
    total = len(items)
    if total == 0:
        return
    print(f"  Upserting {total} {edge_type} edges ({src_type} -> {tgt_type}) in batches of {batch_size} ...")
    for i in range(0, total, batch_size):
        chunk = items[i : i + batch_size]
        tg_conn.upsertEdges(src_type, edge_type, tgt_type, chunk)

# ── 14. Perform Upserts ───────────────────────────────────────────────────────
try:
    print("\n" + "=" * 60)
    print("STARTING GRAPH UPSERTS")
    print("=" * 60)

    # Vertices
    batch_upsert_vertices(conn, "Customer",      customers_seen)
    batch_upsert_vertices(conn, "Card",          cards_seen)
    batch_upsert_vertices(conn, "Transaction",   transactions_seen)
    batch_upsert_vertices(conn, "EmailDomain",   email_domains_seen)
    batch_upsert_vertices(conn, "BillingRegion", billing_seen)
    batch_upsert_vertices(conn, "DeviceProfile", devices_seen)
    batch_upsert_vertices(conn, "ClosedCase",    closed_cases_seen)

    print()
    # Edges
    batch_upsert_edges(conn, "Customer",   "OWNS",              "Card",          edge_pairs["OWNS"])
    batch_upsert_edges(conn, "Card",       "MADE",              "Transaction",   edge_pairs["MADE"])
    batch_upsert_edges(conn, "Transaction","FROM_DEVICE",       "DeviceProfile", edge_pairs["FROM_DEVICE"])
    batch_upsert_edges(conn, "Transaction","PURCHASER_EMAIL",   "EmailDomain",   edge_pairs["PURCHASER_EMAIL"])
    batch_upsert_edges(conn, "Transaction","BILLED_IN",         "BillingRegion", edge_pairs["BILLED_IN"])
    batch_upsert_edges(conn, "Transaction","NEXT",              "Transaction",   edge_pairs["NEXT"])
    batch_upsert_edges(conn, "ClosedCase", "INVOLVES_TXN",      "Transaction",   edge_pairs["INVOLVES_TXN"])
    batch_upsert_edges(conn, "ClosedCase", "ON_CARD",           "Card",          edge_pairs["ON_CARD"])
    batch_upsert_edges(conn, "ClosedCase", "CONNECTED_TO",      "Card",          edge_pairs["CONNECTED_TO"])
    batch_upsert_edges(conn, "ClosedCase", "INVOLVES_CUSTOMER", "Customer",      edge_pairs["INVOLVES_CUSTOMER"])

except Exception:
    print("\n[ERROR] Exception during upsert:")
    traceback.print_exc()

# ── 15. Final Summary ─────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("LOAD SUMMARY")
print("=" * 60)
print(f"  Total customers      : {len(customers_seen)}")
print(f"  Total cards          : {len(cards_seen)}")
print(f"  Total transactions   : {len(transactions_seen)}")
print(f"  Total closed cases   : {len(closed_cases_seen)}")
print(f"  Total devices        : {len(devices_seen)}")
print(f"  Total email domains  : {len(email_domains_seen)}")
print(f"  Total billing regions: {len(billing_seen)}")
print()
for edge_type, pairs in edge_pairs.items():
    print(f"  {edge_type:<20} edges: {len(pairs)}")
print("=" * 60)
print("Done.")
