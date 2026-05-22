“””
Odoo MCP Server - Claude connector for Odoo Online & Community
Modules: CRM, Sales, Expenses, Bank Reconciliation

Configuration via environment variables or interactive setup wizard:
  ODOO_URL      -> https://yourcompany.odoo.com
  ODOO_DB       -> database name
  ODOO_USERNAME -> your Odoo login email
  ODOO_API_KEY  -> API key from Odoo > Preferences > Security

Run ‘odoo_setup’ tool if not configured yet.
“””

import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv, set_key
from mcp.server.fastmcp import FastMCP, Context
from odoo_client import OdooClient

ENV_PATH = Path(__file__).parent / “.env”
load_dotenv(dotenv_path=ENV_PATH)

# ── Initialization ────────────────────────────────────────────────────────────

mcp = FastMCP(“Odoo Connector”)

def _credentials_missing() -> bool:
    return not all([
        os.environ.get(“ODOO_URL”),
        os.environ.get(“ODOO_DB”),
        os.environ.get(“ODOO_USERNAME”),
        os.environ.get(“ODOO_API_KEY”),
    ])

def get_client() -> OdooClient:
    if _credentials_missing():
        return None
    return OdooClient(
        os.environ[“ODOO_URL”],
        os.environ[“ODOO_DB”],
        os.environ[“ODOO_USERNAME”],
        os.environ[“ODOO_API_KEY”],
    )

def _not_configured_msg() -> str:
    return (
        “⚠️ Odoo connector is not configured yet.\n”
        “Run **odoo_setup** to connect to your Odoo instance. “
        “I’ll guide you through it step by step.”
    )


# ── Setup Wizard ──────────────────────────────────────────────────────────────

