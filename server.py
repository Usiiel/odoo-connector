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
    buscar: str = "",
    vendedor: str = "",
    fecha_desde: str = "",
    fecha_hasta: str = "",
    fecha_campo: str = "date_deadline"
) -> str:
    """
    List CRM opportunities / leads.

    Args:
        estado: 'open' (active), 'won', 'lost', 'all'
        limite: max results (default 15)
        buscar: filter by lead name or customer
        vendedor: filter by salesperson name (partial match)
        fecha_desde: start date filter YYYY-MM-DD (applies to fecha_campo)
        fecha_hasta: end date filter YYYY-MM-DD (applies to fecha_campo)
        fecha_campo: date field to filter on — 'date_deadline' (closing date, default),
                     'create_date' (creation date), or 'date_closed' (won/lost date)
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
    if vendedor:
        domain.append(("user_id.name", "ilike", vendedor))
    campo = fecha_campo if fecha_campo in ("date_deadline", "create_date", "date_closed") else "date_deadline"
    if fecha_desde:
        domain.append((campo, ">=", fecha_desde))
    if fecha_hasta:
        domain.append((campo, "<=", fecha_hasta))
    fields = ["name", "partner_name", "partner_id", "expected_revenue", "stage_id",
              "user_id", "date_deadline", "create_date", "probability"]
    leads = client.search_read("crm.lead", domain, fields, limit=limite, order="expected_revenue desc")
    if not leads:
        return "No se encontraron oportunidades con los filtros indicados."

    # Fetch VAT for linked partners in one batch call
    partner_ids = [l["partner_id"][0] for l in leads if l.get("partner_id")]
    vat_map: dict = {}
    if partner_ids:
        partners = client.search_read(
            "res.partner",
            [("id", "in", partner_ids)],
            ["id", "vat"],
            limit=len(partner_ids) + 1
        )
        vat_map = {p["id"]: (p.get("vat") or "-") for p in partners}

    # Build header — show which filters are active
    filtros = []
    if vendedor:
        filtros.append(f"vendedor='{vendedor}'")
    if fecha_desde:
        filtros.append(f"{campo} >= {fecha_desde}")
    if fecha_hasta:
        filtros.append(f"{campo} <= {fecha_hasta}")
    header = f"Oportunidades [{estado}]"
    if filtros:
        header += "  |  Filtros: " + ", ".join(filtros)
    lines = [header, ""]
    lines.append(f"{'#':<4} {'Oportunidad':<30} {'Cliente':<25} {'RUT/VAT':<14} {'Etapa':<18} {'Vendedor':<18} {'Valor Est.':<12} {'Prob%':<7} {'Cierre'}")
    lines.append("-" * 140)
    for l in leads:
        pid = l["partner_id"][0] if l.get("partner_id") else None
        vat = vat_map.get(pid, "-") if pid else "-"
        lines.append(
            f"{l['id']:<4} "
            f"{str(l['name'])[:29]:<30} "
            f"{str(l.get('partner_name') or '')[:24]:<25} "
            f"{str(vat)[:13]:<14} "
            f"{str(l['stage_id'][1] if l.get('stage_id') else '')[:17]:<18} "
            f"{str(l['user_id'][1] if l.get('user_id') else 'Sin asignar')[:17]:<18} "
            f"${l.get('expected_revenue', 0):>10,.0f} "
            f"{l.get('probability', 0):>5.0f}% "
            f"{l.get('date_deadline') or 'Sin fecha'}"
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
def crm_asignar_vendedor(
    oportunidad_ids: list,
    vendedor: str
) -> str:
    """
    Assign one or more CRM leads/opportunities to a different salesperson.

    Args:
        oportunidad_ids: list of opportunity/lead IDs to reassign (e.g. [12, 34, 56])
        vendedor: salesperson name or email to search for (partial match on name, exact on email)
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()

    if not oportunidad_ids:
        return "[!] Debes indicar al menos un ID de oportunidad."

    # Search user by email (exact) or name (partial)
    user = None
    if "@" in vendedor:
        users = client.search_read(
            "res.users",
            [("login", "=", vendedor)],
            ["id", "name", "login"],
            limit=1
        )
    else:
        users = client.search_read(
            "res.users",
            [("name", "ilike", vendedor), ("active", "=", True)],
            ["id", "name", "login"],
            limit=5
        )

    if not users:
        return f"[!] No se encontró ningún usuario con '{vendedor}'. Verifica el nombre o email."

    if len(users) > 1:
        opciones = "\n".join(f"  - {u['name']} ({u['login']})" for u in users)
        return (
            f"[!] Se encontraron varios usuarios que coinciden con '{vendedor}':\n"
            f"{opciones}\n\n"
            f"Usa un nombre más específico o el email exacto para asignar."
        )

    user = users[0]

    # Verify all lead IDs exist
    leads = client.search_read(
        "crm.lead",
        [("id", "in", oportunidad_ids)],
        ["id", "name", "user_id"],
        limit=len(oportunidad_ids) + 1
    )

    if not leads:
        return f"[!] No se encontraron oportunidades con los IDs: {oportunidad_ids}"

    found_ids = [l["id"] for l in leads]
    missing = [i for i in oportunidad_ids if i not in found_ids]

    # Perform the assignment
    client.write("crm.lead", found_ids, {"user_id": user["id"]})

    lines = [f"[OK] {len(found_ids)} oportunidad(es) asignada(s) a {user['name']} ({user['login']}):"]
    for l in leads:
        prev = l["user_id"][1] if l.get("user_id") else "Sin asignar"
        lines.append(f"  #{l['id']} {l['name']}  (antes: {prev})")

    if missing:
        lines.append(f"\n[!] IDs no encontrados y omitidos: {missing}")

    return "\n".join(lines)


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
def pago_registrar(
    factura_id: int,
    monto: float = 0,
    fecha: str = "",
    diario: str = ""
) -> str:
    """
    Register and reconcile a payment on a customer invoice using Odoo's payment wizard.
    Marks the invoice as paid (or partially paid) automatically.

    Args:
        factura_id: ID of the account.move invoice to pay
        monto: amount to pay — defaults to the invoice's full outstanding amount
        fecha: payment date YYYY-MM-DD — defaults to today
        diario: bank/cash journal name (partial match), e.g. 'Banco', 'Caja', 'BCI'
                If omitted, uses Odoo's default payment journal for the invoice.
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()

    # ── 1. Verify invoice exists and is payable ───────────────────────────────
    facturas = client.search_read(
        "account.move",
        [("id", "=", factura_id), ("move_type", "=", "out_invoice")],
        ["id", "name", "state", "payment_state", "amount_total",
         "amount_residual", "partner_id", "invoice_date", "currency_id"],
        limit=1
    )
    if not facturas:
        return f"[!] No se encontro factura de cliente con ID {factura_id}."

    inv = facturas[0]

    if inv.get("state") != "posted":
        return (
            f"[!] La factura #{factura_id} '{inv.get('name')}' esta en estado "
            f"'{inv.get('state')}'. Solo se pueden pagar facturas confirmadas (posted).\n"
            f"Usa factura_confirmar({factura_id}) primero."
        )

    pay_state = inv.get("payment_state", "")
    if pay_state in ("paid", "in_payment"):
        return (
            f"[!] La factura #{factura_id} '{inv.get('name')}' ya esta "
            f"{'pagada' if pay_state == 'paid' else 'en proceso de pago'}."
        )

    amount_residual = float(inv.get("amount_residual") or inv.get("amount_total") or 0)
    partner = str(inv["partner_id"][1] if inv.get("partner_id") else "")

    # ── 2. Resolve journal if provided ───────────────────────────────────────
    journal_id = None
    journal_name = None
    if diario:
        journals = client.search_read(
            "account.journal",
            [("name", "ilike", diario), ("type", "in", ["bank", "cash"])],
            ["id", "name"],
            limit=5
        )
        if not journals:
            all_journals = client.search_read(
                "account.journal",
                [("type", "in", ["bank", "cash"])],
                ["id", "name"],
                limit=20
            )
            opts = ", ".join(f"'{j['name']}'" for j in all_journals)
            return f"[!] No se encontro diario '{diario}'. Disponibles: {opts}"
        if len(journals) > 1:
            opts = ", ".join(f"'{j['name']}'" for j in journals)
            return f"[!] Varios diarios coinciden con '{diario}': {opts}. Sé mas especifico."
        journal_id   = journals[0]["id"]
        journal_name = journals[0]["name"]

    # ── 3. Use account.payment.register wizard ────────────────────────────────
    ctx = {
        "active_model": "account.move",
        "active_ids":   [factura_id],
        "active_id":    factura_id,
    }

    # Get wizard defaults (Odoo fills journal, currency, amount from the invoice)
    try:
        defaults = client.execute(
            "account.payment.register", "default_get",
            [["payment_date", "journal_id", "amount", "currency_id",
              "payment_type", "partner_type", "partner_id"]],
            {"context": ctx}
        ) or {}
    except Exception as e:
        return f"[!] Error al iniciar el wizard de pago: {e}"

    # Build wizard values — override only what the user specified
    wizard_vals: dict = {**defaults}
    if journal_id:
        wizard_vals["journal_id"] = journal_id
    if monto and monto > 0:
        wizard_vals["amount"] = monto
    if fecha:
        wizard_vals["payment_date"] = fecha
    elif not wizard_vals.get("payment_date"):
        wizard_vals["payment_date"] = datetime.now().strftime("%Y-%m-%d")

    effective_amount = float(wizard_vals.get("amount") or amount_residual)
    effective_date   = str(wizard_vals.get("payment_date", ""))

    # Create wizard record
    try:
        wizard_id = client.execute(
            "account.payment.register", "create",
            [wizard_vals],
            {"context": ctx}
        )
    except Exception as e:
        return f"[!] Error al crear el wizard de pago: {e}"

    if not wizard_id:
        return "[!] No se pudo crear el wizard de pago."

    # Execute payment (reconciles automatically)
    try:
        client.execute(
            "account.payment.register", "action_create_payments",
            [[wizard_id]],
            {"context": ctx}
        )
    except Exception as e:
        if "cannot marshal" in str(e) or "NoneType" in str(e):
            pass  # action returns a window action with None — payment was created OK
        else:
            return f"[!] Error al ejecutar el pago: {e}"

    # ── 4. Verify invoice is now paid ─────────────────────────────────────────
    updated = client.search_read(
        "account.move",
        [("id", "=", factura_id)],
        ["name", "payment_state", "amount_residual"],
        limit=1
    )
    new_state   = updated[0].get("payment_state", "?") if updated else "?"
    new_residual = float(updated[0].get("amount_residual") or 0) if updated else 0

    state_label = {
        "paid":       "PAGADA completamente",
        "in_payment": "EN PROCESO DE PAGO",
        "partial":    "PAGO PARCIAL",
        "not_paid":   "NO PAGADA (revisar)",
    }.get(new_state, new_state)

    return "\n".join([
        f"[OK] Pago registrado",
        f"",
        f"  Factura        : #{factura_id} {inv.get('name')}",
        f"  Cliente        : {partner}",
        f"  Monto pagado   : ${effective_amount:,.0f}",
        f"  Fecha          : {effective_date}",
        f"  Diario         : {journal_name or '(por defecto)'}",
        f"  Saldo pendiente: ${new_residual:,.0f}",
        f"  Estado         : {state_label}",
    ])


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
    Search an Odoo contact / customer by name, email, or RUT/VAT.

    Args:
        nombre: text to search in the contact name, email, or VAT/RUT number
        limite: max results
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    partners = client.search_read(
        "res.partner",
        ["|", "|", ("name", "ilike", nombre), ("email", "ilike", nombre), ("vat", "ilike", nombre)],
        ["name", "email", "phone", "vat", "customer_rank", "supplier_rank", "city", "country_id"],
        limit=limite
    )
    if not partners:
        return f"No se encontraron contactos con '{nombre}'."
    lines = [f"{'ID':<6} {'Nombre':<30} {'RUT/VAT':<15} {'Email':<28} {'Teléfono':<15} {'Ciudad'}"]
    lines.append("-" * 105)
    for p in partners:
        lines.append(
            f"{p['id']:<6} {str(p.get('name', ''))[:29]:<30} "
            f"{str(p.get('vat') or '-')[:14]:<15} "
            f"{str(p.get('email') or '')[:27]:<28} "
            f"{str(p.get('phone') or '')[:14]:<15} "
            f"{str(p.get('city') or '')}"
        )
    return "\n".join(lines)


@mcp.tool()
def odoo_actualizar_cliente(
    cliente_id: int,
    nombre: str = "",
    vat: str = "",
    email: str = "",
    telefono: str = "",
    ciudad: str = "",
    direccion: str = ""
) -> str:
    """
    Update fields on an existing Odoo contact / customer (res.partner).

    Args:
        cliente_id: numeric ID of the contact to update (use odoo_buscar_cliente to find it)
        nombre: new display name
        vat: RUT or tax identification number (e.g. '76.123.456-7')
        email: email address
        telefono: main phone number
        ciudad: city
        direccion: street address
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()

    # Verify the contact exists and fetch current values
    existing = client.search_read(
        "res.partner",
        [("id", "=", cliente_id)],
        ["name", "vat", "email", "phone", "city", "street"],
        limit=1
    )
    if not existing:
        return f"[!] No se encontró ningún contacto con ID {cliente_id}."

    current = existing[0]

    # Build update dict with only provided fields
    field_map = {
        "nombre":    ("name",   nombre),
        "vat":       ("vat",    vat),
        "email":     ("email",  email),
        "telefono":  ("phone",  telefono),
        "ciudad":    ("city",   ciudad),
        "direccion": ("street", direccion),
    }
    values: dict = {}
    changes: list = []
    for param, (odoo_field, new_val) in field_map.items():
        if new_val:
            old_val = current.get(odoo_field) or "-"
            values[odoo_field] = new_val
            changes.append(f"  {param:<12} {str(old_val):<30} → {new_val}")

    if not values:
        return "[!] No se indicó ningún campo para actualizar. Usa al menos uno: nombre, vat, email, telefono, movil, ciudad, direccion."

    client.write("res.partner", [cliente_id], values)

    lines = [f"[OK] Contacto #{cliente_id} '{current['name']}' actualizado:"]
    lines.append(f"  {'Campo':<12} {'Valor anterior':<30}   {'Valor nuevo'}")
    lines.append("  " + "-" * 70)
    lines.extend(changes)
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


