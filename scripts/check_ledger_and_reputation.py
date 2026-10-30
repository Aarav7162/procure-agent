import sqlite3
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

db_path = 'audit/ledger.db'
con = sqlite3.connect(db_path)
tables = [row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables in audit/ledger.db:", tables)

counts = {}
for t in tables:
    counts[t] = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
print("Row counts by table:", counts)

# Run verify_ledger_chain
from orchestrator.treasury import verify_ledger_chain
valid, desc, details = verify_ledger_chain()
print(f"verify_ledger_chain() result: is_valid={valid}, desc='{desc}', details={details}")

with open('audit/latest_chain_hash.txt', 'r', encoding='utf-8') as f:
    anchor = f.read().strip()
print(f"Anchor hash in audit/latest_chain_hash.txt: {anchor}")

# Confirm ledger row hashes
last_row = con.execute("SELECT entry_index, worker_id, amount_usd, tx_hash, prev_hash FROM ledger ORDER BY entry_index DESC LIMIT 1").fetchone()
print(f"Latest ledger row in DB: {last_row}")
con.close()