@mcp.tool()
async def odoo_setup(ctx: Context) -> str:
    “””
    Interactive setup wizard. Connects Claude to your Odoo instance step by step.
    Run this first if you haven’t configured the connector yet.
    “””
    # Step 1: URL
    url_result = await ctx.elicit(
        message=(
            “Welcome to the **Odoo Connector** setup! 🎉\n\n”
            “I’ll connect Claude to your Odoo instance in 4 quick steps.\n\n”
            “**Step 1/4** — What is your Odoo URL?\n”
            “*(e.g., https://mycompany.odoo.com)*”
        ),
        schema={“type”: “object”, “properties”: {“value”: {“type”: “string”, “title”: “Odoo URL”}}, “required”: [“value”]},
    )
    if url_result.action != “accept”:
        return “Setup cancelled.”
    url = url_result.data[“value”].rstrip(“/”)

    # Step 2: Database
    db_result = await ctx.elicit(
        message=(
            “**Step 2/4** — What is your database name?\n”
            “*(For Odoo SaaS this is your subdomain — e.g., for mycompany.odoo.com use `mycompany`)*”
        ),
        schema={“type”: “object”, “properties”: {“value”: {“type”: “string”, “title”: “Database name”}}, “required”: [“value”]},
    )
    if db_result.action != “accept”:
        return “Setup cancelled.”
    db = db_result.data[“value”].strip()

    # Step 3: Username
    user_result = await ctx.elicit(
        message=(
            “**Step 3/4** — What is your Odoo login email?”
        ),
        schema={“type”: “object”, “properties”: {“value”: {“type”: “string”, “title”: “Email”}}, “required”: [“value”]},
    )
    if user_result.action != “accept”:
        return “Setup cancelled.”
    username = user_result.data[“value”].strip()

    # Step 4: API Key
    key_result = await ctx.elicit(
        message=(
            “**Step 4/4** — Paste your Odoo API Key.\n\n”
            “To get one: Odoo → click your avatar → **Preferences** → “
            “**Security** tab → **API Keys** → **New Key**”
        ),
        schema={“type”: “object”, “properties”: {“value”: {“type”: “string”, “title”: “API Key”}}, “required”: [“value”]},
    )
    if key_result.action != “accept”:
        return “Setup cancelled.”
    api_key = key_result.data[“value”].strip()

    # Save to .env
    ENV_PATH.touch(exist_ok=True)
    set_key(str(ENV_PATH), “ODOO_URL”, url)
    set_key(str(ENV_PATH), “ODOO_DB”, db)
    set_key(str(ENV_PATH), “ODOO_USERNAME”, username)
    set_key(str(ENV_PATH), “ODOO_API_KEY”, api_key)

    # Reload env vars in current process
    os.environ[“ODOO_URL”] = url
    os.environ[“ODOO_DB”] = db
    os.environ[“ODOO_USERNAME”] = username
    os.environ[“ODOO_API_KEY”] = api_key

    # Test connection
    try:
        client = OdooClient(url, db, username, api_key)
        uid = client.authenticate()
        version = client.get_server_version().get(“server_version”, “N/A”)
        return (
            f”✅ Connected to Odoo successfully!\n”
            f”Version: {version} | User UID: {uid}\n\n”
            f”You’re all set. Try asking:\n”
            f”- *Show me the CRM pipeline*\n”
            f”- *What sales did we confirm this month?*\n”
            f”- *Are there expenses pending approval?*”
        )
    except Exception as e:
        return (
            f”❌ Could not connect: {e}\n\n”
            f”Please check:\n”
            f”- URL has no trailing slash\n”
            f”- Database name is exact (case-sensitive)\n”
            f”- API key is active\n\n”
            f”Run **odoo_setup** again to retry.”
        )


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  ðŸ”Œ CONEXIÃ“N / DIAGNÃ“STICO
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@mcp.tool()
def odoo_ping() -> str:
    """Verifica la conexiÃ³n con Odoo y retorna la versiÃ³n del servidor."""
    client = get_client()
    if client is None:
        return _not_configured_msg()
    version = client.get_server_version()
    uid = client.authenticate()
    return (
        f"âœ… Conectado a Odoo\n"
        f"VersiÃ³n: {version.get('server_version', 'N/A')}\n"
        f"UID de usuario: {uid}"
    )


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  ðŸ“Š CRM â€” Oportunidades / Leads
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@mcp.tool()
def crm_listar_oportunidades(
    estado: str = "open",
    limite: int = 15,
    buscar: str = ""
) -> str:
    """
    Lista oportunidades/leads del CRM.

    Args:
        estado: 'open' (activas), 'won' (ganadas), 'lost' (perdidas), 'all' (todas)
        limite: cantidad mÃ¡xima de resultados (default 15)
        buscar: texto para filtrar por nombre del lead o cliente
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
              "user_id", "date_deadline", "probability", "tag_ids"]
    leads = client.search_read("crm.lead", domain, fields, limit=limite, order="expected_revenue desc")

    if not leads:
        return "No se encontraron oportunidades con esos filtros."

    lines = [f"{'#':<4} {'Oportunidad':<30} {'Cliente':<25} {'Etapa':<20} {'Valor Est.':<12} {'Prob%':<7} {'Cierre'}"]
    lines.append("-" * 110)
    for l in leads:
        lines.append(
            f"{l['id']:<4} "
            f"{str(l['name'])[:29]:<30} "
            f"{str(l.get('partner_name') or '')[:24]:<25} "
            f"{str(l['stage_id'][1] if l.get('stage_id') else '')[:19]:<20} "
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
    Crea una nueva oportunidad en el CRM.

    Args:
        nombre: nombre/tÃ­tulo de la oportunidad (requerido)
        cliente: nombre del cliente/empresa
        valor_esperado: monto esperado de la venta
        fecha_cierre: fecha lÃ­mite en formato YYYY-MM-DD
        vendedor_email: email del vendedor asignado
        notas: descripciÃ³n interna
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

    # Buscar usuario por email si se proveyÃ³
    if vendedor_email:
        users = client.search_read("res.users", [("login", "=", vendedor_email)], ["id", "name"], limit=1)
        if users:
            values["user_id"] = users[0]["id"]

    lead_id = client.create("crm.lead", values)
    return f"âœ… Oportunidad creada con ID {lead_id}: '{nombre}'"


@mcp.tool()
def crm_actualizar_etapa(
    oportunidad_id: int,
    etapa_nombre: str
) -> str:
    """
    Mueve una oportunidad a una nueva etapa del pipeline.

    Args:
        oportunidad_id: ID de la oportunidad
        etapa_nombre: nombre (parcial) de la etapa destino
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    stages = client.search_read("crm.stage", [("name", "ilike", etapa_nombre)], ["id", "name"], limit=5)
    if not stages:
        return f"âŒ No se encontrÃ³ ninguna etapa con el nombre '{etapa_nombre}'."
    stage = stages[0]
    client.write("crm.lead", [oportunidad_id], {"stage_id": stage["id"]})
    return f"âœ… Oportunidad {oportunidad_id} movida a etapa '{stage['name']}'"


@mcp.tool()
def crm_resumen_pipeline() -> str:
    """Muestra un resumen del pipeline CRM agrupado por etapa con totales."""
    client = get_client()
    if client is None:
        return _not_configured_msg()
    leads = client.search_read(
        "crm.lead",
        [("active", "=", True), ("stage_id.is_won", "=", False), ("type", "=", "opportunity")],
        ["stage_id", "expected_revenue", "probability"],
        limit=500
    )
    pipeline: dict[str, dict] = {}
    for l in leads:
        stage = l["stage_id"][1] if l.get("stage_id") else "Sin etapa"
        if stage not in pipeline:
            pipeline[stage] = {"count": 0, "total": 0, "weighted": 0}
        pipeline[stage]["count"] += 1
        pipeline[stage]["total"] += l.get("expected_revenue", 0)
        pipeline[stage]["weighted"] += l.get("expected_revenue", 0) * l.get("probability", 0) / 100

    lines = [f"{'Etapa':<28} {'Opps':>5} {'Valor Total':>14} {'Valor Ponderado':>16}"]
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


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  ðŸ’° VENTAS â€” Ã“rdenes de Venta
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@mcp.tool()
def ventas_listar_ordenes(
    estado: str = "sale",
    limite: int = 15,
    dias: int = 30,
    buscar: str = ""
) -> str:
    """
    Lista Ã³rdenes de venta.

    Args:
        estado: 'draft' (cotizaciÃ³n), 'sale' (confirmada), 'done' (facturada), 'cancel' (cancelada), 'all'
        limite: cantidad mÃ¡xima de resultados
        dias: filtrar Ã³rdenes de los Ãºltimos N dÃ­as (0 = sin filtro)
        buscar: texto para filtrar por nombre de cliente u orden
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
              "user_id", "invoice_status", "currency_id"]
    orders = client.search_read("sale.order", domain, fields, limit=limite, order="date_order desc")

    if not orders:
        return "No se encontraron Ã³rdenes de venta."

    estado_map = {"draft": "CotizaciÃ³n", "sent": "Enviada", "sale": "Confirmada",
                  "done": "Facturada", "cancel": "Cancelada"}
    lines = [f"{'#Orden':<12} {'Cliente':<28} {'Total':>12} {'Estado':<12} {'Fact.':<12} {'Fecha'}"]
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
    Muestra el detalle completo de una orden de venta incluyendo lÃ­neas de producto.

    Args:
        orden_id: ID numÃ©rico de la orden de venta
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    orders = client.read("sale.order", [orden_id],
        ["name", "partner_id", "amount_untaxed", "amount_tax", "amount_total",
         "state", "date_order", "user_id", "order_line", "note", "invoice_status"])
    if not orders:
        return f"Orden {orden_id} no encontrada."
    o = orders[0]

    lines_data = client.read("sale.order.line", o["order_line"],
        ["product_id", "product_uom_qty", "price_unit", "price_subtotal", "name"])

    output = [
        f"ðŸ“‹ Orden: {o['name']}",
        f"Cliente: {o['partner_id'][1] if o.get('partner_id') else 'N/A'}",
        f"Fecha:   {str(o.get('date_order', ''))[:16]}",
        f"Estado:  {o.get('state', '')} | FacturaciÃ³n: {o.get('invoice_status', '')}",
        f"Vendedor:{o['user_id'][1] if o.get('user_id') else 'N/A'}",
        "",
        f"{'Producto':<35} {'Cant':>6} {'Precio':>12} {'Subtotal':>12}",
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
        f"{'Impuestos':>56} ${o.get('amount_tax', 0):>11,.2f}",
        f"{'TOTAL':>56} ${o.get('amount_total', 0):>11,.2f}",
    ])
    if o.get("note"):
        output += ["", f"Nota: {o['note']}"]
    return "\n".join(output)


@mcp.tool()
def ventas_resumen_mes(anio: int = 0, mes: int = 0) -> str:
    """
    Resumen de ventas confirmadas del mes indicado (o del mes actual si no se especifica).

    Args:
        anio: aÃ±o (ej: 2025), 0 = aÃ±o actual
        mes: mes numÃ©rico 1-12, 0 = mes actual
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
    by_vendor: dict[str, float] = {}
    for o in orders:
        v = o["user_id"][1] if o.get("user_id") else "Sin asignar"
        by_vendor[v] = by_vendor.get(v, 0) + o["amount_total"]

    lines = [
        f"ðŸ“… Resumen de Ventas â€” {mes:02d}/{anio}",
        f"Total Ã³rdenes: {len(orders)}  |  Total facturado: ${total:,.2f}",
        "",
        f"{'Vendedor':<30} {'Ventas':>8} {'Total':>14}",
        "-" * 55,
    ]
    vendor_counts: dict[str, int] = {}
    for o in orders:
        v = o["user_id"][1] if o.get("user_id") else "Sin asignar"
        vendor_counts[v] = vendor_counts.get(v, 0) + 1

    for v, total_v in sorted(by_vendor.items(), key=lambda x: -x[1]):
        lines.append(f"{v[:29]:<30} {vendor_counts[v]:>8} ${total_v:>13,.2f}")
    return "\n".join(lines)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  ðŸ§¾ GASTOS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@mcp.tool()
def gastos_listar(
    estado: str = "draft",
    empleado: str = "",
    limite: int = 20
) -> str:
    """
    Lista gastos de empleados.

    Args:
        estado: 'draft' (borrador), 'reported' (reportado), 'approved' (aprobado),
                'done' (pagado), 'refused' (rechazado), 'all'
        empleado: nombre (parcial) del empleado para filtrar
        limite: mÃ¡ximo de resultados
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    domain: list = []
    if estado != "all":
        domain.append(("state", "=", estado))
    if empleado:
        domain.append(("employee_id.name", "ilike", empleado))

    fields = ["name", "employee_id", "total_amount", "currency_id",
              "state", "date", "product_id"]
    expenses = client.search_read("hr.expense", domain, fields, limit=limite, order="date desc")

    if not expenses:
        return "No se encontraron gastos con esos filtros."

    estado_map = {
        "draft": "Borrador", "reported": "Reportado", "approved": "Aprobado",
        "done": "Pagado", "refused": "Rechazado"
    }
    lines = [f"{'ID':<6} {'DescripciÃ³n':<30} {'Empleado':<22} {'Monto':>10} {'Estado':<12} {'Fecha'}"]
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
    Registra un nuevo gasto.

    Args:
        descripcion: descripciÃ³n del gasto
        monto: monto total
        empleado_nombre: nombre del empleado (debe existir en Odoo)
        fecha: fecha en YYYY-MM-DD (default: hoy)
        categoria: nombre de la categorÃ­a/producto de gasto
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()

    # Buscar empleado
    employees = client.search_read("hr.employee", [("name", "ilike", empleado_nombre)], ["id", "name"], limit=3)
    if not employees:
        return f"âŒ No se encontrÃ³ empleado con nombre '{empleado_nombre}'."
    emp = employees[0]

    values: dict = {
        "name": descripcion,
        "employee_id": emp["id"],
        "total_amount": monto,
        "date": fecha or datetime.now().strftime("%Y-%m-%d"),
        "quantity": 1,
    }

    # Buscar categorÃ­a de producto de gasto
    if categoria:
        products = client.search_read(
            "hr.expense.category" if False else "product.product",
            [("name", "ilike", categoria), ("can_be_expensed", "=", True)],
            ["id", "name"], limit=3
        )
        if products:
            values["product_id"] = products[0]["id"]

    expense_id = client.create("hr.expense", values)
    return f"âœ… Gasto creado (ID {expense_id}): '{descripcion}' â€” ${monto:,.2f} para {emp['name']}"


@mcp.tool()
def gastos_resumen_empleado(empleado: str = "", anio: int = 0, mes: int = 0) -> str:
    """
    Resumen de gastos por empleado y estado.

    Args:
        empleado: nombre parcial del empleado (vacÃ­o = todos)
        anio: aÃ±o (0 = todos)
        mes: mes 1-12 (0 = todos)
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

    expenses = client.search_read(
        "hr.expense", domain,
        ["employee_id", "total_amount", "state"],
        limit=1000
    )

    by_emp: dict[str, dict] = {}
    for e in expenses:
        emp = e["employee_id"][1] if e.get("employee_id") else "N/A"
        if emp not in by_emp:
            by_emp[emp] = {"total": 0, "count": 0}
        by_emp[emp]["total"] += e.get("total_amount", 0)
        by_emp[emp]["count"] += 1

    lines = [f"{'Empleado':<30} {'Gastos':>8} {'Total':>14}"]
    lines.append("-" * 55)
    for emp, data in sorted(by_emp.items(), key=lambda x: -x[1]["total"]):
        lines.append(f"{emp[:29]:<30} {data['count']:>8} ${data['total']:>13,.2f}")
    grand = sum(d["total"] for d in by_emp.values())
    lines.append("-" * 55)
    lines.append(f"{'TOTAL':<30} {len(expenses):>8} ${grand:>13,.2f}")
    return "\n".join(lines)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  ðŸ¦ CONCILIACIÃ“N BANCARIA
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@mcp.tool()
def banco_listar_cuentas() -> str:
    """Lista las cuentas/diarios bancarios configurados en Odoo."""
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
        return "No se encontraron diarios bancarios."
    lines = [f"{'ID':<5} {'Nombre':<30} {'Tipo':<8} {'Moneda'}"]
    lines.append("-" * 55)
    for j in journals:
        currency = j["currency_id"][1] if j.get("currency_id") else "Empresa"
        lines.append(f"{j['id']:<5} {j['name'][:29]:<30} {j['type']:<8} {currency}")
    return "\n".join(lines)


@mcp.tool()
def banco_movimientos_sin_conciliar(
    diario_id: int = 0,
    limite: int = 20
) -> str:
    """
    Lista movimientos bancarios (extracto) pendientes de conciliar.

    Args:
        diario_id: ID del diario bancario (0 = todos los bancos)
        limite: mÃ¡ximo de resultados
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    domain: list = [("is_reconciled", "=", False), ("statement_id", "!=", False)]
    if diario_id:
        domain.append(("journal_id", "=", diario_id))

    fields = ["date", "payment_ref", "amount", "currency_id",
              "journal_id", "partner_name", "statement_id"]
    lines_data = client.search_read(
        "account.bank.statement.line", domain, fields, limit=limite, order="date desc"
    )

    if not lines_data:
        return "âœ… No hay movimientos pendientes de conciliar."

    lines = [f"{'Fecha':<12} {'Referencia':<30} {'Partner':<22} {'Monto':>12} {'Banco'}"]
    lines.append("-" * 95)
    for l in lines_data:
        lines.append(
            f"{str(l.get('date', '')):<12} "
            f"{str(l.get('payment_ref', '') or '')[:29]:<30} "
            f"{str(l.get('partner_name') or '')[:21]:<22} "
            f"${l.get('amount', 0):>11,.2f} "
            f"{l['journal_id'][1] if l.get('journal_id') else ''}"
        )
    return f"Movimientos sin conciliar ({len(lines_data)}):\n" + "\n".join(lines)


@mcp.tool()
def banco_estado_extractos(diario_id: int = 0, limite: int = 10) -> str:
    """
    Muestra el estado de los extractos bancarios (abiertos vs cerrados).

    Args:
        diario_id: ID del diario (0 = todos)
        limite: mÃ¡ximo de extractos a mostrar
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    domain: list = []
    if diario_id:
        domain.append(("journal_id", "=", diario_id))

    fields = ["name", "journal_id", "date", "balance_start",
              "balance_end_real", "currency_id"]
    statements = client.search_read(
        "account.bank.statement", domain, fields, limit=limite, order="date desc"
    )

    if not statements:
        return "No se encontraron extractos bancarios."

    lines = [f"{'Extracto':<20} {'Banco':<25} {'Fecha':<12} {'Saldo Inicial':>14} {'Saldo Final':>14}"]
    lines.append("-" * 90)
    for s in statements:
        lines.append(
            f"{str(s.get('name', ''))[:19]:<20} "
            f"{str(s['journal_id'][1] if s.get('journal_id') else '')[:24]:<25} "
            f"{str(s.get('date', '')):<12} "
            f"${s.get('balance_start', 0):>13,.2f} "
            f"${s.get('balance_end_real', 0):>13,.2f}"
        )
    return "\n".join(lines)


@mcp.tool()
def banco_pagos_recientes(dias: int = 7, limite: int = 20) -> str:
    """
    Lista pagos registrados en los Ãºltimos N dÃ­as.

    Args:
        dias: ventana de dÃ­as hacia atrÃ¡s (default 7)
        limite: mÃ¡ximo de resultados
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()
    fecha_desde = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
    domain = [
        ("date", ">=", fecha_desde),
        ("state", "in", ["posted", "reconciled"])
    ]
    fields = ["name", "partner_id", "amount", "payment_type",
              "journal_id", "date", "state", "currency_id"]
    payments = client.search_read(
        "account.payment", domain, fields, limit=limite, order="date desc"
    )

    if not payments:
        return f"No se encontraron pagos en los Ãºltimos {dias} dÃ­as."

    tipo_map = {"inbound": "Cobro", "outbound": "Pago", "transfer": "Transferencia"}
    lines = [f"{'Referencia':<16} {'Partner':<25} {'Tipo':<13} {'Monto':>12} {'Banco':<20} {'Fecha'}"]
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


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  ðŸ” UTILIDADES GENERALES
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@mcp.tool()
def odoo_buscar_cliente(nombre: str, limite: int = 10) -> str:
    """
    Busca un cliente/contacto en Odoo por nombre.

    Args:
        nombre: texto a buscar en el nombre del contacto
        limite: mÃ¡ximo de resultados
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
        return f"No se encontraron contactos con '{nombre}'."
    lines = [f"{'ID':<6} {'Nombre':<30} {'Email':<28} {'TelÃ©fono':<15} {'Ciudad'}"]
    lines.append("-" * 90)
    for p in partners:
        lines.append(
            f"{p['id']:<6} {str(p.get('name', ''))[:29]:<30} "
            f"{str(p.get('email') or '')[:27]:<28} "
            f"{str(p.get('phone') or '')[:14]:<15} "
            f"{str(p.get('city') or '')}"
        )
    return "\n".join(lines)


@mcp.tool()
def contabilidad_facturas_proveedor(
    fecha_desde: str = "",
    fecha_hasta: str = "",
    estado: str = "posted",
    limite: int = 50,
    buscar: str = ""
) -> str:
    """
    Lista facturas de proveedor (compras) para ayudar a conciliar movimientos bancarios.

    Args:
        fecha_desde: fecha inicio en YYYY-MM-DD (ej: 2026-05-01)
        fecha_hasta: fecha fin en YYYY-MM-DD (ej: 2026-05-31)
        estado: 'draft' (borrador), 'posted' (confirmada), 'cancel' (cancelada), 'all'
        limite: maximo de resultados
        buscar: texto para filtrar por proveedor o referencia
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
              "amount_residual", "state", "payment_state", "ref", "invoice_origin"]
    facturas = client.search_read("account.move", domain, fields, limit=limite, order="invoice_date desc")

    if not facturas:
        return "No se encontraron facturas de proveedor con esos filtros."

    pago_map = {"not_paid": "Sin pagar", "in_payment": "En proceso", "paid": "Pagada",
                "partial": "Parcial", "reversed": "Revertida", "invoicing_legacy": "Legacy"}

    lines = [f"{'Factura':<14} {'Proveedor':<28} {'Fecha':<12} {'Total':>12} {'Pendiente':>12} {'Pago'}"]
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
    lines.append(f"{'TOTAL PENDIENTE':>70} ${total_pendiente:>11,.0f}")
    return "\n".join(lines)


@mcp.tool()
def contabilidad_cruzar_banco_facturas(
    fecha_desde: str = "",
    fecha_hasta: str = ""
) -> str:
    """
    Cruza movimientos bancarios sin conciliar con facturas de proveedor sin pagar
    para identificar posibles matches por monto.

    Args:
        fecha_desde: fecha inicio YYYY-MM-DD
        fecha_hasta: fecha fin YYYY-MM-DD
    """
    client = get_client()
    if client is None:
        return _not_configured_msg()

    # Movimientos sin conciliar
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

    # Facturas sin pagar
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

    # Cruzar por monto (egresos bancarios vs facturas pendientes)
    matches = []
    for mov in movimientos:
        monto_banco = abs(mov.get("amount", 0))
        if monto_banco == 0:
            continue
        for fact in facturas:
            monto_fact = fact.get("amount_residual", 0)
            if abs(monto_banco - monto_fact) < 1:  # tolerancia $1
                matches.append({
                    "fecha_banco": mov.get("date", ""),
                    "ref_banco": str(mov.get("payment_ref", ""))[:35],
                    "partner_banco": str(mov.get("partner_name") or "Sin partner")[:20],
                    "monto": monto_banco,
                    "factura": str(fact.get("name", "")),
                    "proveedor": str(fact["partner_id"][1] if fact.get("partner_id") else "N/A")[:25],
                    "fecha_fact": fact.get("invoice_date", "")
                })

    if not matches:
        return (
            f"No se encontraron matches exactos entre movimientos bancarios y facturas "
            f"en el periodo {fecha_desde} - {fecha_hasta}.\n"
            f"Movimientos revisados: {len(movimientos)} | Facturas revisadas: {len(facturas)}"
        )

    lines = [
        f"Matches encontrados: {len(matches)}",
        "",
        f"{'Fecha Banco':<12} {'Referencia Banco':<36} {'Monto':>12} {'Factura':<14} {'Proveedor':<26} {'Fecha Fact.'}",
        "-" * 115
    ]
    for m in matches:
        lines.append(
            f"{m['fecha_banco']:<12} {m['ref_banco']:<36} ${m['monto']:>11,.0f} "
            f"{m['factura']:<14} {m['proveedor']:<26} {m['fecha_fact']}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()