@mcp.tool()
def actividad_crear(
    modelo: str,
    registro_id: int,
    tipo: str = "Correo electrónico",
    resumen: str = "",
    nota: str = "",
    fecha_limite: str = "",
    usuario: str = ""
) -> str:
    """
    Schedule a follow-up activity on any Odoo record (lead, invoice, subscription, contact, etc.).

    Args:
        modelo: Odoo model of the target record. Common values:
                'crm.lead'     — CRM leads/opportunities
                'account.move' — invoices
                'sale.order'   — subscriptions / sales orders
                'res.partner'  — contacts / customers
        registro_id: ID of the target record
        tipo: activity type name (partial match). Common types:
              'Correo electronico', 'Llamada', 'Reunion', 'Tarea', 'Subir documento'
              Defaults to email if not found.
        resumen: short title shown in the chatter (max ~80 chars)
        nota: longer description or instructions
        fecha_limite: due date YYYY-MM-DD (default: today)
        usuario: assign to this user by name (partial match). Defaults to current API user.
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()

    # ── 1. Resolve res_model_id (ir.model ID for the target model) ────────────
    ir_models = client.search_read(
        "ir.model",
        [("model", "=", modelo)],
        ["id", "name"],
        limit=1
    )
    if not ir_models:
        return (
            f"[!] Modelo '{modelo}' no encontrado en Odoo.\n"
            f"Valores comunes: 'crm.lead', 'account.move', 'sale.order', 'res.partner'"
        )
    res_model_id = ir_models[0]["id"]
    model_name   = ir_models[0]["name"]

    # ── 2. Verify the target record exists ────────────────────────────────────
    record = client.search_read(
        modelo,
        [("id", "=", registro_id)],
        ["id", "name"] if modelo != "account.move" else ["id", "name", "partner_id"],
        limit=1
    )
    if not record:
        return f"[!] No se encontro el registro #{registro_id} en '{modelo}'."
    record_name = str(record[0].get("name") or registro_id)

    # ── 3. Resolve activity type ──────────────────────────────────────────────
    act_types = client.search_read(
        "mail.activity.type",
        [("name", "ilike", tipo)],
        ["id", "name"],
        limit=5
    )
    if not act_types:
        # Fallback: list available types so the user can choose
        all_types = client.search_read(
            "mail.activity.type", [], ["id", "name"], limit=20
        )
        type_list = ", ".join(f"'{t['name']}'" for t in all_types)
        return (
            f"[!] No se encontro un tipo de actividad con '{tipo}'.\n"
            f"Tipos disponibles: {type_list}"
        )

    if len(act_types) > 1:
        opciones = ", ".join(f"'{t['name']}'" for t in act_types)
        act_type = act_types[0]  # pick closest
    else:
        act_type = act_types[0]

    # ── 4. Resolve assigned user ──────────────────────────────────────────────
    user_id = None
    user_name = None
    if usuario:
        users = client.search_read(
            "res.users",
            [("name", "ilike", usuario), ("active", "=", True)],
            ["id", "name"],
            limit=5
        )
        if not users:
            return f"[!] No se encontro ningun usuario con '{usuario}'."
        if len(users) > 1:
            opciones = ", ".join(f"'{u['name']}'" for u in users)
            return (
                f"[!] Varios usuarios coinciden con '{usuario}': {opciones}\n"
                f"Usa un nombre mas especifico."
            )
        user_id   = users[0]["id"]
        user_name = users[0]["name"]

    # ── 5. Build date_deadline ────────────────────────────────────────────────
    if not fecha_limite:
        fecha_limite = datetime.now().strftime("%Y-%m-%d")

    # ── 6. Create the activity ────────────────────────────────────────────────
    values: dict = {
        "res_model_id":      res_model_id,
        "res_id":            registro_id,
        "activity_type_id":  act_type["id"],
        "date_deadline":     fecha_limite,
    }
    if resumen:
        values["summary"] = resumen
    if nota:
        values["note"] = nota
    if user_id:
        values["user_id"] = user_id

    try:
        activity_id = client.create("mail.activity", values)
    except Exception as e:
        return f"[!] Error al crear la actividad: {e}"

    return "\n".join([
        f"[OK] Actividad agendada (ID {activity_id})",
        f"",
        f"  Tipo           : {act_type['name']}",
        f"  Registro       : {model_name} #{registro_id} — {record_name}",
        f"  Resumen        : {resumen or '(sin resumen)'}",
        f"  Fecha limite   : {fecha_limite}",
        f"  Asignado a     : {user_name or '(usuario actual)'}",
        f"  Nota           : {nota[:80] + '...' if len(nota) > 80 else nota or '(sin nota)'}",
    ])


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


@mcp.tool()
def suscripcion_detalle(suscripcion_id: int) -> str:
    """
    Full detail of a single subscription: header, product lines, recent invoices,
    payment status and next renewal date.

    Args:
        suscripcion_id: ID of the subscription (sale.order with is_subscription=True)
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()

    # ── 1. Header fields — request all useful ones, handle missing gracefully ─
    header_fields = [
        "name", "partner_id", "user_id", "team_id",
        "subscription_state", "amount_total", "amount_untaxed",
        "recurring_monthly", "currency_id",
        "date_order", "next_invoice_date", "last_invoice_date",
        "payment_term_id", "plan_id",
        "client_order_ref", "note",
        "invoice_ids", "order_line",
        "first_contract_date",
    ]
    try:
        rows = client.search_read(
            "sale.order",
            [("id", "=", suscripcion_id), ("is_subscription", "=", True)],
            header_fields,
            limit=1
        )
    except Exception:
        # Retry without optional fields that may not exist in this Odoo version
        rows = client.search_read(
            "sale.order",
            [("id", "=", suscripcion_id), ("is_subscription", "=", True)],
            ["name", "partner_id", "user_id", "subscription_state",
             "amount_total", "recurring_monthly", "currency_id",
             "date_order", "next_invoice_date", "invoice_ids", "order_line"],
            limit=1
        )

    if not rows:
        return (
            f"[!] No se encontro suscripcion con ID {suscripcion_id}.\n"
            f"Usa suscripciones_listar() para ver los IDs disponibles."
        )

    s = rows[0]

    # ── 2. Order lines (products / plan details) ──────────────────────────────
    line_ids = s.get("order_line") or []
    lines_data = []
    if line_ids:
        try:
            lines_data = client.search_read(
                "sale.order.line",
                [("id", "in", line_ids)],
                ["name", "product_id", "product_uom_qty", "price_unit",
                 "price_subtotal", "recurring_monthly"],
                limit=20
            )
        except Exception:
            lines_data = []

    # ── 3. Recent invoices (last 6) ───────────────────────────────────────────
    invoice_ids = s.get("invoice_ids") or []
    invoices = []
    if invoice_ids:
        try:
            invoices = client.search_read(
                "account.move",
                [("id", "in", invoice_ids), ("move_type", "=", "out_invoice")],
                ["name", "invoice_date", "amount_total", "state", "payment_state"],
                limit=6,
                order="invoice_date desc"
            )
        except Exception:
            invoices = []

    # ── 4. Helpers ────────────────────────────────────────────────────────────
    def _val(field, default="-"):
        v = s.get(field)
        if v is None or v is False:
            return default
        if isinstance(v, (list, tuple)) and len(v) > 1:
            return str(v[1])
        return str(v)

    STATE_LABELS = {
        "1_draft":    "Borrador",
        "2_renewal":  "En renovación",
        "3_progress": "Activa",
        "4_paused":   "Pausada",
        "5_close":    "Cerrada",
        "6_churn":    "Cancelada (churn)",
    }
    PAYMENT_LABELS = {
        "not_paid":   "Sin pagar",
        "in_payment": "En proceso",
        "paid":       "Pagada",
        "partial":    "Pago parcial",
        "reversed":   "Revertida",
    }

    state_raw = s.get("subscription_state", "")
    state_label = STATE_LABELS.get(state_raw, state_raw)

    currency = _val("currency_id", "")
    mrr = s.get("recurring_monthly") or 0
    total = s.get("amount_total") or 0

    sep = "─" * 56

    # ── 5. Build output ───────────────────────────────────────────────────────
    out = [
        f"{'═'*58}",
        f"  SUSCRIPCIÓN #{suscripcion_id}  —  {_val('name')}",
        f"{'═'*58}",
        "",
        f"  CLIENTE",
        f"  {sep}",
        f"  Nombre          : {_val('partner_id')}",
        f"  Vendedor        : {_val('user_id')}",
        f"  Equipo          : {_val('team_id')}",
        "",
        f"  ESTADO",
        f"  {sep}",
        f"  Estado          : {state_label}",
        f"  Plan            : {_val('plan_id')}",
        f"  Ref. cliente    : {_val('client_order_ref')}",
        "",
        f"  FECHAS",
        f"  {sep}",
        f"  Inicio contrato : {_val('first_contract_date') or _val('date_order')}",
        f"  Ultima factura  : {_val('last_invoice_date')}",
        f"  Proxima factura : {_val('next_invoice_date')}",
        f"  Plazo de pago   : {_val('payment_term_id')}",
        "",
        f"  MONTO",
        f"  {sep}",
        f"  MRR             : {currency} {mrr:,.0f}" if mrr else f"  MRR             : -",
        f"  Total contrato  : {currency} {total:,.0f}",
    ]

    # Product lines
    if lines_data:
        out += ["", f"  LINEAS DEL PLAN", f"  {sep}",
                f"  {'Producto':<38} {'Cant':>5}  {'Precio':>12}  {'Subtotal':>12}"]
        out.append(f"  {'─'*72}")
        for ln in lines_data:
            prod = str(ln.get("name") or (ln["product_id"][1] if ln.get("product_id") else ""))
            qty  = ln.get("product_uom_qty") or 0
            pu   = ln.get("price_unit") or 0
            sub  = ln.get("price_subtotal") or 0
            out.append(
                f"  {prod[:37]:<38} {qty:>5.0f}  {currency} {pu:>10,.0f}  {currency} {sub:>10,.0f}"
            )
    else:
        out += ["", "  LINEAS DEL PLAN", f"  {sep}", "  (sin líneas disponibles)"]

    # Recent invoices
    if invoices:
        out += ["", f"  FACTURAS RECIENTES ({len(invoice_ids)} total)", f"  {sep}",
                f"  {'Numero':<16} {'Fecha':<12} {'Total':>12}  {'Estado':<10}  {'Pago'}"]
        out.append(f"  {'─'*68}")
        for inv in invoices:
            pstate = PAYMENT_LABELS.get(inv.get("payment_state", ""), inv.get("payment_state", ""))
            out.append(
                f"  {str(inv.get('name') or '')[:15]:<16} "
                f"{str(inv.get('invoice_date') or ''):<12} "
                f"{currency} {inv.get('amount_total', 0):>10,.0f}  "
                f"{str(inv.get('state') or '')[:9]:<10}  "
                f"{pstate}"
            )
    elif invoice_ids:
        out += ["", f"  FACTURAS ({len(invoice_ids)} vinculadas — no son de cliente)", f"  {sep}"]
    else:
        out += ["", f"  FACTURAS", f"  {sep}", "  Sin facturas vinculadas"]

    # Notes
    note = s.get("note") or ""
    if note:
        import re
        clean_note = re.sub(r'<[^>]+>', '', note).strip()[:200]
        if clean_note:
            out += ["", f"  NOTAS", f"  {sep}", f"  {clean_note}"]

    out.append("")
    return "\n".join(out)


