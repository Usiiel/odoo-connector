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
