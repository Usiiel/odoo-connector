"""
Odoo MCP Server - Claude connector for Odoo Online & Community
Modules: CRM, Sales, Expenses, Bank Reconciliation

Configuration via environment variables or interactive setup wizard:
  ODOO_URL      -> https://yourcompany.odoo.com
  ODOO_DB       -> database name (subdomain for SaaS)
  ODOO_USERNAME -> your Odoo login email
  ODOO_API_KEY  -> API key from Odoo > Preferences > Security

Run 'odoo_setup' tool if credentials are not configured yet.
"""

import os
import json
import sys
import traceback
print("[MCP-ODOO] server.py loading...", file=sys.stderr, flush=True)
from pathlib import Path
from datetime import datetime, timedelta

try:
    from dotenv import load_dotenv, set_key
except ImportError:
    def load_dotenv(**kwargs): pass
    def set_key(path, key, val): pass

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    raise

from odoo_client import OdooClient

ENV_PATH = Path(__file__).parent / ".env"
try:
    load_dotenv(dotenv_path=ENV_PATH)
except Exception as e:
    print(f"[WARN] dotenv load failed: {e}", file=sys.stderr)

try:
    mcp = FastMCP("Odoo MCP")
except Exception as e:
    print(f"[FATAL] FastMCP init failed: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _credentials_missing() -> bool:
    return not all([
        os.environ.get("ODOO_URL"),
        os.environ.get("ODOO_DB"),
        os.environ.get("ODOO_USERNAME"),
        os.environ.get("ODOO_API_KEY"),
    ])


def get_client():
    if _credentials_missing():
        return None
    return OdooClient(
        os.environ["ODOO_URL"],
        os.environ["ODOO_DB"],
        os.environ["ODOO_USERNAME"],
        os.environ["ODOO_API_KEY"],
    )


def _not_configured_msg() -> str:
    return (
        "[!] Odoo connector is not configured yet.\n"
        "Run the 'odoo_setup' tool and I will guide you through it step by step."
    )


# ---------------------------------------------------------------------------
#  SETUP WIZARD
# ---------------------------------------------------------------------------

@mcp.tool()
def odoo_setup(
    url: str = "",
    db: str = "",
    username: str = "",
    api_key: str = ""
) -> str:
    """
    Configure the Odoo connector. Provide all four parameters to connect.

    Args:
        url: Your Odoo URL, e.g. https://mycompany.odoo.com
        db: Database name (subdomain for SaaS, e.g. 'mycompany')
        username: Your Odoo login email
        api_key: API key from Odoo > Preferences > Security > API Keys
    """
    if not all([url, db, username, api_key]):
        configured = all([
            os.environ.get("ODOO_URL"),
            os.environ.get("ODOO_DB"),
            os.environ.get("ODOO_USERNAME"),
            os.environ.get("ODOO_API_KEY"),
        ])
        if configured:
            return (
                "[OK] Odoo is already configured.\n"
                f"URL: {os.environ.get('ODOO_URL')}\n"
                f"DB:  {os.environ.get('ODOO_DB')}\n"
                f"User:{os.environ.get('ODOO_USERNAME')}\n\n"
                "To reconfigure, call odoo_setup with all four parameters:\n"
                "  url, db, username, api_key"
            )
        return (
            "[!] Odoo connector is not configured yet.\n\n"
            "Call odoo_setup with these four parameters:\n"
            "  url      -> https://mycompany.odoo.com\n"
            "  db       -> mycompany (the subdomain)\n"
            "  username -> you@company.com\n"
            "  api_key  -> generate at Odoo > Preferences > Security > API Keys\n\n"
            "Example:\n"
            "  odoo_setup(url='https://mycompany.odoo.com', db='mycompany', "
            "username='me@company.com', api_key='abc123')"
        )

    url = url.strip().rstrip("/")
    db = db.strip()
    username = username.strip()
    api_key = api_key.strip()

    try:
        client = OdooClient(url, db, username, api_key)
        version = client.get_server_version()
        uid = client.authenticate()
    except Exception as e:
        return (
            f"[!] Connection failed: {e}\n"
            "Please check your credentials and try again."
        )

    ENV_PATH.touch(exist_ok=True)
    try:
        set_key(str(ENV_PATH), "ODOO_URL", url)
        set_key(str(ENV_PATH), "ODOO_DB", db)
        set_key(str(ENV_PATH), "ODOO_USERNAME", username)
        set_key(str(ENV_PATH), "ODOO_API_KEY", api_key)
    except Exception:
        pass  # env file write failed, still set in-process vars

    os.environ["ODOO_URL"] = url
    os.environ["ODOO_DB"] = db
    os.environ["ODOO_USERNAME"] = username
    os.environ["ODOO_API_KEY"] = api_key

    server_ver = version.get("server_version", "N/A")
    return (
        f"[OK] Connected to Odoo successfully!\n"
        f"URL:     {url}\n"
        f"DB:      {db}\n"
        f"User:    {username} (UID: {uid})\n"
        f"Version: {server_ver}\n\n"
        "Credentials saved. You can now use all Odoo tools."
    )


# ---------------------------------------------------------------------------
#  PING / DIAGNOSTICS
# ---------------------------------------------------------------------------

@mcp.tool()
def odoo_ping() -> str:
    """Verify the Odoo connection and return server version and user ID."""
    client = get_client()
    if client is None:
        return _not_configured_msg()
    version = client.get_server_version()
    uid = client.authenticate()
    return (
        f"[OK] Connected to Odoo\n"
        f"Version: {version.get('server_version', 'N/A')}\n"
        f"User UID: {uid}"
    )


# ---------------------------------------------------------------------------
#  CRM
# ---------------------------------------------------------------------------

@mcp.tool()
def crm_listar_oportunidades(
    estado: str = "open",
    limite: int = 15,
    buscar: str = ""
) -> str:
    """
    List CRM opportunities / leads.

    Args:
        estado: 'open' (active), 'won', 'lost', 'all'
        limite: max results (default 15)
        buscar: filter by lead name or customer
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    domain: list = []
    if estado == "open":
        domain.append(("stage_id.is_won", "=", False))
        domain.append(("active", "=", True))
    elif estado == "won":
        domain.append(("stage_id.is_won", "=", True))
    elif estado == "lost":
        domain.append(("active", "=", False))
    if buscar:
        domain.append("|")
        domain.append(("name", "ilike", buscar))
        domain.append(("partner_name", "ilike", buscar))
    fields = ["name", "partner_name", "expected_revenue", "stage_id",
              "user_id", "date_deadline", "probability"]
    leads = client.search_read("crm.lead", domain, fields, limit=limite, order="expected_revenue desc")
    if not leads:
        return "No opportunities found with those filters."
    lines = [f"{'#':<4} {'Opportunity':<30} {'Customer':<25} {'Stage':<20} {'Est. Value':<12} {'Prob%':<7} {'Deadline'}"]
    lines.append("-" * 110)
    for l in leads:
        lines.append(
            f"{l['id']:<4} "
            f"{str(l['name'])[:29]:<30} "
            f"{str(l.get('partner_name') or '')[:24]:<25} "
            f"{str(l['stage_id'][1] if l.get('stage_id') else '')[:19]:<20} "
            f"${l.get('expected_revenue', 0):>10,.0f} "
            f"{l.get('probability', 0):>5.0f}% "
            f"{l.get('date_deadline') or 'No date'}"
        )
    return "\n".join(lines)


@mcp.tool()
def crm_crear_oportunidad(
    nombre: str,
    cliente: str = "",
    valor_esperado: float = 0,
    fecha_cierre: str = "",
    vendedor_email: str = "",
    notas: str = ""
) -> str:
    """
    Create a new CRM opportunity.

    Args:
        nombre: opportunity title (required)
        cliente: customer/company name
        valor_esperado: expected sale amount
        fecha_cierre: deadline in YYYY-MM-DD
        vendedor_email: assigned salesperson email
        notas: internal description
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    values: dict = {"name": nombre, "type": "opportunity"}
    if cliente:
        values["partner_name"] = cliente
    if valor_esperado:
        values["expected_revenue"] = valor_esperado
    if fecha_cierre:
        values["date_deadline"] = fecha_cierre
    if notas:
        values["description"] = notas
    if vendedor_email:
        users = client.search_read("res.users", [("login", "=", vendedor_email)], ["id", "name"], limit=1)
        if users:
            values["user_id"] = users[0]["id"]
    lead_id = client.create("crm.lead", values)
    return f"[OK] Opportunity created with ID {lead_id}: '{nombre}'"


@mcp.tool()
def crm_actualizar_etapa(oportunidad_id: int, etapa_nombre: str) -> str:
    """
    Move an opportunity to a different pipeline stage.

    Args:
        oportunidad_id: opportunity ID
        etapa_nombre: partial name of the target stage
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    stages = client.search_read("crm.stage", [("name", "ilike", etapa_nombre)], ["id", "name"], limit=5)
    if not stages:
        return f"[!] No stage found with name '{etapa_nombre}'."
    stage = stages[0]
    client.write("crm.lead", [oportunidad_id], {"stage_id": stage["id"]})
    return f"[OK] Opportunity {oportunidad_id} moved to stage '{stage['name']}'"


@mcp.tool()
def crm_resumen_pipeline() -> str:
    """Show a CRM pipeline summary grouped by stage with totals."""
    client = get_client()
    if client is None:
        return _not_configured_msg()
    leads = client.search_read(
        "crm.lead",
        [("active", "=", True), ("stage_id.is_won", "=", False), ("type", "=", "opportunity")],
        ["stage_id", "expected_revenue", "probability"],
        limit=500
    )
    pipeline: dict = {}
    for l in leads:
        stage = l["stage_id"][1] if l.get("stage_id") else "No stage"
        if stage not in pipeline:
            pipeline[stage] = {"count": 0, "total": 0, "weighted": 0}
        pipeline[stage]["count"] += 1
        pipeline[stage]["total"] += l.get("expected_revenue", 0)
        pipeline[stage]["weighted"] += l.get("expected_revenue", 0) * l.get("probability", 0) / 100
    lines = [f"{'Stage':<28} {'Opps':>5} {'Total Value':>14} {'Weighted Value':>16}"]
    lines.append("-" * 68)
    grand_total = grand_weighted = grand_count = 0
    for stage, data in pipeline.items():
        lines.append(
            f"{stage[:27]:<28} {data['count']:>5} "
            f"${data['total']:>13,.0f} ${data['weighted']:>15,.0f}"
        )
        grand_total += data["total"]
        grand_weighted += data["weighted"]
        grand_count += data["count"]
    lines.append("-" * 68)
    lines.append(f"{'TOTAL':<28} {grand_count:>5} ${grand_total:>13,.0f} ${grand_weighted:>15,.0f}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
#  SALES
# ---------------------------------------------------------------------------

@mcp.tool()
def ventas_listar_ordenes(
    estado: str = "sale",
    limite: int = 15,
    dias: int = 30,
    buscar: str = ""
) -> str:
    """
    List sales orders.

    Args:
        estado: 'draft' (quotation), 'sale' (confirmed), 'done' (invoiced), 'cancel', 'all'
        limite: max results
        dias: filter orders from the last N days (0 = no filter)
        buscar: filter by customer name or order number
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    domain: list = []
    if estado != "all":
        domain.append(("state", "=", estado))
    if dias > 0:
        fecha_desde = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
        domain.append(("date_order", ">=", fecha_desde))
    if buscar:
        domain.append("|")
        domain.append(("name", "ilike", buscar))
        domain.append(("partner_id.name", "ilike", buscar))
    fields = ["name", "partner_id", "amount_total", "state", "date_order",
              "user_id", "invoice_status"]
    orders = client.search_read("sale.order", domain, fields, limit=limite, order="date_order desc")
    if not orders:
        return "No sales orders found."
    estado_map = {"draft": "Quotation", "sent": "Sent", "sale": "Confirmed",
                  "done": "Invoiced", "cancel": "Cancelled"}
    lines = [f"{'Order':<12} {'Customer':<28} {'Total':>12} {'Status':<12} {'Invoice':<12} {'Date'}"]
    lines.append("-" * 90)
    for o in orders:
        lines.append(
            f"{o['name']:<12} "
            f"{str(o['partner_id'][1] if o.get('partner_id') else '')[:27]:<28} "
            f"${o.get('amount_total', 0):>11,.2f} "
            f"{estado_map.get(o['state'], o['state']):<12} "
            f"{o.get('invoice_status', ''):<12} "
            f"{str(o.get('date_order', ''))[:10]}"
        )
    return "\n".join(lines)


@mcp.tool()
def ventas_detalle_orden(orden_id: int) -> str:
    """
    Get full details of a sales order including product lines.

    Args:
        orden_id: numeric sales order ID
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    orders = client.read("sale.order", [orden_id],
        ["name", "partner_id", "amount_untaxed", "amount_tax", "amount_total",
         "state", "date_order", "user_id", "order_line", "note", "invoice_status"])
    if not orders:
        return f"Order {orden_id} not found."
    o = orders[0]
    lines_data = client.read("sale.order.line", o["order_line"],
        ["product_id", "product_uom_qty", "price_unit", "price_subtotal", "name"])
    output = [
        f"Order:    {o['name']}",
        f"Customer: {o['partner_id'][1] if o.get('partner_id') else 'N/A'}",
        f"Date:     {str(o.get('date_order', ''))[:16]}",
        f"Status:   {o.get('state', '')} | Invoicing: {o.get('invoice_status', '')}",
        f"Salesperson: {o['user_id'][1] if o.get('user_id') else 'N/A'}",
        "",
        f"{'Product':<35} {'Qty':>6} {'Price':>12} {'Subtotal':>12}",
        "-" * 68,
    ]
    for line in lines_data:
        output.append(
            f"{str(line.get('name') or (line['product_id'][1] if line.get('product_id') else ''))[:34]:<35} "
            f"{line.get('product_uom_qty', 0):>6.1f} "
            f"${line.get('price_unit', 0):>11,.2f} "
            f"${line.get('price_subtotal', 0):>11,.2f}"
        )
    output.extend([
        "-" * 68,
        f"{'Subtotal':>56} ${o.get('amount_untaxed', 0):>11,.2f}",
        f"{'Taxes':>56} ${o.get('amount_tax', 0):>11,.2f}",
        f"{'TOTAL':>56} ${o.get('amount_total', 0):>11,.2f}",
    ])
    if o.get("note"):
        output += ["", f"Note: {o['note']}"]
    return "\n".join(output)


@mcp.tool()
def ventas_resumen_mes(anio: int = 0, mes: int = 0) -> str:
    """
    Monthly sales summary for confirmed orders, grouped by salesperson.

    Args:
        anio: year (e.g. 2025), 0 = current year
        mes: month 1-12, 0 = current month
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    now = datetime.now()
    anio = anio or now.year
    mes = mes or now.month
    fecha_inicio = f"{anio}-{mes:02d}-01"
    if mes == 12:
        fecha_fin = f"{anio + 1}-01-01"
    else:
        fecha_fin = f"{anio}-{mes + 1:02d}-01"
    orders = client.search_read(
        "sale.order",
        [("state", "in", ["sale", "done"]),
         ("date_order", ">=", fecha_inicio),
         ("date_order", "<", fecha_fin)],
        ["name", "partner_id", "amount_total", "user_id"],
        limit=500
    )
    total = sum(o["amount_total"] for o in orders)
    by_vendor: dict = {}
    vendor_counts: dict = {}
    for o in orders:
        v = o["user_id"][1] if o.get("user_id") else "Unassigned"
        by_vendor[v] = by_vendor.get(v, 0) + o["amount_total"]
        vendor_counts[v] = vendor_counts.get(v, 0) + 1
    lines = [
        f"Sales Summary - {mes:02d}/{anio}",
        f"Total orders: {len(orders)}  |  Total revenue: ${total:,.2f}",
        "",
        f"{'Salesperson':<30} {'Orders':>8} {'Total':>14}",
        "-" * 55,
    ]
    for v, total_v in sorted(by_vendor.items(), key=lambda x: -x[1]):
        lines.append(f"{v[:29]:<30} {vendor_counts[v]:>8} ${total_v:>13,.2f}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
#  EXPENSES
# ---------------------------------------------------------------------------

@mcp.tool()
def gastos_listar(
    estado: str = "draft",
    empleado: str = "",
    limite: int = 20
) -> str:
    """
    List employee expenses.

    Args:
        estado: 'draft', 'reported', 'approved', 'done' (paid), 'refused', 'all'
        empleado: filter by employee name (partial)
        limite: max results
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    domain: list = []
    if estado != "all":
        domain.append(("state", "=", estado))
    if empleado:
        domain.append(("employee_id.name", "ilike", empleado))
    fields = ["name", "employee_id", "total_amount", "state", "date", "product_id"]
    expenses = client.search_read("hr.expense", domain, fields, limit=limite, order="date desc")
    if not expenses:
        return "No expenses found with those filters."
    estado_map = {
        "draft": "Draft", "reported": "Reported", "approved": "Approved",
        "done": "Paid", "refused": "Refused"
    }
    lines = [f"{'ID':<6} {'Description':<30} {'Employee':<22} {'Amount':>10} {'Status':<12} {'Date'}"]
    lines.append("-" * 95)
    for e in expenses:
        lines.append(
            f"{e['id']:<6} "
            f"{str(e.get('name', ''))[:29]:<30} "
            f"{str(e['employee_id'][1] if e.get('employee_id') else '')[:21]:<22} "
            f"${e.get('total_amount', 0):>9,.2f} "
            f"{estado_map.get(e['state'], e['state']):<12} "
            f"{e.get('date', '')}"
        )
    return "\n".join(lines)


@mcp.tool()
def gastos_crear(
    descripcion: str,
    monto: float,
    empleado_nombre: str,
    fecha: str = "",
    categoria: str = ""
) -> str:
    """
    Register a new expense.

    Args:
        descripcion: expense description
        monto: total amount
        empleado_nombre: employee name (must exist in Odoo)
        fecha: date in YYYY-MM-DD (default: today)
        categoria: expense product/category name
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    employees = client.search_read("hr.employee", [("name", "ilike", empleado_nombre)], ["id", "name"], limit=3)
    if not employees:
        return f"[!] No employee found with name '{empleado_nombre}'."
    emp = employees[0]
    values: dict = {
        "name": descripcion,
        "employee_id": emp["id"],
        "total_amount": monto,
        "date": fecha or datetime.now().strftime("%Y-%m-%d"),
        "quantity": 1,
    }
    if categoria:
        products = client.search_read(
            "product.product",
            [("name", "ilike", categoria), ("can_be_expensed", "=", True)],
            ["id", "name"], limit=3
        )
        if products:
            values["product_id"] = products[0]["id"]
    expense_id = client.create("hr.expense", values)
    return f"[OK] Expense created (ID {expense_id}): '{descripcion}' - ${monto:,.2f} for {emp['name']}"


@mcp.tool()
def gastos_resumen_empleado(empleado: str = "", anio: int = 0, mes: int = 0) -> str:
    """
    Expense summary grouped by employee.

    Args:
        empleado: partial employee name (empty = all)
        anio: year (0 = all)
        mes: month 1-12 (0 = all)
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    domain: list = []
    if empleado:
        domain.append(("employee_id.name", "ilike", empleado))
    if anio:
        domain.append(("date", ">=", f"{anio}-01-01"))
        domain.append(("date", "<", f"{anio + 1}-01-01"))
    if mes and anio:
        domain = [d for d in domain if not (isinstance(d, tuple) and d[0] == "date")]
        fecha_inicio = f"{anio}-{mes:02d}-01"
        fecha_fin = f"{anio}-{mes + 1:02d}-01" if mes < 12 else f"{anio + 1}-01-01"
        domain.append(("date", ">=", fecha_inicio))
        domain.append(("date", "<", fecha_fin))
    expenses = client.search_read("hr.expense", domain, ["employee_id", "total_amount", "state"], limit=1000)
    by_emp: dict = {}
    for e in expenses:
        emp = e["employee_id"][1] if e.get("employee_id") else "N/A"
        if emp not in by_emp:
            by_emp[emp] = {"total": 0, "count": 0}
        by_emp[emp]["total"] += e.get("total_amount", 0)
        by_emp[emp]["count"] += 1
    lines = [f"{'Employee':<30} {'Expenses':>8} {'Total':>14}"]
    lines.append("-" * 55)
    for emp, data in sorted(by_emp.items(), key=lambda x: -x[1]["total"]):
        lines.append(f"{emp[:29]:<30} {data['count']:>8} ${data['total']:>13,.2f}")
    grand = sum(d["total"] for d in by_emp.values())
    lines.append("-" * 55)
    lines.append(f"{'TOTAL':<30} {len(expenses):>8} ${grand:>13,.2f}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
#  BANK RECONCILIATION
# ---------------------------------------------------------------------------

@mcp.tool()
def banco_listar_cuentas() -> str:
    """List bank journals configured in Odoo."""
    client = get_client()
    if client is None:
        return _not_configured_msg()
    journals = client.search_read(
        "account.journal",
        [("type", "in", ["bank", "cash"])],
        ["name", "type", "currency_id", "default_account_id"],
        limit=20
    )
    if not journals:
        return "No bank journals found."
    lines = [f"{'ID':<5} {'Name':<30} {'Type':<8} {'Currency'}"]
    lines.append("-" * 55)
    for j in journals:
        currency = j["currency_id"][1] if j.get("currency_id") else "Company default"
        lines.append(f"{j['id']:<5} {j['name'][:29]:<30} {j['type']:<8} {currency}")
    return "\n".join(lines)


@mcp.tool()
def banco_movimientos_sin_conciliar(diario_id: int = 0, limite: int = 20) -> str:
    """
    List unreconciled bank statement lines.

    Args:
        diario_id: bank journal ID (0 = all journals)
        limite: max results
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    domain: list = [("is_reconciled", "=", False), ("statement_id", "!=", False)]
    if diario_id:
        domain.append(("journal_id", "=", diario_id))
    fields = ["date", "payment_ref", "amount", "journal_id", "partner_name"]
    lines_data = client.search_read(
        "account.bank.statement.line", domain, fields, limit=limite, order="date desc"
    )
    if not lines_data:
        return "[OK] No unreconciled movements found."
    lines = [f"{'Date':<12} {'Reference':<30} {'Partner':<22} {'Amount':>12} {'Bank'}"]
    lines.append("-" * 95)
    for l in lines_data:
        lines.append(
            f"{str(l.get('date', '')):<12} "
            f"{str(l.get('payment_ref', '') or '')[:29]:<30} "
            f"{str(l.get('partner_name') or '')[:21]:<22} "
            f"${l.get('amount', 0):>11,.2f} "
            f"{l['journal_id'][1] if l.get('journal_id') else ''}"
        )
    return f"Unreconciled movements ({len(lines_data)}):\n" + "\n".join(lines)


@mcp.tool()
def banco_estado_extractos(diario_id: int = 0, limite: int = 10) -> str:
    """
    Show bank statement status (open vs closed).

    Args:
        diario_id: journal ID (0 = all)
        limite: max statements to show
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    domain: list = []
    if diario_id:
        domain.append(("journal_id", "=", diario_id))
    fields = ["name", "journal_id", "date", "balance_start", "balance_end_real"]
    statements = client.search_read(
        "account.bank.statement", domain, fields, limit=limite, order="date desc"
    )
    if not statements:
        return "No bank statements found."
    lines = [f"{'Statement':<20} {'Bank':<25} {'Date':<12} {'Opening Balance':>15} {'Closing Balance':>15}"]
    lines.append("-" * 92)
    for s in statements:
        lines.append(
            f"{str(s.get('name', ''))[:19]:<20} "
            f"{str(s['journal_id'][1] if s.get('journal_id') else '')[:24]:<25} "
            f"{str(s.get('date', '')):<12} "
            f"${s.get('balance_start', 0):>14,.2f} "
            f"${s.get('balance_end_real', 0):>14,.2f}"
        )
    return "\n".join(lines)


@mcp.tool()
def banco_pagos_recientes(dias: int = 7, limite: int = 20) -> str:
    """
    List payments registered in the last N days.

    Args:
        dias: lookback window in days (default 7)
        limite: max results
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    fecha_desde = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
    domain = [("date", ">=", fecha_desde), ("state", "in", ["posted", "reconciled"])]
    fields = ["name", "partner_id", "amount", "payment_type", "journal_id", "date", "state"]
    payments = client.search_read(
        "account.payment", domain, fields, limit=limite, order="date desc"
    )
    if not payments:
        return f"No payments found in the last {dias} days."
    tipo_map = {"inbound": "Receipt", "outbound": "Payment", "transfer": "Transfer"}
    lines = [f"{'Reference':<16} {'Partner':<25} {'Type':<13} {'Amount':>12} {'Bank':<20} {'Date'}"]
    lines.append("-" * 100)
    for p in payments:
        lines.append(
            f"{str(p.get('name', ''))[:15]:<16} "
            f"{str(p['partner_id'][1] if p.get('partner_id') else 'N/A')[:24]:<25} "
            f"{tipo_map.get(p.get('payment_type', ''), p.get('payment_type', '')):<13} "
            f"${p.get('amount', 0):>11,.2f} "
            f"{str(p['journal_id'][1] if p.get('journal_id') else '')[:19]:<20} "
            f"{p.get('date', '')}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
#  GENERAL UTILITIES
# ---------------------------------------------------------------------------

@mcp.tool()
def odoo_buscar_cliente(nombre: str, limite: int = 10) -> str:
    """
    Search an Odoo contact / customer by name.

    Args:
        nombre: text to search in the contact name or email
        limite: max results
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    partners = client.search_read(
        "res.partner",
        ["|", ("name", "ilike", nombre), ("email", "ilike", nombre)],
        ["name", "email", "phone", "customer_rank", "supplier_rank", "city", "country_id"],
        limit=limite
    )
    if not partners:
        return f"No contacts found matching '{nombre}'."
    lines = [f"{'ID':<6} {'Name':<30} {'Email':<28} {'Phone':<15} {'City'}"]
    lines.append("-" * 90)
    for p in partners:
        lines.append(
            f"{p['id']:<6} {str(p.get('name', ''))[:29]:<30} "
            f"{str(p.get('email') or '')[:27]:<28} "
            f"{str(p.get('phone') or '')[:14]:<15} "
            f"{str(p.get('city') or '')}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
#  ACCOUNTING
# ---------------------------------------------------------------------------

@mcp.tool()
def contabilidad_facturas_proveedor(
    fecha_desde: str = "",
    fecha_hasta: str = "",
    estado: str = "posted",
    limite: int = 50,
    buscar: str = ""
) -> str:
    """
    List vendor bills to help reconcile bank movements.

    Args:
        fecha_desde: start date YYYY-MM-DD (e.g. 2026-05-01)
        fecha_hasta: end date YYYY-MM-DD (e.g. 2026-05-31)
        estado: 'draft', 'posted', 'cancel', 'all'
        limite: max results
        buscar: filter by vendor name or reference
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    domain: list = [("move_type", "in", ["in_invoice", "in_receipt"])]
    if estado != "all":
        domain.append(("state", "=", estado))
    if fecha_desde:
        domain.append(("invoice_date", ">=", fecha_desde))
    if fecha_hasta:
        domain.append(("invoice_date", "<=", fecha_hasta))
    if buscar:
        domain.append("|")
        domain.append(("partner_id.name", "ilike", buscar))
        domain.append(("ref", "ilike", buscar))
    fields = ["name", "partner_id", "invoice_date", "amount_total",
              "amount_residual", "state", "payment_state", "ref"]
    facturas = client.search_read("account.move", domain, fields, limit=limite, order="invoice_date desc")
    if not facturas:
        return "No vendor bills found with those filters."
    pago_map = {
        "not_paid": "Unpaid", "in_payment": "In progress", "paid": "Paid",
        "partial": "Partial", "reversed": "Reversed"
    }
    lines = [f"{'Bill':<14} {'Vendor':<28} {'Date':<12} {'Total':>12} {'Pending':>12} {'Payment'}"]
    lines.append("-" * 90)
    total_pendiente = 0
    for f in facturas:
        pendiente = f.get("amount_residual", 0)
        total_pendiente += pendiente
        lines.append(
            f"{str(f.get('name', ''))[:13]:<14} "
            f"{str(f['partner_id'][1] if f.get('partner_id') else 'N/A')[:27]:<28} "
            f"{str(f.get('invoice_date', '')):<12} "
            f"${f.get('amount_total', 0):>11,.0f} "
            f"${pendiente:>11,.0f} "
            f"{pago_map.get(f.get('payment_state', ''), f.get('payment_state', ''))}"
        )
    lines.append("-" * 90)
    lines.append(f"{'TOTAL PENDING':>70} ${total_pendiente:>11,.0f}")
    return "\n".join(lines)


@mcp.tool()
def contabilidad_cruzar_banco_facturas(
    fecha_desde: str = "",
    fecha_hasta: str = ""
) -> str:
    """
    Cross-reference unreconciled bank movements with unpaid vendor bills by amount.

    Args:
        fecha_desde: start date YYYY-MM-DD
        fecha_hasta: end date YYYY-MM-DD
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    domain_banco: list = [("is_reconciled", "=", False), ("statement_id", "!=", False)]
    if fecha_desde:
        domain_banco.append(("date", ">=", fecha_desde))
    if fecha_hasta:
        domain_banco.append(("date", "<=", fecha_hasta))
    movimientos = client.search_read(
        "account.bank.statement.line", domain_banco,
        ["date", "payment_ref", "amount", "partner_name"],
        limit=200
    )
    domain_fact: list = [
        ("move_type", "in", ["in_invoice", "in_receipt"]),
        ("state", "=", "posted"),
        ("payment_state", "in", ["not_paid", "partial"])
    ]
    if fecha_desde:
        domain_fact.append(("invoice_date", ">=", fecha_desde))
    if fecha_hasta:
        domain_fact.append(("invoice_date", "<=", fecha_hasta))
    facturas = client.search_read(
        "account.move", domain_fact,
        ["name", "partner_id", "invoice_date", "amount_total", "amount_residual"],
        limit=200
    )
    matches = []
    for mov in movimientos:
        monto_banco = abs(mov.get("amount", 0))
        if monto_banco == 0:
            continue
        for fact in facturas:
            monto_fact = fact.get("amount_residual", 0)
            if abs(monto_banco - monto_fact) < 1:
                matches.append({
                    "fecha_banco": mov.get("date", ""),
                    "ref_banco": str(mov.get("payment_ref", ""))[:35],
                    "partner_banco": str(mov.get("partner_name") or "No partner")[:20],
                    "monto": monto_banco,
                    "factura": str(fact.get("name", "")),
                    "proveedor": str(fact["partner_id"][1] if fact.get("partner_id") else "N/A")[:25],
                    "fecha_fact": fact.get("invoice_date", "")
                })
    if not matches:
        return (
            f"No exact matches found between bank movements and vendor bills "
            f"for the period {fecha_desde} - {fecha_hasta}.\n"
            f"Movements reviewed: {len(movimientos)} | Bills reviewed: {len(facturas)}"
        )
    lines = [
        f"Matches found: {len(matches)}",
        "",
        f"{'Bank Date':<12} {'Bank Reference':<36} {'Bank Partner':<22} "
        f"{'Amount':>12} {'Bill':<14} {'Vendor':<26} {'Bill Date'}",
        "-" * 130,
    ]
    for m in matches:
        lines.append(
            f"{m['fecha_banco']:<12} {m['ref_banco']:<36} {m['partner_banco']:<22} "
            f"${m['monto']:>11,.2f} {m['factura']:<14} {m['proveedor']:<26} {m['fecha_fact']}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------

@mcp.tool()
def actividades_pendientes(
    usuario: str = "",
    vencidas: bool = False,
    limite: int = 30
) -> str:
    """
    List pending activities scheduled in Odoo for a user.

    Args:
        usuario: filter by user name (partial, empty = all users)
        vencidas: if True, show only overdue activities (past deadline)
        limite: max results
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()

    domain: list = []
    if usuario:
        domain.append(("user_id.name", "ilike", usuario))
    if vencidas:
        today = datetime.now().strftime("%Y-%m-%d")
        domain.append(("date_deadline", "<", today))

    fields = [
        "activity_type_id", "summary", "note", "date_deadline",
        "user_id", "res_model", "res_name", "res_id"
    ]
    activities = client.search_read(
        "mail.activity", domain, fields, limit=limite, order="date_deadline asc"
    )

    if not activities:
        msg = "overdue" if vencidas else "pending"
        return f"No {msg} activities found."

    today = datetime.now().date()
    lines = [
        f"{'Deadline':<12} {'Type':<18} {'Summary':<28} {'Assigned to':<20} {'Document'}"
    ]
    lines.append("-" * 100)
    for a in activities:
        deadline_str = str(a.get("date_deadline") or "No date")
        try:
            deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            overdue = " (!)" if deadline_date < today else ""
        except Exception:
            overdue = ""

        act_type = str(a["activity_type_id"][1] if a.get("activity_type_id") else "")
        summary = str(a.get("summary") or "")
        user = str(a["user_id"][1] if a.get("user_id") else "Unassigned")
        doc = str(a.get("res_name") or a.get("res_model") or "")

        lines.append(
            f"{deadline_str + overdue:<12} "
            f"{act_type[:17]:<18} "
            f"{summary[:27]:<28} "
            f"{user[:19]:<20} "
            f"{doc[:35]}"
        )

    overdue_count = sum(
        1 for a in activities
        if a.get("date_deadline") and
        datetime.strptime(str(a["date_deadline"]), "%Y-%m-%d").date() < today
    )
    header = f"Pending activities ({len(activities)} total, {overdue_count} overdue):\n"
    return header + "\n".join(lines)


# ---------------------------------------------------------------------------
#  HELPDESK
# ---------------------------------------------------------------------------

@mcp.tool()
def helpdesk_tickets(
    estado: str = "open",
    equipo: str = "",
    asignado: str = "",
    prioridad: str = "",
    limite: int = 20,
    buscar: str = ""
) -> str:
    """
    List Helpdesk tickets.

    Args:
        estado: 'open' (not closed), 'done' (resolved), 'all'
        equipo: filter by team name (partial)
        asignado: filter by assigned user name (partial)
        prioridad: '0' (normal), '1' (low), '2' (high), '3' (urgent), '' = all
        limite: max results
        buscar: filter by ticket title or customer name
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()

    domain: list = []
    if estado == "open":
        domain.append(("stage_id.is_close", "=", False))
    elif estado == "done":
        domain.append(("stage_id.is_close", "=", True))
    if equipo:
        domain.append(("team_id.name", "ilike", equipo))
    if asignado:
        domain.append(("user_id.name", "ilike", asignado))
    if prioridad:
        domain.append(("priority", "=", prioridad))
    if buscar:
        domain.append("|")
        domain.append(("name", "ilike", buscar))
        domain.append(("partner_id.name", "ilike", buscar))

    fields = [
        "name", "partner_id", "user_id", "team_id", "stage_id",
        "priority", "create_date", "date_last_stage_update", "ticket_type_id"
    ]
    tickets = client.search_read(
        "helpdesk.ticket", domain, fields, limit=limite, order="create_date desc"
    )

    if not tickets:
        return "No helpdesk tickets found with those filters."

    priority_map = {"0": "Normal", "1": "Low", "2": "High", "3": "Urgent"}

    lines = [
        f"{'ID':<6} {'Title':<32} {'Customer':<22} {'Stage':<18} "
        f"{'Priority':<9} {'Assigned':<18} {'Created'}"
    ]
    lines.append("-" * 120)
    for t in tickets:
        lines.append(
            f"{t['id']:<6} "
            f"{str(t.get('name', ''))[:31]:<32} "
            f"{str(t['partner_id'][1] if t.get('partner_id') else 'N/A')[:21]:<22} "
            f"{str(t['stage_id'][1] if t.get('stage_id') else '')[:17]:<18} "
            f"{priority_map.get(str(t.get('priority', '0')), 'Normal'):<9} "
            f"{str(t['user_id'][1] if t.get('user_id') else 'Unassigned')[:17]:<18} "
            f"{str(t.get('create_date', ''))[:10]}"
        )
    return f"Helpdesk tickets ({len(tickets)}):\n" + "\n".join(lines)


@mcp.tool()
def helpdesk_detalle_ticket(ticket_id: int) -> str:
    """
    Get full details of a helpdesk ticket.

    Args:
        ticket_id: numeric ticket ID
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()

    tickets = client.read(
        "helpdesk.ticket", [ticket_id],
        ["name", "partner_id", "user_id", "team_id", "stage_id",
         "priority", "description", "create_date", "date_last_stage_update",
         "ticket_type_id", "tag_ids"]
    )
    if not tickets:
        return f"Ticket {ticket_id} not found."

    t = tickets[0]
    priority_map = {"0": "Normal", "1": "Low", "2": "High", "3": "Urgent"}

    lines = [
        f"Ticket #{t['id']}: {t.get('name', '')}",
        f"Customer:  {t['partner_id'][1] if t.get('partner_id') else 'N/A'}",
        f"Team:      {t['team_id'][1] if t.get('team_id') else 'N/A'}",
        f"Stage:     {t['stage_id'][1] if t.get('stage_id') else 'N/A'}",
        f"Priority:  {priority_map.get(str(t.get('priority', '0')), 'Normal')}",
        f"Assigned:  {t['user_id'][1] if t.get('user_id') else 'Unassigned'}",
        f"Type:      {t['ticket_type_id'][1] if t.get('ticket_type_id') else 'N/A'}",
        f"Created:   {str(t.get('create_date', ''))[:16]}",
        f"Last update: {str(t.get('date_last_stage_update', ''))[:16]}",
    ]
    if t.get("description"):
        import re
        desc = re.sub(r"<[^>]+>", "", str(t["description"])).strip()
        if desc:
            lines += ["", "Description:", desc[:500]]

    return "\n".join(lines)

# ---------------------------------------------------------------------------
#  WEBSITE / eCOMMERCE (read-only)
# ---------------------------------------------------------------------------

@mcp.tool()
def website_paginas(limite: int = 30, buscar: str = "") -> str:
    """
    List published pages on the Odoo website.

    Args:
        limite: max results
        buscar: filter by page name or URL
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    domain: list = [("website_published", "=", True)]
    if buscar:
        domain.append("|")
        domain.append(("name", "ilike", buscar))
        domain.append(("url", "ilike", buscar))
    fields = ["name", "url", "website_published", "is_visible", "write_date"]
    try:
        pages = client.search_read("website.page", domain, fields, limit=limite, order="write_date desc")
    except Exception as e:
        return f"[!] Could not read website pages: {e}"
    if not pages:
        return "No published pages found."
    lines = [f"{'Name':<35} {'URL':<40} {'Last Updated'}"]
    lines.append("-" * 90)
    for p in pages:
        lines.append(
            f"{str(p.get('name', ''))[:34]:<35} "
            f"{str(p.get('url', ''))[:39]:<40} "
            f"{str(p.get('write_date', ''))[:10]}"
        )
    return f"Published pages ({len(pages)}):\n" + "\n".join(lines)


@mcp.tool()
def ecommerce_productos(
    publicado: bool = True,
    limite: int = 30,
    buscar: str = "",
    categoria: str = ""
) -> str:
    """
    List eCommerce products on the Odoo website.

    Args:
        publicado: True = only published products, False = all
        limite: max results
        buscar: filter by product name
        categoria: filter by category name (partial)
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    domain: list = []
    if publicado:
        domain.append(("is_published", "=", True))
    if buscar:
        domain.append(("name", "ilike", buscar))
    if categoria:
        domain.append(("categ_id.name", "ilike", categoria))
    fields = ["name", "list_price", "categ_id", "is_published",
              "website_published", "qty_available", "description_sale"]
    try:
        products = client.search_read("product.template", domain, fields, limit=limite, order="name asc")
    except Exception as e:
        return f"[!] Could not read eCommerce products: {e}"
    if not products:
        return "No products found."
    lines = [f"{'ID':<6} {'Product':<35} {'Price':>10} {'Stock':>8} {'Category'}"]
    lines.append("-" * 85)
    for p in products:
        lines.append(
            f"{p['id']:<6} "
            f"{str(p.get('name', ''))[:34]:<35} "
            f"${p.get('list_price', 0):>9,.2f} "
            f"{p.get('qty_available', 0):>8,.0f} "
            f"{str(p['categ_id'][1] if p.get('categ_id') else '')}"
        )
    return f"eCommerce products ({len(products)}):\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
#  PURCHASES
# ---------------------------------------------------------------------------

@mcp.tool()
def compras_listar_ordenes(
    estado: str = "purchase",
    limite: int = 15,
    dias: int = 30,
    buscar: str = ""
) -> str:
    """
    List purchase orders.

    Args:
        estado: 'draft' (RFQ), 'sent' (RFQ sent), 'purchase' (confirmed), 'done', 'cancel', 'all'
        limite: max results
        dias: filter orders from the last N days (0 = no filter)
        buscar: filter by vendor name or order number
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    domain: list = []
    if estado != "all":
        domain.append(("state", "=", estado))
    if dias > 0:
        fecha_desde = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
        domain.append(("date_order", ">=", fecha_desde))
    if buscar:
        domain.append("|")
        domain.append(("name", "ilike", buscar))
        domain.append(("partner_id.name", "ilike", buscar))
    fields = ["name", "partner_id", "amount_total", "state",
              "date_order", "user_id", "invoice_status", "currency_id"]
    orders = client.search_read("purchase.order", domain, fields, limit=limite, order="date_order desc")
    if not orders:
        return "No purchase orders found."
    estado_map = {"draft": "RFQ", "sent": "RFQ Sent", "purchase": "Confirmed",
                  "done": "Locked", "cancel": "Cancelled"}
    lines = [f"{'Order':<12} {'Vendor':<28} {'Total':>12} {'Status':<12} {'Invoice':<12} {'Date'}"]
    lines.append("-" * 90)
    for o in orders:
        lines.append(
            f"{o['name']:<12} "
            f"{str(o['partner_id'][1] if o.get('partner_id') else '')[:27]:<28} "
            f"${o.get('amount_total', 0):>11,.2f} "
            f"{estado_map.get(o['state'], o['state']):<12} "
            f"{o.get('invoice_status', ''):<12} "
            f"{str(o.get('date_order', ''))[:10]}"
        )
    return "\n".join(lines)


@mcp.tool()
def compras_detalle_orden(orden_id: int) -> str:
    """
    Get full details of a purchase order including product lines.

    Args:
        orden_id: numeric purchase order ID
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    orders = client.read("purchase.order", [orden_id],
        ["name", "partner_id", "amount_untaxed", "amount_tax", "amount_total",
         "state", "date_order", "user_id", "order_line", "notes", "invoice_status"])
    if not orders:
        return f"Purchase order {orden_id} not found."
    o = orders[0]
    lines_data = client.read("purchase.order.line", o["order_line"],
        ["product_id", "product_qty", "price_unit", "price_subtotal", "name", "date_planned"])
    output = [
        f"Order:    {o['name']}",
        f"Vendor:   {o['partner_id'][1] if o.get('partner_id') else 'N/A'}",
        f"Date:     {str(o.get('date_order', ''))[:16]}",
        f"Status:   {o.get('state', '')} | Invoicing: {o.get('invoice_status', '')}",
        f"Buyer:    {o['user_id'][1] if o.get('user_id') else 'N/A'}",
        "",
        f"{'Product':<35} {'Qty':>6} {'Unit Price':>12} {'Subtotal':>12} {'Scheduled'}",
        "-" * 80,
    ]
    for line in lines_data:
        output.append(
            f"{str(line.get('name') or (line['product_id'][1] if line.get('product_id') else ''))[:34]:<35} "
            f"{line.get('product_qty', 0):>6.1f} "
            f"${line.get('price_unit', 0):>11,.2f} "
            f"${line.get('price_subtotal', 0):>11,.2f} "
            f"{str(line.get('date_planned', ''))[:10]}"
        )
    output.extend([
        "-" * 80,
        f"{'Subtotal':>66} ${o.get('amount_untaxed', 0):>11,.2f}",
        f"{'Taxes':>66} ${o.get('amount_tax', 0):>11,.2f}",
        f"{'TOTAL':>66} ${o.get('amount_total', 0):>11,.2f}",
    ])
    return "\n".join(output)


@mcp.tool()
def compras_resumen_mes(anio: int = 0, mes: int = 0) -> str:
    """
    Monthly purchase summary grouped by vendor.

    Args:
        anio: year (0 = current year)
        mes: month 1-12 (0 = current month)
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    now = datetime.now()
    anio = anio or now.year
    mes = mes or now.month
    fecha_inicio = f"{anio}-{mes:02d}-01"
    fecha_fin = f"{anio}-{mes + 1:02d}-01" if mes < 12 else f"{anio + 1}-01-01"
    orders = client.search_read(
        "purchase.order",
        [("state", "in", ["purchase", "done"]),
         ("date_order", ">=", fecha_inicio),
         ("date_order", "<", fecha_fin)],
        ["partner_id", "amount_total"],
        limit=500
    )
    total = sum(o["amount_total"] for o in orders)
    by_vendor: dict = {}
    vendor_counts: dict = {}
    for o in orders:
        v = o["partner_id"][1] if o.get("partner_id") else "Unknown"
        by_vendor[v] = by_vendor.get(v, 0) + o["amount_total"]
        vendor_counts[v] = vendor_counts.get(v, 0) + 1
    lines = [
        f"Purchase Summary - {mes:02d}/{anio}",
        f"Total orders: {len(orders)}  |  Total spent: ${total:,.2f}",
        "",
        f"{'Vendor':<35} {'Orders':>8} {'Total':>14}",
        "-" * 60,
    ]
    for v, t in sorted(by_vendor.items(), key=lambda x: -x[1]):
        lines.append(f"{v[:34]:<35} {vendor_counts[v]:>8} ${t:>13,.2f}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
#  INVENTORY
# ---------------------------------------------------------------------------

@mcp.tool()
def inventario_stock(
    buscar: str = "",
    ubicacion: str = "",
    limite: int = 30,
    sin_stock: bool = False
) -> str:
    """
    Query current stock levels.

    Args:
        buscar: filter by product name (partial)
        ubicacion: filter by location name (partial, e.g. 'WH/Stock')
        limite: max results
        sin_stock: if True, include products with zero stock
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    domain: list = [("location_id.usage", "=", "internal")]
    if buscar:
        domain.append(("product_id.name", "ilike", buscar))
    if ubicacion:
        domain.append(("location_id.complete_name", "ilike", ubicacion))
    if not sin_stock:
        domain.append(("quantity", ">", 0))
    fields = ["product_id", "quantity", "reserved_quantity",
              "location_id", "lot_id", "package_id"]
    quants = client.search_read("stock.quant", domain, fields, limit=limite, order="quantity desc")
    if not quants:
        return "No stock found with those filters."
    lines = [f"{'Product':<35} {'On Hand':>10} {'Reserved':>10} {'Available':>10} {'Location'}"]
    lines.append("-" * 95)
    for q in quants:
        on_hand = q.get("quantity", 0)
        reserved = q.get("reserved_quantity", 0)
        available = on_hand - reserved
        lines.append(
            f"{str(q['product_id'][1] if q.get('product_id') else '')[:34]:<35} "
            f"{on_hand:>10,.2f} "
            f"{reserved:>10,.2f} "
            f"{available:>10,.2f} "
            f"{str(q['location_id'][1] if q.get('location_id') else '')}"
        )
    return f"Stock levels ({len(quants)} lines):\n" + "\n".join(lines)


@mcp.tool()
def inventario_movimientos(
    estado: str = "ready",
    limite: int = 20,
    dias: int = 7,
    tipo: str = ""
) -> str:
    """
    List stock transfers / movements.

    Args:
        estado: 'draft', 'ready' (waiting), 'done', 'cancel', 'all'
        limite: max results
        dias: last N days (0 = no filter)
        tipo: 'incoming' (receipts), 'outgoing' (deliveries), 'internal', '' = all
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    domain: list = []
    if estado != "all":
        state_map = {"ready": "assigned", "done": "done", "draft": "draft", "cancel": "cancel"}
        domain.append(("state", "=", state_map.get(estado, estado)))
    if dias > 0:
        fecha_desde = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
        domain.append(("scheduled_date", ">=", fecha_desde))
    if tipo:
        domain.append(("picking_type_code", "=", tipo))
    fields = ["name", "partner_id", "picking_type_id", "state",
              "scheduled_date", "origin", "location_id", "location_dest_id"]
    pickings = client.search_read("stock.picking", domain, fields, limit=limite, order="scheduled_date desc")
    if not pickings:
        return "No stock movements found."
    estado_map = {"draft": "Draft", "waiting": "Waiting", "confirmed": "Confirmed",
                  "assigned": "Ready", "done": "Done", "cancel": "Cancelled"}
    lines = [f"{'Reference':<16} {'Type':<14} {'Status':<12} {'Partner':<22} {'From':<18} {'Scheduled'}"]
    lines.append("-" * 100)
    for p in pickings:
        lines.append(
            f"{str(p.get('name', ''))[:15]:<16} "
            f"{str(p['picking_type_id'][1] if p.get('picking_type_id') else '')[:13]:<14} "
            f"{estado_map.get(p.get('state', ''), p.get('state', '')):<12} "
            f"{str(p['partner_id'][1] if p.get('partner_id') else 'N/A')[:21]:<22} "
            f"{str(p['location_id'][1] if p.get('location_id') else '')[:17]:<18} "
            f"{str(p.get('scheduled_date', ''))[:10]}"
        )
    return f"Stock movements ({len(pickings)}):\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
#  PROJECTS
# ---------------------------------------------------------------------------

@mcp.tool()
def proyecto_listar(activo: bool = True, limite: int = 20) -> str:
    """
    List projects.

    Args:
        activo: True = only active projects
        limite: max results
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    domain: list = []
    if activo:
        domain.append(("active", "=", True))
    fields = ["name", "partner_id", "user_id", "date_start", "date",
              "task_count", "description"]
    projects = client.search_read("project.project", domain, fields, limit=limite, order="name asc")
    if not projects:
        return "No projects found."
    lines = [f"{'ID':<5} {'Project':<32} {'Manager':<22} {'Customer':<22} {'Tasks':>6} {'Start':<12} {'Deadline'}"]
    lines.append("-" * 110)
    for p in projects:
        lines.append(
            f"{p['id']:<5} "
            f"{str(p.get('name', ''))[:31]:<32} "
            f"{str(p['user_id'][1] if p.get('user_id') else 'N/A')[:21]:<22} "
            f"{str(p['partner_id'][1] if p.get('partner_id') else '')[:21]:<22} "
            f"{p.get('task_count', 0):>6} "
            f"{str(p.get('date_start', ''))[:10]:<12} "
            f"{str(p.get('date', ''))[:10]}"
        )
    return f"Projects ({len(projects)}):\n" + "\n".join(lines)


@mcp.tool()
def proyecto_tareas(
    proyecto: str = "",
    estado: str = "open",
    asignado: str = "",
    limite: int = 25,
    buscar: str = ""
) -> str:
    """
    List project tasks.

    Args:
        proyecto: filter by project name (partial)
        estado: 'open' (not done), 'done', 'all'
        asignado: filter by assigned user name (partial)
        limite: max results
        buscar: filter by task title
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    domain: list = []
    if proyecto:
        domain.append(("project_id.name", "ilike", proyecto))
    if estado == "open":
        domain.append(("stage_id.is_closed", "=", False))
    elif estado == "done":
        domain.append(("stage_id.is_closed", "=", True))
    if asignado:
        domain.append(("user_ids.name", "ilike", asignado))
    if buscar:
        domain.append(("name", "ilike", buscar))
    fields = ["name", "project_id", "user_ids", "stage_id",
              "date_deadline", "priority", "tag_ids", "description"]
    tasks = client.search_read("project.task", domain, fields, limit=limite, order="date_deadline asc")
    if not tasks:
        return "No tasks found."
    lines = [f"{'ID':<6} {'Task':<32} {'Project':<22} {'Stage':<18} {'Assigned':<20} {'Deadline'}"]
    lines.append("-" * 110)
    for t in tasks:
        assigned = ", ".join([u[1] for u in t.get("user_ids", []) if u]) if t.get("user_ids") else "Unassigned"
        priority = " [!]" if t.get("priority") == "1" else ""
        lines.append(
            f"{t['id']:<6} "
            f"{str(t.get('name', ''))[:31] + priority:<32} "
            f"{str(t['project_id'][1] if t.get('project_id') else '')[:21]:<22} "
            f"{str(t['stage_id'][1] if t.get('stage_id') else '')[:17]:<18} "
            f"{assigned[:19]:<20} "
            f"{str(t.get('date_deadline', ''))[:10] or 'No date'}"
        )
    return f"Tasks ({len(tasks)}):\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
#  EMPLOYEES
# ---------------------------------------------------------------------------

@mcp.tool()
def empleados_listar(
    activo: bool = True,
    departamento: str = "",
    buscar: str = "",
    limite: int = 30
) -> str:
    """
    List employees.

    Args:
        activo: True = active employees only
        departamento: filter by department name (partial)
        buscar: filter by employee name
        limite: max results
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    domain: list = []
    if activo:
        domain.append(("active", "=", True))
    if departamento:
        domain.append(("department_id.name", "ilike", departamento))
    if buscar:
        domain.append(("name", "ilike", buscar))
    fields = ["name", "job_title", "department_id", "work_email",
              "work_phone", "parent_id", "coach_id"]
    employees = client.search_read("hr.employee", domain, fields, limit=limite, order="name asc")
    if not employees:
        return "No employees found."
    lines = [f"{'ID':<5} {'Name':<28} {'Job Title':<25} {'Department':<20} {'Email'}"]
    lines.append("-" * 100)
    for e in employees:
        lines.append(
            f"{e['id']:<5} "
            f"{str(e.get('name', ''))[:27]:<28} "
            f"{str(e.get('job_title', '') or '')[:24]:<25} "
            f"{str(e['department_id'][1] if e.get('department_id') else '')[:19]:<20} "
            f"{str(e.get('work_email', '') or '')}"
        )
    return f"Employees ({len(employees)}):\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
#  CALENDAR
# ---------------------------------------------------------------------------

@mcp.tool()
def calendario_eventos(
    dias: int = 7,
    usuario: str = "",
    limite: int = 20
) -> str:
    """
    List upcoming calendar events.

    Args:
        dias: show events for the next N days (default 7)
        usuario: filter by attendee name (partial)
        limite: max results
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    hoy = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hasta = (datetime.now() + timedelta(days=dias)).strftime("%Y-%m-%d %H:%M:%S")
    domain: list = [
        ("start", ">=", hoy),
        ("start", "<=", hasta),
        ("active", "=", True),
    ]
    if usuario:
        domain.append(("attendee_ids.partner_id.name", "ilike", usuario))
    fields = ["name", "start", "stop", "user_id", "partner_ids",
              "location", "description", "allday"]
    events = client.search_read("calendar.event", domain, fields, limit=limite, order="start asc")
    if not events:
        return f"No events found in the next {dias} days."
    lines = [f"{'Start':<18} {'End':<18} {'Title':<30} {'Organizer':<20} {'Location'}"]
    lines.append("-" * 100)
    for e in events:
        start = str(e.get("start", ""))[:16]
        stop = str(e.get("stop", ""))[:16]
        lines.append(
            f"{start:<18} "
            f"{stop:<18} "
            f"{str(e.get('name', ''))[:29]:<30} "
            f"{str(e['user_id'][1] if e.get('user_id') else '')[:19]:<20} "
            f"{str(e.get('location', '') or '')[:30]}"
        )
    return f"Upcoming events (next {dias} days):\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
#  SUBSCRIPTIONS
# ---------------------------------------------------------------------------

@mcp.tool()
def suscripciones_listar(
    estado: str = "open",
    limite: int = 20,
    buscar: str = ""
) -> str:
    """
    List recurring subscriptions.

    Args:
        estado: 'open' (active), 'closed', 'all'
        limite: max results
        buscar: filter by customer name
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    # Try sale.subscription first (Odoo 16), fallback to sale.order with subscription flag
    try:
        # Odoo 16: sale.subscription model
        domain: list = []
        if estado == "open":
            domain.append(("stage_category", "=", "progress"))
        elif estado == "closed":
            domain.append(("stage_category", "=", "closed"))
        if buscar:
            domain.append(("partner_id.name", "ilike", buscar))
        fields = ["name", "partner_id", "recurring_monthly", "stage_id",
                  "date_start", "date", "user_id", "currency_id"]
        subs = client.search_read("sale.subscription", domain, fields, limit=limite, order="date_start desc")
        model_used = "sale.subscription"
    except Exception:
        # Odoo 17-19: sale.order with is_subscription flag
        try:
            domain = [("is_subscription", "=", True)]
            if estado == "open":
                domain.append(("subscription_state", "=", "3_progress"))
            if buscar:
                domain.append(("partner_id.name", "ilike", buscar))
            fields = ["name", "partner_id", "amount_total", "subscription_state",
                      "next_invoice_date", "user_id", "date_order"]
            subs = client.search_read("sale.order", domain, fields, limit=limite, order="date_order desc")
            model_used = "sale.order (subscription)"
        except Exception as e2:
            return f"[!] Could not read subscriptions: {e2}"

    if not subs:
        return "No subscriptions found."

    lines = [f"Model: {model_used}", "",
             f"{'ID':<6} {'Customer':<28} {'Stage':<18} {'MRR/Total':>12} {'Start':<12} {'Salesperson'}"]
    lines.append("-" * 95)
    for s in subs:
        mrr = s.get("recurring_monthly") or s.get("amount_total") or 0
        stage = s.get("stage_id")
        stage_str = stage[1] if isinstance(stage, (list, tuple)) and len(stage) > 1 else str(s.get("subscription_state", ""))
        lines.append(
            f"{s['id']:<6} "
            f"{str(s['partner_id'][1] if s.get('partner_id') else '')[:27]:<28} "
            f"{stage_str[:17]:<18} "
            f"${mrr:>11,.2f} "
            f"{str(s.get('date_start', ''))[:10]:<12} "
            f"{str(s['user_id'][1] if s.get('user_id') else '')}"
        )
    return f"Subscriptions ({len(subs)}):\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
#  ATTENDANCES
# ---------------------------------------------------------------------------

@mcp.tool()
def asistencias_reporte(
    empleado: str = "",
    fecha_desde: str = "",
    fecha_hasta: str = "",
    limite: int = 50
) -> str:
    """
    Report employee check-in/check-out attendance records.

    Args:
        empleado: filter by employee name (partial, empty = all)
        fecha_desde: start date YYYY-MM-DD (default: today)
        fecha_hasta: end date YYYY-MM-DD (default: today)
        limite: max results
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    hoy = datetime.now().strftime("%Y-%m-%d")
    fecha_desde = fecha_desde or hoy
    fecha_hasta = fecha_hasta or hoy
    domain: list = [
        ("check_in", ">=", f"{fecha_desde} 00:00:00"),
        ("check_in", "<=", f"{fecha_hasta} 23:59:59"),
    ]
    if empleado:
        domain.append(("employee_id.name", "ilike", empleado))
    fields = ["employee_id", "check_in", "check_out", "worked_hours"]
    records = client.search_read("hr.attendance", domain, fields, limit=limite, order="check_in desc")
    if not records:
        return f"No attendance records found for {fecha_desde} to {fecha_hasta}."
    by_emp: dict = {}
    for r in records:
        emp = r["employee_id"][1] if r.get("employee_id") else "N/A"
        if emp not in by_emp:
            by_emp[emp] = {"hours": 0, "count": 0}
        by_emp[emp]["hours"] += r.get("worked_hours", 0)
        by_emp[emp]["count"] += 1
    lines = [f"Attendance {fecha_desde} to {fecha_hasta}:", ""]
    lines.append(f"{'Employee':<28} {'Check-in':<18} {'Check-out':<18} {'Hours':>7}")
    lines.append("-" * 75)
    for r in records:
        emp = str(r["employee_id"][1] if r.get("employee_id") else "N/A")
        check_in = str(r.get("check_in", ""))[:16]
        check_out = str(r.get("check_out", "") or "Active")[:16]
        hours = r.get("worked_hours", 0)
        lines.append(f"{emp[:27]:<28} {check_in:<18} {check_out:<18} {hours:>7.2f}h")
    lines.append("-" * 75)
    lines.append("")
    lines.append("Summary by employee:")
    for emp, data in sorted(by_emp.items(), key=lambda x: -x[1]["hours"]):
        lines.append(f"  {emp[:30]:<30} {data['count']} records  {data['hours']:.2f}h total")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
#  EMAIL MARKETING
# ---------------------------------------------------------------------------

@mcp.tool()
def marketing_campanas(
    estado: str = "all",
    limite: int = 20,
    buscar: str = ""
) -> str:
    """
    List email marketing campaigns.

    Args:
        estado: 'draft', 'in_queue', 'sending', 'done', 'all'
        limite: max results
        buscar: filter by campaign subject
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    domain: list = []
    if estado != "all":
        domain.append(("state", "=", estado))
    if buscar:
        domain.append(("subject", "ilike", buscar))
    fields = ["subject", "email_from", "state", "sent", "opened",
              "clicked", "scheduled_date", "contact_list_ids", "reply_to"]
    try:
        mailings = client.search_read("mailing.mailing", domain, fields, limit=limite, order="scheduled_date desc")
    except Exception as e:
        return f"[!] Could not read email campaigns: {e}"
    if not mailings:
        return "No email campaigns found."
    estado_map = {
        "draft": "Draft", "in_queue": "Queued", "sending": "Sending",
        "done": "Sent", "cancel": "Cancelled"
    }
    lines = [f"{'Subject':<35} {'Status':<10} {'Sent':>7} {'Opened':>7} {'Clicked':>8} {'Scheduled'}"]
    lines.append("-" * 85)
    for m in mailings:
        sent = m.get("sent", 0) or 0
        opened = m.get("opened", 0) or 0
        clicked = m.get("clicked", 0) or 0
        open_rate = f"{opened/sent*100:.0f}%" if sent > 0 else "-"
        lines.append(
            f"{str(m.get('subject', ''))[:34]:<35} "
            f"{estado_map.get(m.get('state', ''), m.get('state', '')):<10} "
            f"{sent:>7} "
            f"{open_rate:>7} "
            f"{clicked:>8} "
            f"{str(m.get('scheduled_date', '') or '')[:10]}"
        )
    return f"Email campaigns ({len(mailings)}):\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
#  WHATSAPP
# ---------------------------------------------------------------------------

@mcp.tool()
def whatsapp_mensajes(
    limite: int = 20,
    buscar: str = ""
) -> str:
    """
    List recent WhatsApp messages sent from Odoo.

    Args:
        limite: max results
        buscar: filter by phone number or partner name
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    domain: list = []
    if buscar:
        domain.append("|")
        domain.append(("mobile_number", "ilike", buscar))
        domain.append(("partner_id.name", "ilike", buscar))
    fields = ["mobile_number", "partner_id", "state", "create_date",
              "wa_template_id", "body"]
    try:
        msgs = client.search_read("whatsapp.message", domain, fields, limit=limite, order="create_date desc")
    except Exception as e:
        return f"[!] Could not read WhatsApp messages: {e}"
    if not msgs:
        return "No WhatsApp messages found."
    estado_map = {"outgoing": "Sending", "sent": "Sent", "delivered": "Delivered",
                  "read": "Read", "error": "Error", "cancel": "Cancelled"}
    lines = [f"{'Phone':<16} {'Contact':<25} {'Template':<25} {'Status':<12} {'Date'}"]
    lines.append("-" * 90)
    for m in msgs:
        template = str(m["wa_template_id"][1] if m.get("wa_template_id") else "Custom")
        lines.append(
            f"{str(m.get('mobile_number', ''))[:15]:<16} "
            f"{str(m['partner_id'][1] if m.get('partner_id') else 'N/A')[:24]:<25} "
            f"{template[:24]:<25} "
            f"{estado_map.get(m.get('state', ''), m.get('state', '')):<12} "
            f"{str(m.get('create_date', ''))[:10]}"
        )
    return f"WhatsApp messages ({len(msgs)}):\n" + "\n".join(lines)


@mcp.tool()
def whatsapp_plantillas(limite: int = 20) -> str:
    """List available WhatsApp message templates."""
    client = get_client()
    if client is None:
        return _not_configured_msg()
    fields = ["name", "status", "category", "lang"]
    try:
        templates = client.search_read("whatsapp.template", [], fields, limit=limite, order="name asc")
    except Exception as e:
        return f"[!] Could not read WhatsApp templates: {e}"
    if not templates:
        return "No WhatsApp templates found."
    lines = [f"{'ID':<5} {'Name':<35} {'Category':<18} {'Status':<12} {'Language'}"]
    lines.append("-" * 80)
    for t in templates:
        lines.append(
            f"{t['id']:<5} "
            f"{str(t.get('name', ''))[:34]:<35} "
            f"{str(t.get('category', '') or '')[:17]:<18} "
            f"{str(t.get('status', '') or ''):<12} "
            f"{str(t.get('lang', '') or '')}"
        )
    return f"WhatsApp templates ({len(templates)}):\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
#  CONVERSATIONS / DISCUSS
# ---------------------------------------------------------------------------

@mcp.tool()
def conversaciones_canales(limite: int = 20) -> str:
    """List Discuss channels and group conversations."""
    client = get_client()
    if client is None:
        return _not_configured_msg()
    domain: list = [("channel_type", "=", "channel")]
    fields = ["name", "description", "member_count", "create_date", "channel_type"]
    try:
        channels = client.search_read("discuss.channel", domain, fields, limit=limite, order="name asc")
    except Exception as e:
        return f"[!] Could not read channels: {e}"
    if not channels:
        return "No channels found."
    lines = [f"{'ID':<5} {'Channel':<30} {'Members':>8} {'Description'}"]
    lines.append("-" * 70)
    for c in channels:
        lines.append(
            f"{c['id']:<5} "
            f"{str(c.get('name', ''))[:29]:<30} "
            f"{c.get('member_count', 0):>8} "
            f"{str(c.get('description', '') or '')[:40]}"
        )
    return f"Channels ({len(channels)}):\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
#  DOCUMENTS
# ---------------------------------------------------------------------------

@mcp.tool()
def documentos_listar(
    carpeta: str = "",
    buscar: str = "",
    limite: int = 30
) -> str:
    """
    List documents stored in Odoo Documents module.

    Args:
        carpeta: filter by folder name (partial)
        buscar: filter by document name
        limite: max results
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    domain: list = [("type", "=", "binary")]
    if carpeta:
        domain.append(("folder_id.name", "ilike", carpeta))
    if buscar:
        domain.append(("name", "ilike", buscar))
    fields = ["name", "folder_id", "partner_id", "owner_id",
              "write_date", "file_size", "mimetype", "tag_ids"]
    try:
        docs = client.search_read("documents.document", domain, fields, limit=limite, order="write_date desc")
    except Exception as e:
        return f"[!] Could not read documents: {e}"
    if not docs:
        return "No documents found."
    lines = [f"{'Name':<35} {'Folder':<22} {'Owner':<18} {'Size':>8} {'Modified'}"]
    lines.append("-" * 95)
    for d in docs:
        size = d.get("file_size", 0) or 0
        size_str = f"{size/1024:.0f}KB" if size < 1048576 else f"{size/1048576:.1f}MB"
        lines.append(
            f"{str(d.get('name', ''))[:34]:<35} "
            f"{str(d['folder_id'][1] if d.get('folder_id') else 'Root')[:21]:<22} "
            f"{str(d['owner_id'][1] if d.get('owner_id') else '')[:17]:<18} "
            f"{size_str:>8} "
            f"{str(d.get('write_date', ''))[:10]}"
        )
    return f"Documents ({len(docs)}):\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
#  APPOINTMENTS
# ---------------------------------------------------------------------------

@mcp.tool()
def citas_listar(
    fecha_desde: str = "",
    fecha_hasta: str = "",
    limite: int = 20
) -> str:
    """
    List scheduled appointments.

    Args:
        fecha_desde: start date YYYY-MM-DD (default: today)
        fecha_hasta: end date YYYY-MM-DD (default: 7 days from now)
        limite: max results
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    hoy = datetime.now().strftime("%Y-%m-%d")
    hasta = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    fecha_desde = fecha_desde or hoy
    fecha_hasta = fecha_hasta or hasta
    domain: list = [
        ("start", ">=", f"{fecha_desde} 00:00:00"),
        ("start", "<=", f"{fecha_hasta} 23:59:59"),
    ]
    # Appointments in Odoo are calendar events with appointment_type_id
    domain.append(("appointment_type_id", "!=", False))
    fields = ["name", "start", "stop", "partner_ids", "user_id",
              "appointment_type_id", "location"]
    try:
        appts = client.search_read("calendar.event", domain, fields, limit=limite, order="start asc")
    except Exception as e:
        return f"[!] Could not read appointments: {e}"
    if not appts:
        return f"No appointments found from {fecha_desde} to {fecha_hasta}."
    lines = [f"{'Title':<30} {'Type':<22} {'Start':<18} {'Staff':<18} {'Customer'}"]
    lines.append("-" * 100)
    for a in appts:
        customers = ", ".join([p[1] for p in (a.get("partner_ids") or []) if p])[:25]
        lines.append(
            f"{str(a.get('name', ''))[:29]:<30} "
            f"{str(a['appointment_type_id'][1] if a.get('appointment_type_id') else '')[:21]:<22} "
            f"{str(a.get('start', ''))[:16]:<18} "
            f"{str(a['user_id'][1] if a.get('user_id') else '')[:17]:<18} "
            f"{customers}"
        )
    return f"Appointments ({len(appts)}):\n" + "\n".join(lines)


@mcp.tool()
def citas_tipos(limite: int = 20) -> str:
    """List available appointment types configured in Odoo."""
    client = get_client()
    if client is None:
        return _not_configured_msg()
    fields = ["name", "category", "slot_duration", "appointment_duration",
              "staff_user_ids", "location_id"]
    try:
        types = client.search_read("appointment.type", [], fields, limit=limite, order="name asc")
    except Exception as e:
        return f"[!] Could not read appointment types: {e}"
    if not types:
        return "No appointment types found."
    lines = [f"{'ID':<5} {'Name':<35} {'Duration':<10} {'Category'}"]
    lines.append("-" * 65)
    for t in types:
        dur = t.get("appointment_duration") or t.get("slot_duration") or 0
        lines.append(
            f"{t['id']:<5} "
            f"{str(t.get('name', ''))[:34]:<35} "
            f"{dur:.0f} min{'':<4} "
            f"{str(t.get('category', '') or '')}"
        )
    return f"Appointment types ({len(types)}):\n" + "\n".join(lines)


if __name__ == "__main__" or True:
    mcp.run()