@mcp.tool()
def suscripciones_metricas(
    fecha_desde: str = "",
    fecha_hasta: str = "",
    agrupar_por_vendedor: bool = False
) -> str:
    """
    SaaS subscription metrics: MRR, ARR, active count, new, churned and churn rate.

    Args:
        fecha_desde: start of the period YYYY-MM-DD (for new/churned counts)
        fecha_hasta: end of the period YYYY-MM-DD (for new/churned counts)
        agrupar_por_vendedor: if True, include a breakdown by salesperson
    """
    from datetime import date, datetime

    client = get_client()
    if client is None:
        return _not_configured_msg()

    # ── 1. Pull ALL subscriptions (no limit) ──────────────────────────────────
    fields = [
        "id", "name", "partner_id", "user_id",
        "subscription_state", "amount_total", "recurring_monthly",
        "date_order", "next_invoice_date"
    ]
    try:
        all_subs = client.search_read(
            "sale.order",
            [("is_subscription", "=", True)],
            fields,
            limit=2000,
            order="date_order desc"
        )
    except Exception as e:
        return f"[!] Error leyendo suscripciones: {e}"

    if not all_subs:
        return "No se encontraron suscripciones en el sistema."

    # ── 2. Helper: get monthly value ──────────────────────────────────────────
    def mrr_of(s):
        rm = s.get("recurring_monthly")
        if rm:
            return float(rm)
        # fallback: amount_total is likely annual for yearly plans
        return float(s.get("amount_total") or 0) / 12

    # ── 3. Classify by state ──────────────────────────────────────────────────
    # Odoo 17-19 subscription_state values:
    #   1_draft, 2_renewal, 3_progress, 4_paused, 5_close, 6_churn
    ACTIVE_STATES  = {"3_progress", "2_renewal"}
    CHURNED_STATES = {"6_churn", "5_close"}

    active   = [s for s in all_subs if s.get("subscription_state") in ACTIVE_STATES]
    churned  = [s for s in all_subs if s.get("subscription_state") in CHURNED_STATES]
    draft    = [s for s in all_subs if s.get("subscription_state") == "1_draft"]
    paused   = [s for s in all_subs if s.get("subscription_state") == "4_paused"]

    # ── 4. Core metrics ───────────────────────────────────────────────────────
    mrr = sum(mrr_of(s) for s in active)
    arr = mrr * 12

    # ── 5. Period metrics (new & churned in date window) ─────────────────────
    period_label = ""
    new_in_period: list = []
    churned_in_period: list = []

    if fecha_desde or fecha_hasta:
        def in_range(date_str):
            if not date_str:
                return False
            d = str(date_str)[:10]
            if fecha_desde and d < fecha_desde:
                return False
            if fecha_hasta and d > fecha_hasta:
                return False
            return True

        new_in_period     = [s for s in all_subs if in_range(s.get("date_order"))]
        churned_in_period = [s for s in all_subs
                             if s.get("subscription_state") in CHURNED_STATES
                             and in_range(s.get("date_order"))]

        period_label = f"  {fecha_desde or '?'} → {fecha_hasta or 'hoy'}"
    else:
        period_label = "  (sin filtro de periodo — muestra totales históricos)"

    # Churn rate = churned / (active + churned) if we have period data
    total_for_churn = len(active) + len(churned)
    churn_rate = (len(churned) / total_for_churn * 100) if total_for_churn > 0 else 0

    # ── 6. Format output ──────────────────────────────────────────────────────
    sep  = "─" * 52
    sep2 = "─" * 52

    lines = [
        "╔══════════════════════════════════════════════════════╗",
        "║          MÉTRICAS DE SUSCRIPCIONES — mitimbre        ║",
        "╚══════════════════════════════════════════════════════╝",
        "",
        "  INGRESOS RECURRENTES",
        sep,
        f"  MRR (mensual)          $ {mrr:>14,.0f}",
        f"  ARR (anual)            $ {arr:>14,.0f}",
        "",
        "  SUSCRIPCIONES",
        sep,
        f"  Activas                  {len(active):>6}",
        f"  En renovación            {len([s for s in active if s.get('subscription_state') == '2_renewal']):>6}",
        f"  Pausadas                 {len(paused):>6}",
        f"  Borrador                 {len(draft):>6}",
        f"  Canceladas / Churn       {len(churned):>6}",
        f"  TOTAL                    {len(all_subs):>6}",
        "",
        "  CHURN",
        sep,
        f"  Churn rate (histórico)   {churn_rate:>5.1f}%",
    ]

    if fecha_desde or fecha_hasta:
        lines += [
            "",
            f"  PERIODO{period_label}",
            sep,
            f"  Nuevas suscripciones     {len(new_in_period):>6}",
            f"  MRR nuevas           $ {sum(mrr_of(s) for s in new_in_period):>14,.0f}",
            f"  Canceladas periodo       {len(churned_in_period):>6}",
            f"  MRR perdido          $ {sum(mrr_of(s) for s in churned_in_period):>14,.0f}",
        ]
        net_new = len(new_in_period) - len(churned_in_period)
        net_mrr = sum(mrr_of(s) for s in new_in_period) - sum(mrr_of(s) for s in churned_in_period)
        lines += [
            f"  Net new subs             {net_new:>+6}",
            f"  Net MRR              $ {net_mrr:>+14,.0f}",
        ]

    # ── 7. Salesperson breakdown ──────────────────────────────────────────────
    if agrupar_por_vendedor:
        from collections import defaultdict
        vend: dict = defaultdict(lambda: {"count": 0, "mrr": 0.0})
        for s in active:
            nombre = s["user_id"][1] if s.get("user_id") else "Sin asignar"
            vend[nombre]["count"] += 1
            vend[nombre]["mrr"]   += mrr_of(s)

        lines += [
            "",
            "  POR VENDEDOR (activas)",
            sep2,
            f"  {'Vendedor':<25} {'Subs':>5}  {'MRR':>14}",
            "  " + "─" * 48,
        ]
        for nombre, datos in sorted(vend.items(), key=lambda x: -x[1]["mrr"]):
            pct = datos["mrr"] / mrr * 100 if mrr else 0
            lines.append(
                f"  {nombre[:24]:<25} {datos['count']:>5}  $ {datos['mrr']:>12,.0f}  ({pct:.0f}%)"
            )

    lines.append("")
    return "\n".join(lines)


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
              "clicked", "schedule_date", "contact_list_ids", "reply_to"]
    try:
        mailings = client.search_read("mailing.mailing", domain, fields, limit=limite, order="write_date desc")
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
            f"{str(m.get('schedule_date', '') or '')[:10]}"
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


