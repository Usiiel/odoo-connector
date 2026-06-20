"""
Probe script: inspect payroll model fields and sample data.
Run: python E:\Personal\odoo-mcp\probe_nomina.py
"""
import xmlrpc.client
from pathlib import Path

env = {}
with open(Path(__file__).parent / ".env", encoding="utf-8-sig") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()

URL  = env["ODOO_URL"]
DB   = env["ODOO_DB"]
USER = env["ODOO_USERNAME"]
KEY  = env["ODOO_API_KEY"]

common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
uid = common.authenticate(DB, USER, KEY, {})
obj = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")

# --- hr.payslip fields ---
print("=== hr.payslip fields ===")
fields = obj.execute_kw(DB, uid, KEY, "hr.payslip", "fields_get", [],
                        {"attributes": ["string", "type"]})
for fname, info in sorted(fields.items()):
    print(f"  {fname:<35} {info['type']:<12} {info['string']}")

# --- sample payslip ---
print("\n=== sample hr.payslip record ===")
sample = obj.execute_kw(DB, uid, KEY, "hr.payslip", "search_read",
    [[]], {"fields": list(fields.keys()), "limit": 1})
if sample:
    for k, v in sample[0].items():
        print(f"  {k:<35} {str(v)[:60]}")

# --- hr.payslip.line fields ---
print("\n=== hr.payslip.line fields ===")
lfields = obj.execute_kw(DB, uid, KEY, "hr.payslip.line", "fields_get", [],
                         {"attributes": ["string", "type"]})
for fname, info in sorted(lfields.items()):
    print(f"  {fname:<35} {info['type']:<12} {info['string']}")
