# Odoo Connector for Claude

<!-- mcp-name: io.github.Usiiel/odoo-connector -->

Connect Claude to your Odoo instance (Online or Community) and manage your entire business in natural language — CRM, sales, purchases, inventory, projects, helpdesk, expenses, bank reconciliation, marketing, and more.

## What you can do

- **CRM** — Query pipeline, create opportunities, move stages, get revenue forecasts
- **Sales** — List orders, monthly summaries by salesperson, order details
- **Purchases** — RFQs, confirmed orders, monthly vendor summaries
- **Inventory** — Stock levels by product/location, transfers and movements
- **Projects** — List projects and tasks, filter by assignee or status
- **Employees** — Directory with department filters
- **Calendar** — Upcoming events and meetings
- **Subscriptions** — Active recurring contracts
- **Expenses** — Track pending approvals, create expenses, summaries by employee
- **Bank Reconciliation** — Find unreconciled movements, cross-reference with vendor bills
- **Helpdesk** — Tickets by team, priority, status; full ticket details
- **Website / eCommerce** — Published pages and product catalog
- **Activities** — Pending and overdue activities across all models
- **Attendances** — Employee check-in/check-out reports
- **Email Marketing** — Campaign list and status
- **WhatsApp** — Messages and templates
- **Conversations** — Discuss channels
- **Documents** — File list from Odoo Documents module
- **Appointments** — Scheduled appointments and types

## Requirements

- Python 3.11+
- Odoo 16, 17, 18, or 19 (Online or Community)
- An Odoo API key

## Installation

### 1. Install Python dependencies

```bash
pip install "mcp[cli]" python-dotenv
```

### 2. Get your Odoo API Key

1. Log into Odoo -> click your avatar -> **Preferences**
2. Go to **Security** tab -> **API Keys** -> **New Key**
3. Name it "Claude MCP" and copy the key

### 3. Configure credentials

Create a `.env` file in the project folder:

```env
ODOO_URL=https://yourcompany.odoo.com
ODOO_DB=yourcompany
ODOO_USERNAME=you@yourcompany.com
ODOO_API_KEY=your-api-key-here
```

> For Odoo SaaS, the database name is the subdomain (e.g., for `mycompany.odoo.com` use `mycompany`).

### 4. Add to Claude

**Option A -- Claude Code CLI:**
```bash
claude mcp add odoo -- python /path/to/server.py
```

**Option B -- Manual config** (`~/.claude.json` or `claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "odoo": {
      "command": "python",
      "args": ["/path/to/server.py"],
      "env": {
        "ODOO_URL": "https://yourcompany.odoo.com",
        "ODOO_DB": "yourcompany",
        "ODOO_USERNAME": "you@yourcompany.com",
        "ODOO_API_KEY": "your-api-key"
      }
    }
  }
}
```

### 5. Test the connection

Ask Claude: `odoo_ping` -- you should see your Odoo version and user ID.

## Available Tools (42)

| Tool | Description |
|------|-------------|
| `odoo_setup` | Interactive setup wizard |
| `odoo_ping` | Verify connection |
| `odoo_buscar_cliente` | Search contacts |
| `crm_resumen_pipeline` | Pipeline overview by stage |
| `crm_listar_oportunidades` | List deals with filters |
| `crm_crear_oportunidad` | Create new opportunity |
| `crm_actualizar_etapa` | Move deal to new stage |
| `ventas_listar_ordenes` | List sales orders |
| `ventas_detalle_orden` | Full order details |
| `ventas_resumen_mes` | Monthly sales by salesperson |
| `gastos_listar` | List expenses by status |
| `gastos_crear` | Register new expense |
| `gastos_resumen_empleado` | Expense summary by employee |
| `banco_listar_cuentas` | List bank journals |
| `banco_movimientos_sin_conciliar` | Unreconciled bank lines |
| `banco_estado_extractos` | Bank statement status |
| `banco_pagos_recientes` | Recent payments |
| `contabilidad_facturas_proveedor` | Vendor bills |
| `contabilidad_cruzar_banco_facturas` | Auto-match bank vs bills |
| `actividades_pendientes` | Pending / overdue activities |
| `helpdesk_tickets` | List helpdesk tickets |
| `helpdesk_detalle_ticket` | Ticket details |
| `website_paginas` | Published website pages |
| `ecommerce_productos` | eCommerce product catalog |
| `compras_listar_ordenes` | List purchase orders |
| `compras_detalle_orden` | Purchase order details |
| `compras_resumen_mes` | Monthly purchases by vendor |
| `inventario_stock` | Current stock levels |
| `inventario_movimientos` | Stock transfers / movements |
| `proyecto_listar` | List projects |
| `proyecto_tareas` | List project tasks |
| `empleados_listar` | Employee directory |
| `calendario_eventos` | Upcoming calendar events |
| `suscripciones_listar` | Active subscriptions |
| `asistencias_reporte` | Attendance check-in/check-out |
| `marketing_campanas` | Email marketing campaigns |
| `whatsapp_mensajes` | WhatsApp messages |
| `whatsapp_plantillas` | WhatsApp templates |
| `conversaciones_canales` | Discuss channels |
| `documentos_listar` | Documents module files |
| `citas_listar` | Scheduled appointments |
| `citas_tipos` | Appointment types |

## Example prompts

```
Show me the CRM pipeline summary
What sales were confirmed this month?
Which expenses are pending approval?
Find unreconciled bank movements for May
Cross-reference bank movements with vendor bills for May
Create a new opportunity for Acme Corp worth $50,000
Show me open purchase orders this week
What's the current stock level for product X?
List my pending activities for today
Show helpdesk tickets assigned to me
Attendance report for the team today
List active email marketing campaigns
Show me published website pages
```

## Compatibility

Tested with Odoo 19.0 (Online). Should work with Odoo 16+.
For Odoo 15 or earlier, some field names may differ.

## Changelog

### v0.2.0 (2026-05-23)
- Added 24 new tools across 14 modules: Activities, Helpdesk, Website, eCommerce, Purchases, Inventory, Projects, Employees, Calendar, Subscriptions, Attendances, Email Marketing, WhatsApp, Conversations, Documents, Appointments
- Total: 42 tools covering 20 Odoo modules

### v0.1.0 (2026-05-22)
- Initial release with 18 tools: CRM, Sales, Expenses, Bank Reconciliation

## License

MIT -- free to use, modify and distribute.

## Contributing

Pull requests welcome at [github.com/usiiel/odoo-connector](https://github.com/usiiel/odoo-connector)