@mcp.tool()
def nomina_recibos(
    empleado: str = "",
    anio: int = 0,
    mes: int = 0,
    estado: str = "all",
    limite: int = 20
) -> str:
    """List payslips (recibos de salario) with filters.

    Args:
        empleado: filter by employee name (partial, empty = all)
        anio: year e.g. 2026 (0 = current year)
        mes: month 1-12 (0 = all months)
        estado: 'draft', 'verify', 'done', 'paid', 'cancel', 'all'
        limite: max results
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()

    from datetime import datetime
    now = datetime.now()
    if anio == 0:
        anio = now.year

    domain = []
    if estado != "all":
        domain.append(["state", "=", estado])
    if mes:
        month_str = f"{anio}-{mes:02d}"
        domain.append(["date_from", ">=", f"{month_str}-01"])
        import calendar
        last_day = calendar.monthrange(anio, mes)[1]
        domain.append(["date_to", "<=", f"{month_str}-{last_day:02d}"])
    else:
        domain.append(["date_from", ">=", f"{anio}-01-01"])
        domain.append(["date_to", "<=", f"{anio}-12-31"])

    if empleado:
        domain.append(["employee_id.name", "ilike", empleado])

    fields = ["name", "employee_id", "department_id", "date_from", "date_to",
              "state", "basic_wage", "gross_wage", "net_wage", "employer_cost",
              "paid", "paid_date", "currency_id"]
    try:
        slips = client.search_read("hr.payslip", domain, fields,
                                   limit=limite, order="date_from desc")
    except Exception as e:
        return f"[!] Could not read payslips: {e}"

    if not slips:
        return "No payslips found for the given filters."

    lines = [f"{'ID':<5} {'Employee':<22} {'Period':<14} {'State':<8} "
             f"{'Net Wage':>12} {'Paid'}"]
    lines.append("-" * 75)
    for s in slips:
        emp = str(s.get("employee_id", [0, ""])[1])[:21]
        d_from = str(s.get("date_from", ""))[:7]
        state = str(s.get("state", ""))
        net = s.get("net_wage", 0)
        currency = str(s.get("currency_id", [0, ""])[1])
        paid = "Yes" if s.get("paid") else "No"
        lines.append(
            f"{s['id']:<5} {emp:<22} {d_from:<14} {state:<8} "
            f"{net:>12,.0f} {currency}  {paid}"
        )

    total_net = sum(s.get("net_wage", 0) for s in slips)
    currency = str(slips[0].get("currency_id", [0, ""])[1]) if slips else ""
    lines.append("-" * 75)
    lines.append(f"{'Total net wage:':<42} {total_net:>12,.0f} {currency}  ({len(slips)} slips)")
    return "\n".join(lines)


@mcp.tool()
def nomina_detalle(recibo_id: int) -> str:
    """Get full detail of a payslip including all salary component lines.

    Args:
        recibo_id: numeric payslip ID
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()

    slip_fields = ["name", "employee_id", "department_id", "job_id",
                   "date_from", "date_to", "state", "struct_id",
                   "basic_wage", "gross_wage", "net_wage", "employer_cost",
                   "sum_worked_hours", "paid", "paid_date", "currency_id",
                   "note", "payslip_run_id"]
    try:
        slips = client.search_read("hr.payslip", [["id", "=", recibo_id]],
                                   slip_fields, limit=1)
    except Exception as e:
        return f"[!] Could not read payslip: {e}"

    if not slips:
        return f"Payslip ID {recibo_id} not found."

    s = slips[0]
    currency = str(s.get("currency_id", [0, ""])[1])

    out = [
        f"Payslip: {s.get('name', '')}",
        f"Employee:   {s.get('employee_id', [0,''])[1]}",
        f"Department: {s.get('department_id', [0,''])[1]}",
        f"Job:        {s.get('job_id', [0,''])[1]}",
        f"Period:     {s.get('date_from','')} to {s.get('date_to','')}",
        f"Structure:  {s.get('struct_id', [0,''])[1]}",
        f"Pay Run:    {s.get('payslip_run_id', [0,''])[1] or '(none)'}",
        f"State:      {s.get('state','')}",
        f"Worked hrs: {s.get('sum_worked_hours', 0):.1f} h",
        "",
        f"{'Component':<35} {'Category':<20} {'Amount':>14}",
        "-" * 72,
    ]

    # Salary lines
    line_fields = ["name", "code", "category_id", "amount", "total",
                   "quantity", "rate", "appears_on_payslip", "ytd"]
    try:
        lines = client.search_read(
            "hr.payslip.line",
            [["slip_id", "=", recibo_id], ["appears_on_payslip", "=", True]],
            line_fields,
            order="sequence asc"
        )
    except Exception as e:
        lines = []
        out.append(f"(could not load lines: {e})")

    for ln in lines:
        cat = str(ln.get("category_id", [0, ""])[1])[:19]
        total = ln.get("total", ln.get("amount", 0))
        ytd = ln.get("ytd", 0)
        name = str(ln.get("name", ""))[:34]
        out.append(
            f"{name:<35} {cat:<20} {total:>14,.0f}"
            + (f"  (YTD: {ytd:,.0f})" if ytd else "")
        )

    out += [
        "-" * 72,
        f"{'Basic Wage:':<55} {s.get('basic_wage',0):>14,.0f} {currency}",
        f"{'Gross Wage:':<55} {s.get('gross_wage',0):>14,.0f} {currency}",
        f"{'Net Wage:':<55} {s.get('net_wage',0):>14,.0f} {currency}",
        f"{'Employer Cost:':<55} {s.get('employer_cost',0):>14,.0f} {currency}",
    ]
    if s.get("paid"):
        out.append(f"{'Paid on:':<55} {s.get('paid_date','')}")
    if s.get("note"):
        out.append(f"\nNote: {s['note']}")

    return "\n".join(out)


