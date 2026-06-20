import xmlrpc.client
from pathlib import Path

env = {}
with open(Path(__file__).parent / ".env", encoding="utf-8-sig") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()

URL, DB, USER, KEY = env["ODOO_URL"], env["ODOO_DB"], env["ODOO_USERNAME"], env["ODOO_API_KEY"]
common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
uid = common.authenticate(DB, USER, KEY, {})
obj = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")

print("=== mailing.trace fields ===")
fields = obj.execute_kw(DB, uid, KEY, "mailing.trace", "fields_get", [],
                        {"attributes": ["string", "type"]})
for fname, info in sorted(fields.items()):
    print(f"  {fname:<40} {info['type']:<12} {info['string']}")

print("\n=== sample mailing.trace record (any status) ===")
sample = obj.execute_kw(DB, uid, KEY, "mailing.trace", "search_read",
    [[]], {"fields": list(fields.keys()), "limit": 1})
if sample:
    for k, v in sample[0].items():
        if v not in (False, None, [], {}):
            print(f"  {k:<40} {str(v)[:80]}")

print("\n=== mailing.trace records opened for mailing ID 11 ===")
# Try just id + trace_status first
try:
    opened = obj.execute_kw(DB, uid, KEY, "mailing.trace", "search_read",
        [[["mass_mailing_id", "=", 11]]],
        {"fields": ["id", "trace_status"], "limit": 5})
    print(f"Found {len(opened)} traces for mailing 11")
    for r in opened:
        print(f"  {r}")
except Exception as e:
    print(f"Error: {e}")