@mcp.tool()
def nomina_resumen_mes(anio: int = 0, mes: int = 0) -> str:
    """Monthly payroll summary grouped by employee showing net wages and costs.

    Args:
        anio: year (0 = current year)
        mes: month 1-12 (0 = current month)
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()

    from datetime import datetime
    import calendar
    now = datetime.now()
    if anio == 0:
        anio = now.year
    if mes == 0:
        mes = now.month

    month_str = f"{anio}-{mes:02d}"
    last_day = calendar.monthrange(anio, mes)[1]
    domain = [
        ["date_from", ">=", f"{month_str}-01"],
        ["date_to", "<=", f"{month_str}-{last_day:02d}"],
        ["state", "!=", "cancel"],
    ]
    fields = ["employee_id", "department_id", "basic_wage", "gross_wage",
              "net_wage", "employer_cost", "state", "paid", "currency_id"]
    try:
        slips = client.search_read("hr.payslip", domain, fields,
                                   limit=200, order="employee_id asc")
    except Exception as e:
        return f"[!] Could not read payroll: {e}"

    if not slips:
        return f"No payslips found for {month_str}."

    currency = str(slips[0].get("currency_id", [0, ""])[1]) if slips else ""
    month_name = datetime(anio, mes, 1).strftime("%B %Y")

    lines = [
        f"Payroll summary — {month_name}",
        "",
        f"{'Employee':<28} {'Department':<25} {'Net Wage':>14} {'Empl.Cost':>13} {'Paid'}",
        "-" * 88,
    ]

    total_net = 0
    total_cost = 0
    for s in slips:
        emp = str(s.get("employee_id", [0, ""])[1])[:27]
        dept = str(s.get("department_id", [0, ""])[1])[:24]
        net = s.get("net_wage", 0)
        cost = s.get("employer_cost", 0)
        paid = "Yes" if s.get("paid") else "No"
        total_net += net
        total_cost += cost
        lines.append(
            f"{emp:<28} {dept:<25} {net:>14,.0f} {cost:>13,.0f}  {paid}"
        )

    lines += [
        "-" * 88,
        f"{'TOTAL':<53} {total_net:>14,.0f} {total_cost:>13,.0f}",
        f"",
        f"Headcount: {len(slips)} employee(s)   Currency: {currency}",
        f"Paid: {sum(1 for s in slips if s.get('paid'))} / {len(slips)}",
    ]
    return "\n".join(lines)


@mcp.tool()
def marketing_aperturas(campana_id: int = 0, buscar_campana: str = "", solo_leads: bool = False) -> str:
    """Show contacts who opened an email from a marketing campaign, cross-referenced with CRM leads.

    Args:
        campana_id: mailing ID (use 0 to auto-pick the last sent campaign)
        buscar_campana: filter campaigns by subject to find the right one
        solo_leads: if True, only show contacts that also have a CRM lead
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()

    # Step 1: find campaign
    if campana_id == 0:
        domain = [("state", "=", "done")]
        if buscar_campana:
            domain.append(("subject", "ilike", buscar_campana))
        try:
            mailings = client.search_read(
                "mailing.mailing", domain,
                ["id", "subject", "sent", "opened", "clicked", "schedule_date"],
                limit=1, order="write_date desc"
            )
        except Exception as e:
            return f"[!] Could not read campaigns: {e}"
        if not mailings:
            # Try any state if no done campaigns
            try:
                mailings = client.search_read(
                    "mailing.mailing", [] if not buscar_campana else [("subject", "ilike", buscar_campana)],
                    ["id", "subject", "sent", "opened", "clicked", "schedule_date"],
                    limit=1, order="write_date desc"
                )
            except Exception as e:
                return f"[!] Could not read campaigns: {e}"
        if not mailings:
            return "No campaigns found."
        mailing = mailings[0]
        campana_id = mailing["id"]
    else:
        try:
            mailings = client.search_read(
                "mailing.mailing", [["id", "=", campana_id]],
                ["id", "subject", "sent", "opened", "clicked", "schedule_date"],
                limit=1
            )
        except Exception as e:
            return f"[!] Could not read campaign {campana_id}: {e}"
        if not mailings:
            return f"Campaign ID {campana_id} not found."
        mailing = mailings[0]

    subj = mailing.get("subject", "")
    sent = mailing.get("sent", 0) or 0
    opened = mailing.get("opened", 0) or 0
    date = str(mailing.get("schedule_date", "") or "")[:10]

    # Step 2: get traces with 'open' status
    # Odoo 19 fields: open_datetime, res_id (many2one_reference), model, email
    safe_fields = ["res_id", "model", "email", "trace_status", "open_datetime",
                   "links_click_datetime", "sent_datetime"]
    try:
        traces = client.search_read(
            "mailing.trace",
            [["mass_mailing_id", "=", campana_id], ["trace_status", "in", ["open", "reply"]]],
            safe_fields,
            limit=200
        )
    except Exception as e:
        return (
            f"Campaign: {subj} (ID {campana_id})\n"
            f"Sent: {sent}  Opened: {opened}  Date: {date}\n\n"
            f"[!] Could not read mailing traces: {e}"
        )

    if not traces:
        return (
            f"Campaign: {subj}\n"
            f"Sent: {sent}  Opened: {opened}  Date: {date}\n\n"
            f"No open traces found for this campaign."
        )

    # Step 3: collect emails and contact names
    # Traces target mailing.contact via (model=mailing.contact, res_id=id)
    # We match CRM leads by email_from
    emails = [t.get("email", "") for t in traces if t.get("email")]

    # Batch-read mailing.contact names for display
    contact_ids_by_model: dict = {}
    for t in traces:
        m = t.get("model") or ""
        rid = t.get("res_id")
        if m and rid:
            contact_ids_by_model.setdefault(m, []).append(rid)

    names_by_model: dict = {}
    for model, ids in contact_ids_by_model.items():
        ids = list(set(i for i in ids if i))
        if not ids:
            continue
        try:
            recs = client.search_read(model, [["id", "in", ids]],
                                      ["id", "name"], limit=300)
            names_by_model[model] = {r["id"]: r.get("name", "") for r in recs}
        except Exception:
            names_by_model[model] = {}

    # Find CRM leads by email
    leads_by_email: dict = {}
    if emails:
        try:
            leads = client.search_read(
                "crm.lead",
                [["email_from", "in", emails]],
                ["id", "name", "email_from", "stage_id", "expected_revenue", "probability"],
                limit=300
            )
            for l in leads:
                key = str(l.get("email_from", "")).lower().strip()
                if key:
                    leads_by_email[key] = l
        except Exception:
            pass

    # Step 4: render
    lines = [
        f"Campaign: {subj}",
        f"Date: {date}  |  Sent: {sent}  |  Opened: {opened}",
        f"Contacts who opened: {len(traces)}",
        "",
        f"{'Email':<36} {'Name':<28} {'Opened':<18} {'CRM Lead'}",
        "-" * 108,
    ]

    shown = 0
    with_lead = 0
    for t in sorted(traces, key=lambda x: str(x.get("open_datetime") or "")):
        email = str(t.get("email", "") or "")
        model = t.get("model") or ""
        res_id = t.get("res_id")
        open_dt = str(t.get("open_datetime", "") or "")[:16]
        clicked = "✓" if t.get("links_click_datetime") else ""

        contact_name = names_by_model.get(model, {}).get(res_id, "") if res_id else ""
        crm = leads_by_email.get(email.lower().strip())

        if solo_leads and not crm:
            continue

        if crm:
            stage = crm.get("stage_id", [0, ""])[1] if crm.get("stage_id") else ""
            rev = crm.get("expected_revenue", 0) or 0
            lead_str = f"[{crm['id']}] {str(crm.get('name',''))[:25]} | {stage} | ${rev:,.0f}"
            with_lead += 1
        else:
            lead_str = "(no CRM lead)"

        lines.append(
            f"{email[:35]:<36} {str(contact_name)[:27]:<28} {open_dt:<18} {lead_str} {clicked}"
        )
        shown += 1

    if shown == 0:
        lines.append("(no results match the filters)")

    lines.append("-" * 108)
    lines.append(f"Total opened: {shown}  |  With CRM lead: {with_lead}  |  Without lead: {shown - with_lead}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
#  INVOICING / ATTACHMENTS
# ---------------------------------------------------------------------------

@mcp.tool()
def facturas_cliente_listar(
    buscar: str = "",
    fecha_desde: str = "",
    fecha_hasta: str = "",
    estado: str = "posted",
    limite: int = 20
) -> str:
    """
    List customer invoices (account.move with move_type='out_invoice').

    Args:
        buscar: filter by customer name or invoice number
        fecha_desde: start date YYYY-MM-DD (filters on invoice_date)
        fecha_hasta: end date YYYY-MM-DD (filters on invoice_date)
        estado: 'draft', 'posted', 'cancel', 'all' (default: 'posted')
        limite: max results (default 20)
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()

    domain: list = [("move_type", "=", "out_invoice")]
    if estado != "all":
        domain.append(("state", "=", estado))
    if fecha_desde:
        domain.append(("invoice_date", ">=", fecha_desde))
    if fecha_hasta:
        domain.append(("invoice_date", "<=", fecha_hasta))
    if buscar:
        domain.append("|")
        domain.append(("partner_id.name", "ilike", buscar))
        domain.append(("name", "ilike", buscar))

    fields = [
        "id", "name", "partner_id", "amount_total", "amount_untaxed",
        "state", "invoice_date", "invoice_date_due", "ref",
        "invoice_origin", "payment_state"
    ]
    invoices = client.search_read("account.move", domain, fields, limit=limite, order="invoice_date desc")

    if not invoices:
        return "No se encontraron facturas con los filtros indicados."

    lines = [
        f"{'ID':<6} {'Número':<14} {'Cliente':<28} {'Fecha':<12} {'Vence':<12} "
        f"{'Total':>12} {'Pago':<14} {'Origen'}"
    ]
    lines.append("-" * 115)
    for inv in invoices:
        partner = str(inv["partner_id"][1] if inv.get("partner_id") else "")[:27]
        lines.append(
            f"{inv['id']:<6} "
            f"{str(inv.get('name') or '')[:13]:<14} "
            f"{partner:<28} "
            f"{str(inv.get('invoice_date') or ''):<12} "
            f"{str(inv.get('invoice_date_due') or ''):<12} "
            f"${inv.get('amount_total', 0):>10,.0f} "
            f"{str(inv.get('payment_state') or '')[:13]:<14} "
            f"{str(inv.get('invoice_origin') or inv.get('ref') or '')[:20]}"
        )
    return "\n".join(lines)


@mcp.tool()
def factura_crear(
    cliente: str,
    lineas: list,
    fecha_factura: str = "",
    fecha_vencimiento: str = "",
    referencia: str = "",
    notas: str = ""
) -> str:
    """
    Create a customer invoice (account.move, move_type='out_invoice') in draft state.

    Args:
        cliente: customer name, RUT/VAT, or email — used to look up res.partner.
                 If multiple matches, the tool returns the options and asks to clarify.
        lineas: list of invoice line dicts. Each line must have:
                  - 'descripcion' (str, required): line name / description
                  - 'precio'      (float, required): unit price
                  - 'cantidad'    (float, optional, default 1): quantity
                  - 'producto_id' (int, optional): product ID to link the line to
        fecha_factura:    invoice date YYYY-MM-DD (default: today)
        fecha_vencimiento: due date YYYY-MM-DD (default: Odoo payment terms)
        referencia: customer PO or external reference
        notas: internal notes / narration

    Example:
        factura_crear(
            cliente="Edificio Urbano Nunoa",
            lineas=[
                {"descripcion": "Suscripcion Mayo 2026 - Plan Pro", "precio": 150000, "cantidad": 1},
                {"descripcion": "Soporte adicional", "precio": 25000}
            ],
            referencia="OC-2026-05"
        )
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()

    if not lineas:
        return "[!] Debes incluir al menos una linea en el parametro 'lineas'."

    # ── 1. Resolve customer ───────────────────────────────────────────────────
    partners = client.search_read(
        "res.partner",
        ["|", "|",
         ("name", "ilike", cliente),
         ("vat", "ilike", cliente),
         ("email", "ilike", cliente)],
        ["id", "name", "vat", "email"],
        limit=5
    )
    if not partners:
        return f"[!] No se encontro ningun cliente con '{cliente}'. Verifica el nombre, RUT o email."

    if len(partners) > 1:
        opciones = "\n".join(
            f"  #{p['id']} {p['name']}"
            f"{' | RUT: ' + p['vat'] if p.get('vat') else ''}"
            f"{' | ' + p['email'] if p.get('email') else ''}"
            for p in partners
        )
        return (
            f"[!] Se encontraron {len(partners)} clientes con '{cliente}':\n"
            f"{opciones}\n\n"
            f"Usa un nombre mas especifico o el RUT exacto para crear la factura."
        )

    partner = partners[0]
    partner_id = partner["id"]

    # ── 2. Build invoice lines ────────────────────────────────────────────────
    invoice_lines = []
    errores = []
    for i, linea in enumerate(lineas, start=1):
        desc  = linea.get("descripcion") or linea.get("name") or linea.get("description")
        precio = linea.get("precio") or linea.get("price_unit") or linea.get("price")
        if not desc:
            errores.append(f"Linea {i}: falta 'descripcion'")
            continue
        if precio is None:
            errores.append(f"Linea {i}: falta 'precio'")
            continue
        cantidad = float(linea.get("cantidad") or linea.get("quantity") or 1)
        line_vals = {
            "name":       str(desc),
            "price_unit": float(precio),
            "quantity":   cantidad,
        }
        if linea.get("producto_id"):
            line_vals["product_id"] = int(linea["producto_id"])
        invoice_lines.append((0, 0, line_vals))

    if errores:
        return "[!] Errores en las lineas:\n" + "\n".join(f"  - {e}" for e in errores)

    if not invoice_lines:
        return "[!] No se pudo construir ninguna linea valida."

    # ── 3. Build invoice header ───────────────────────────────────────────────
    values: dict = {
        "move_type":          "out_invoice",
        "partner_id":         partner_id,
        "invoice_line_ids":   invoice_lines,
    }
    if fecha_factura:
        values["invoice_date"] = fecha_factura
    if fecha_vencimiento:
        values["invoice_date_due"] = fecha_vencimiento
    if referencia:
        values["ref"] = referencia
    if notas:
        values["narration"] = notas

    # ── 4. Create in Odoo ─────────────────────────────────────────────────────
    try:
        factura_id = client.create("account.move", values)
    except Exception as e:
        return f"[!] Error al crear la factura: {e}"

    # ── 5. Read back to confirm ───────────────────────────────────────────────
    created = client.search_read(
        "account.move",
        [("id", "=", factura_id)],
        ["name", "amount_untaxed", "amount_tax", "amount_total",
         "state", "invoice_date", "invoice_date_due"],
        limit=1
    )
    if not created:
        return f"[OK] Factura creada con ID {factura_id} (no se pudo leer el detalle)."

    inv = created[0]
    total_lineas = sum(
        float(l.get("precio") or l.get("price_unit") or 0)
        * float(l.get("cantidad") or l.get("quantity") or 1)
        for l in lineas
    )

    lines_out = [
        f"[OK] Factura creada en borrador",
        f"",
        f"  ID             : {factura_id}",
        f"  Numero         : {inv.get('name') or '(asignado al confirmar)'}",
        f"  Cliente        : {partner['name']}"
        + (f" — RUT {partner['vat']}" if partner.get('vat') else ""),
        f"  Fecha          : {inv.get('invoice_date') or '(hoy al confirmar)'}",
        f"  Vencimiento    : {inv.get('invoice_date_due') or '(segun plazo de pago)'}",
        f"  Referencia     : {referencia or '-'}",
        f"",
        f"  {'Descripcion':<40} {'Cant':>5}  {'Precio':>12}",
        f"  {'─'*62}",
    ]
    for linea in lineas:
        desc  = str(linea.get("descripcion") or linea.get("name") or "")
        cant  = float(linea.get("cantidad") or 1)
        precio = float(linea.get("precio") or linea.get("price_unit") or 0)
        lines_out.append(
            f"  {desc[:39]:<40} {cant:>5.0f}  ${precio:>11,.0f}"
        )
    lines_out += [
        f"  {'─'*62}",
        f"  {'TOTAL':<46} ${inv.get('amount_total', total_lineas):>11,.0f}",
        f"",
        f"  Estado         : BORRADOR — usa factura_confirmar({factura_id}) para postear",
    ]
    return "\n".join(lines_out)


@mcp.tool()
def adjuntar_archivo(
    modelo: str,
    registro_id: int,
    nombre_archivo: str,
    contenido_base64: str,
    mimetype: str = "application/pdf"
) -> str:
    """
    Attach a base64-encoded file to any Odoo record via ir.attachment.

    Args:
        modelo: Odoo model name, e.g. 'account.move' or 'sale.order'
        registro_id: ID of the record to attach the file to
        nombre_archivo: file name, e.g. '143.pdf'
        contenido_base64: file contents encoded as base64 string
        mimetype: MIME type (default 'application/pdf')
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    values = {
        "name": nombre_archivo,
        "res_model": modelo,
        "res_id": registro_id,
        "datas": contenido_base64,
        "mimetype": mimetype,
        "type": "binary",
    }
    attachment_id = client.create("ir.attachment", values)
    if attachment_id:
        return (
            f"[OK] Archivo adjuntado.\n"
            f"  attachment_id : {attachment_id}\n"
            f"  nombre        : {nombre_archivo}\n"
            f"  modelo        : {modelo} #{registro_id}"
        )
    return "[!] No se pudo crear el adjunto."


@mcp.tool()
def factura_confirmar(factura_id: int) -> str:
    """
    Confirm (post) a draft customer invoice in Odoo.
    Assigns the official invoice number and makes it payable.

    Args:
        factura_id: ID of the account.move to confirm
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()

    facturas = client.search_read(
        "account.move",
        [("id", "=", factura_id)],
        ["id", "name", "state", "partner_id", "amount_total",
         "invoice_date", "move_type"],
        limit=1
    )
    if not facturas:
        return f"[!] No se encontro factura con ID {factura_id}."

    inv = facturas[0]

    if inv.get("move_type") != "out_invoice":
        return f"[!] El registro #{factura_id} no es una factura de cliente."

    state = inv.get("state")
    if state == "posted":
        return (
            f"[!] La factura #{factura_id} '{inv.get('name')}' ya esta confirmada (posted).\n"
            f"  Cliente : {inv['partner_id'][1] if inv.get('partner_id') else '-'}\n"
            f"  Total   : ${inv.get('amount_total', 0):,.0f}"
        )
    if state == "cancel":
        return f"[!] La factura #{factura_id} esta cancelada y no se puede confirmar."

    client.call("account.move", "action_post", [factura_id])

    updated = client.search_read(
        "account.move",
        [("id", "=", factura_id)],
        ["name", "state", "payment_state", "amount_total", "invoice_date"],
        limit=1
    )
    if not updated:
        return f"[OK] Factura #{factura_id} confirmada (no se pudo leer el resultado)."

    inv2 = updated[0]
    return "\n".join([
        f"[OK] Factura confirmada",
        f"",
        f"  ID             : {factura_id}",
        f"  Numero         : {inv2.get('name') or '(sin numero)'}",
        f"  Cliente        : {inv['partner_id'][1] if inv.get('partner_id') else '-'}",
        f"  Fecha          : {inv2.get('invoice_date') or '-'}",
        f"  Total          : ${inv2.get('amount_total', 0):,.0f}",
        f"  Estado         : {inv2.get('state')} / {inv2.get('payment_state')}",
    ])


@mcp.tool()
def cliente_crear(
    nombre: str,
    vat: str = "",
    email: str = "",
    telefono: str = "",
    ciudad: str = "",
    direccion: str = ""
) -> str:
    """
    Create a new customer contact in Odoo (res.partner).

    Args:
        nombre: full name of the customer (required)
        vat: RUT or tax ID (e.g. '76.123.456-7')
        email: email address
        telefono: phone number
        ciudad: city
        direccion: street address
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()

    existing = client.search_read(
        "res.partner",
        [("name", "=", nombre)],
        ["id", "name", "vat"],
        limit=3
    )
    if existing:
        opts = "\n".join(
            f"  #{p['id']} {p['name']}{' — RUT: ' + p['vat'] if p.get('vat') else ''}"
            for p in existing
        )
        return (
            f"[!] Ya existe(n) contacto(s) con el nombre '{nombre}':\n{opts}\n\n"
            f"Usa odoo_actualizar_cliente para modificar uno existente."
        )

    values: dict = {"name": nombre, "customer_rank": 1}
    if vat:
        values["vat"] = vat
    if email:
        values["email"] = email
    if telefono:
        values["phone"] = telefono
    if ciudad:
        values["city"] = ciudad
    if direccion:
        values["street"] = direccion

    try:
        partner_id = client.create("res.partner", values)
    except Exception as e:
        return f"[!] Error al crear el cliente: {e}"

    return "\n".join([
        f"[OK] Cliente creado",
        f"",
        f"  ID       : {partner_id}",
        f"  Nombre   : {nombre}",
        f"  RUT/VAT  : {vat or '-'}",
        f"  Email    : {email or '-'}",
        f"  Telefono : {telefono or '-'}",
        f"  Ciudad   : {ciudad or '-'}",
    ])


@mcp.tool()
def suscripcion_facturas(suscripcion_id: int) -> str:
    """
    List all customer invoices linked to a subscription (sale.order).

    Args:
        suscripcion_id: ID of the subscription / sale order
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()

    orden = client.search_read(
        "sale.order",
        [("id", "=", suscripcion_id)],
        ["id", "name", "partner_id", "invoice_ids"],
        limit=1
    )
    if not orden:
        return f"[!] No se encontro suscripcion/orden con ID {suscripcion_id}."

    orden = orden[0]
    invoice_ids = orden.get("invoice_ids") or []
    if not invoice_ids:
        return f"La suscripcion #{suscripcion_id} '{orden.get('name')}' no tiene facturas vinculadas."

    facturas = client.search_read(
        "account.move",
        [("id", "in", invoice_ids), ("move_type", "=", "out_invoice")],
        ["id", "name", "amount_total", "state", "invoice_date", "payment_state", "ref"],
        limit=100,
        order="invoice_date desc"
    )
    if not facturas:
        return f"La suscripcion #{suscripcion_id} no tiene facturas de cliente vinculadas."

    cliente = str(orden["partner_id"][1] if orden.get("partner_id") else "")
    lines = [
        f"Suscripcion #{suscripcion_id} -- {orden.get('name')} -- Cliente: {cliente}",
        f"{len(facturas)} factura(s):",
        "",
        f"{'ID':<6} {'Numero':<14} {'Fecha':<12} {'Total':>12} {'Estado':<10} {'Pago':<16} {'Ref'}"
    ]
    lines.append("-" * 85)
    for fac in facturas:
        lines.append(
            f"{fac['id']:<6} "
            f"{str(fac.get('name') or '')[:13]:<14} "
            f"{str(fac.get('invoice_date') or ''):<12} "
            f"${fac.get('amount_total', 0):>10,.0f} "
            f"{str(fac.get('state') or '')[:9]:<10} "
            f"{str(fac.get('payment_state') or '')[:15]:<16} "
            f"{str(fac.get('ref') or '')[:20]}"
        )
    return "\n".join(lines)


@mcp.tool()
def factura_obtener_url(registro_id: int, modelo: str = "account.move") -> str:
    """
    Build the web URL to open an Odoo record directly in the browser.

    Args:
        registro_id: numeric ID of the record
        modelo: Odoo model (default 'account.move' for invoices)
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    model_routes = {
        "account.move": "odoo/accounting/customer-invoices",
        "sale.order":   "odoo/sales/orders",
        "crm.lead":     "odoo/crm",
        "res.partner":  "odoo/contacts",
    }
    route = model_routes.get(modelo, f"odoo/{modelo.replace('.', '-')}")
    base_url = (client.url or "").rstrip("/")
    return f"URL: {base_url}/{route}/{registro_id}"


@mcp.tool()
def actualizar_lineas_factura(factura_id: int, lineas: list) -> str:
    """
    Update description/price/qty of invoice lines.
    Resets to draft if posted, updates, then re-confirms automatically.

    Args:
        factura_id: ID of the account.move
        lineas: list of dicts — each needs 'id' plus any of:
                'descripcion', 'precio', 'cantidad'
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    if not lineas:
        return "[!] Debes pasar al menos una linea."

    facturas = client.search_read(
        "account.move", [("id", "=", factura_id)],
        ["id", "name", "state"], limit=1
    )
    if not facturas:
        return f"[!] No se encontro factura con ID {factura_id}."

    factura = facturas[0]
    estado_original = factura["state"]
    if estado_original == "posted":
        client.call("account.move", "button_draft", [factura_id])

    line_ids = [l["id"] for l in lineas if "id" in l]
    current_lines = client.search_read(
        "account.move.line",
        [("id", "in", line_ids), ("move_id", "=", factura_id)],
        ["id", "name", "price_unit", "quantity"],
        limit=len(line_ids) + 1
    )
    current_map = {l["id"]: l for l in current_lines}

    missing = [lid for lid in line_ids if lid not in current_map]
    if missing:
        if estado_original == "posted":
            client.call("account.move", "action_post", [factura_id])
        return f"[!] Lineas no encontradas en factura #{factura_id}: {missing}"

    changes = []
    for linea in lineas:
        lid = linea.get("id")
        if not lid:
            continue
        values = {}
        diffs = []
        cur = current_map.get(lid, {})
        if "descripcion" in linea:
            values["name"] = linea["descripcion"]
            diffs.append(f"desc: '{cur.get('name','')}' -> '{linea['descripcion']}'")
        if "precio" in linea:
            values["price_unit"] = linea["precio"]
            diffs.append(f"precio: {cur.get('price_unit',0):,.0f} -> {linea['precio']:,.0f}")
        if "cantidad" in linea:
            values["quantity"] = linea["cantidad"]
            diffs.append(f"cant: {cur.get('quantity',0)} -> {linea['cantidad']}")
        if values:
            client.write("account.move.line", [lid], values)
            changes.append(f"  Linea #{lid}: " + " | ".join(diffs))

    if estado_original == "posted":
        client.call("account.move", "action_post", [factura_id])

    if not changes:
        return "[!] No se realizaron cambios."

    out = [f"[OK] Factura #{factura_id} '{factura.get('name')}' actualizada:", ""]
    out.extend(changes)
    if estado_original == "posted":
        out += ["", "  (Factura re-confirmada automaticamente)"]
    return "\n".join(out)



@mcp.tool()
def factura_enviar_email(factura_id: int, email_destino: str = "") -> str:
    """
    Send a confirmed customer invoice by email via Odoo.

    Args:
        factura_id:    ID of the account.move (must be in 'posted' state)
        email_destino: optional override recipient email; if empty uses the
                       customer's email on file
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()

    facturas = client.search_read(
        "account.move",
        [("id", "=", factura_id)],
        ["id", "name", "state", "move_type", "partner_id",
         "amount_total", "currency_id", "invoice_date", "invoice_date_due"],
        limit=1,
    )
    if not facturas:
        return f"[!] No se encontro factura con ID {factura_id}."

    factura = facturas[0]
    if factura["state"] != "posted":
        estado = factura["state"]
        return (
            f"[!] La factura #{factura_id} no esta confirmada (estado: {estado}). "
            "Usa factura_confirmar primero."
        )
    if factura["move_type"] not in ("out_invoice", "out_refund"):
        return "[!] Solo se pueden enviar facturas de cliente (out_invoice / out_refund)."

    # Resolve recipient email
    partner_id = factura["partner_id"][0] if factura.get("partner_id") else None
    partner_email = ""
    partner_name = ""
    if partner_id:
        partners = client.search_read(
            "res.partner", [("id", "=", partner_id)], ["name", "email"], limit=1
        )
        if partners:
            partner_name = partners[0].get("name", "")
            partner_email = partners[0].get("email", "") or ""

    recipient = (email_destino or partner_email).strip()
    if not recipient:
        return (
            f"[!] No hay email destino. El cliente '{partner_name}' no tiene email "
            "registrado. Pasa 'email_destino' como argumento."
        )

    # --- Strategy: use message_post to send the invoice PDF by email ---
    # Odoo's message_post on account.move triggers the standard email flow
    # (subtype 'account.mt_invoice_validated' already exists in Odoo 17+).
    # We look up the partner_id of the recipient so Odoo logs the follower.
    recipient_partner_ids = []
    if partner_id and not email_destino:
        recipient_partner_ids = [partner_id]
    elif email_destino:
        # Try to find a partner matching the override email
        matches = client.search_read(
            "res.partner", [("email", "=", email_destino)], ["id", "name"], limit=1
        )
        if matches:
            recipient_partner_ids = [matches[0]["id"]]

    # Build a minimal email body
    nombre_factura = factura.get("name", f"#{factura_id}")
    fecha_factura  = factura.get("invoice_date", "") or ""
    fecha_venc     = factura.get("invoice_date_due", "") or ""
    cur            = factura["currency_id"][1] if factura.get("currency_id") else ""
    monto          = factura.get("amount_total", 0)

    body_html = (
        f"<p>Estimado/a {partner_name},</p>"
        f"<p>Adjuntamos la factura <strong>{nombre_factura}</strong>"
        + (f" con fecha {fecha_factura}" if fecha_factura else "")
        + f" por un total de <strong>{monto:,.0f} {cur}</strong>"
        + (f" con vencimiento {fecha_venc}" if fecha_venc else "")
        + ".</p>"
        "<p>Quedamos atentos ante cualquier consulta.</p>"
    )

    try:
        client.execute(
            "account.move",
            "message_post",
            [[factura_id]],
            {
                "body":            body_html,
                "message_type":    "email",
                "partner_ids":     recipient_partner_ids,
                "email_from":      False,   # use company default
                "subtype_xmlid":   "mail.mt_comment",
            },
        )
        enviado_ok = True
    except Exception as exc:
        enviado_ok = False
        err_msg = str(exc)

    if not enviado_ok:
        return f"[!] Error al enviar el email: {err_msg}"

    out = [
        f"[OK] Email enviado para factura {nombre_factura}",
        f"  Destinatario : {recipient}",
        f"  Cliente      : {partner_name}",
        f"  Monto        : {monto:,.0f} {cur}",
    ]
    if fecha_factura:
        out.append(f"  Fecha        : {fecha_factura}")
    if fecha_venc:
        out.append(f"  Vencimiento  : {fecha_venc}")
    return "\n".join(out)


@mcp.tool()
def factura_adjuntos_listar(factura_id: int) -> str:
    """
    List all file attachments linked to a customer invoice (account.move).

    Args:
        factura_id: ID of the account.move
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()

    # Verify invoice exists
    facturas = client.search_read(
        "account.move", [("id", "=", factura_id)],
        ["id", "name", "partner_id", "state"], limit=1
    )
    if not facturas:
        return f"[!] No se encontro factura con ID {factura_id}."

    factura = facturas[0]
    nombre_factura = factura.get("name", f"#{factura_id}")
    partner = factura["partner_id"][1] if factura.get("partner_id") else ""

    # Query ir.attachment for this record
    adjuntos = client.search_read(
        "ir.attachment",
        [("res_model", "=", "account.move"), ("res_id", "=", factura_id)],
        ["id", "name", "mimetype", "file_size", "create_date", "create_uid", "type", "url"],
        limit=50,
        order="create_date desc",
    )

    if not adjuntos:
        return (
            f"Factura {nombre_factura} ({partner}) no tiene archivos adjuntos."
        )

    lines = [
        f"Adjuntos de factura {nombre_factura} — {partner}",
        f"Total: {len(adjuntos)} archivo(s)",
        "",
        f"{'ID':<7} {'Nombre':<40} {'Tipo':<25} {'Tamaño':>10}  {'Subido por':<20}  Fecha",
        "-" * 115,
    ]
    for adj in adjuntos:
        size_kb = (adj.get("file_size") or 0) / 1024
        size_str = f"{size_kb:,.1f} KB" if size_kb < 1024 else f"{size_kb/1024:,.2f} MB"
        nombre = str(adj.get("name") or "")[:39]
        mime = str(adj.get("mimetype") or adj.get("type") or "")[:24]
        uploader = str(adj["create_uid"][1] if adj.get("create_uid") else "")[:19]
        fecha = str(adj.get("create_date") or "")[:16]
        lines.append(
            f"{adj['id']:<7} {nombre:<40} {mime:<25} {size_str:>10}  {uploader:<20}  {fecha}"
        )

    return "\n".join(lines)


@mcp.tool()
def facturacion_mensual_resumen(mes: str) -> str:
    """
    Full monthly billing dashboard in a single call.

    Returns a JSON array — one entry per active subscription — with its
    invoice for the requested month (if any), attachment list, and a
    trailing "_resumen" summary object.

    Args:
        mes: month in "YYYY-MM" format (e.g. "2026-05")
    """
    import json
    import re
    import calendar

    client = get_client()
    if client is None:
        return _not_configured_msg()

    # --- Validate and expand month ----------------------------------------
    if not re.match(r"^\d{4}-\d{2}$", mes):
        return "[!] Formato invalido. Usa 'YYYY-MM' (ej: '2026-05')."
    year, month = int(mes[:4]), int(mes[5:7])
    fecha_desde = f"{mes}-01"
    last_day    = calendar.monthrange(year, month)[1]
    fecha_hasta = f"{mes}-{last_day:02d}"

    # --- 1. Active subscriptions ------------------------------------------
    ACTIVE_STATES = ["3_progress", "2_renewal"]
    subs = client.search_read(
        "sale.order",
        [("is_subscription", "=", True),
         ("subscription_state", "in", ACTIVE_STATES)],
        ["id", "name", "partner_id", "recurring_monthly",
         "amount_total", "invoice_ids"],
        limit=500,
        order="name asc",
    )
    if not subs:
        return json.dumps(
            [{"_resumen": {"total_suscripciones": 0, "con_factura": 0,
                           "sin_factura": 0, "con_pdf_sii": 0,
                           "monto_total": 0, "monto_facturado": 0,
                           "monto_pendiente": 0}}],
            ensure_ascii=False, indent=2,
        )

    # --- 2. Batch VAT lookup -----------------------------------------------
    partner_ids = list({s["partner_id"][0] for s in subs if s.get("partner_id")})
    partners_raw = client.search_read(
        "res.partner",
        [("id", "in", partner_ids)],
        ["id", "vat"],
        limit=len(partner_ids) + 1,
    )
    vat_map = {p["id"]: (p.get("vat") or "") for p in partners_raw}

    # --- 3. Batch invoice lookup for the month ----------------------------
    all_invoice_ids: list = []
    sub_invoice_ids: dict = {}
    for s in subs:
        ids = s.get("invoice_ids") or []
        sub_invoice_ids[s["id"]] = ids
        all_invoice_ids.extend(ids)

    invoice_map: dict = {}   # invoice_id -> invoice dict
    sub_inv_map: dict  = {}  # sub_id     -> invoice dict (first match in month)

    if all_invoice_ids:
        invoices = client.search_read(
            "account.move",
            [("id", "in", all_invoice_ids),
             ("move_type", "=", "out_invoice"),
             ("invoice_date", ">=", fecha_desde),
             ("invoice_date", "<=", fecha_hasta)],
            ["id", "name", "state", "payment_state",
             "invoice_date", "amount_total", "partner_id"],
            limit=1000,
        )
        for inv in invoices:
            invoice_map[inv["id"]] = inv

        for s in subs:
            for iid in sub_invoice_ids.get(s["id"], []):
                if iid in invoice_map:
                    sub_inv_map[s["id"]] = invoice_map[iid]
                    break

    # --- 4. Batch attachment lookup ---------------------------------------
    matched_ids = list(invoice_map.keys())
    attach_map: dict = {}   # invoice_id -> [filename, ...]

    if matched_ids:
        attachments = client.search_read(
            "ir.attachment",
            [("res_model", "=", "account.move"),
             ("res_id", "in", matched_ids)],
            ["id", "name", "res_id"],
            limit=2000,
        )
        for att in attachments:
            rid = att["res_id"]
            attach_map.setdefault(rid, []).append(att.get("name") or "")

    # --- 5. Build result --------------------------------------------------
    SII_PDF = re.compile(r"^\d+\.pdf$", re.IGNORECASE)
    result   = []
    monto_total      = 0
    monto_facturado  = 0
    con_factura      = 0
    con_pdf_sii      = 0

    for s in subs:
        pid   = s["partner_id"][0]   if s.get("partner_id") else None
        pname = s["partner_id"][1]   if s.get("partner_id") else ""
        mrr   = s.get("recurring_monthly") or s.get("amount_total") or 0
        monto_total += mrr

        inv      = sub_inv_map.get(s["id"])
        archivos = attach_map.get(inv["id"], []) if inv else []
        tiene_sii_pdf = any(SII_PDF.match(f) for f in archivos)

        if inv:
            con_factura     += 1
            monto_facturado += mrr
            if tiene_sii_pdf:
                con_pdf_sii += 1

        result.append({
            "suscripcion_id":  s["id"],
            "suscripcion_num": s.get("name", ""),
            "cliente":         pname,
            "rut":             vat_map.get(pid, "") if pid else "",
            "monto":           mrr,
            "factura": {
                "id":     inv["id"],
                "numero": inv.get("name", ""),
                "estado": inv.get("state", ""),
                "pago":   inv.get("payment_state", ""),
                "fecha":  str(inv.get("invoice_date") or ""),
                "total":  inv.get("amount_total", 0),
            } if inv else None,
            "adjuntos": {
                "total":    len(archivos),
                "archivos": archivos,
            } if inv else {"total": 0, "archivos": []},
        })

    total_subs       = len(subs)
    monto_pendiente  = monto_total - monto_facturado

    result.append({
        "_resumen": {
            "total_suscripciones": total_subs,
            "con_factura":         con_factura,
            "sin_factura":         total_subs - con_factura,
            "con_pdf_sii":         con_pdf_sii,
            "monto_total":         monto_total,
            "monto_facturado":     monto_facturado,
            "monto_pendiente":     monto_pendiente,
        }
    })

    return json.dumps(result, ensure_ascii=False, indent=2)

if __name__ == "__main__" or True:
    mcp.run()
