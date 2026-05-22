# Odoo Connector for Claude

Connect Claude to your Odoo instance (Online or Community) and manage your business in natural language.

## What you can do

- **CRM** — Query pipeline, create opportunities, move stages, get revenue forecasts
- **Sales** — List orders, monthly summaries by salesperson, order details
- **Expenses** — Track pending approvals, create expenses, summaries by employee
- **Bank Reconciliation** — Find unreconciled movements, cross-reference with vendor bills

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

1. Log into Odoo → click your avatar → **Preferences**
2. Go to **Security** tab → **API Keys** → **New Key**
3. Name it "Claude MCP" and copy the key

### 3. Configure credentials

Create a `.env` file in the `server/` folder:

```env
ODOO_URL=https://yourcompany.odoo.com
ODOO_DB=yourcompany
ODOO_USERNAME=you@yourcompany.com
ODOO_API_KEY=your-api-key-here
```

> For Odoo SaaS, the database name is the subdomain (e.g., for `mycompany.odoo.com` use `mycompany`).

### 4. Add to Claude

**Option A — Claude Code CLI:**
```bash
claude mcp add odoo -- python /path/to/server/server.py
```

**Option B — Manual config** (`~/.claude.json` or `claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "odoo": {
      "command": "python",
      "args": ["/path/to/server/server.py"],
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

Ask Claude: `odoo_ping` — you should see your Odoo version and user ID.

## Available Tools

| Tool | Description |
|------|-------------|
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

## Example prompts

```
Show me the CRM pipeline summary
What sales were confirmed this month?
Which expenses are pending approval?
Find unreconciled bank movements for May
Cross-reference bank movements with vendor bills for May
Create a new opportunity for Acme Corp worth $50,000
```

## Compatibility

Tested with Odoo 19.0 (Online). Should work with Odoo 16+.
For Odoo 15 or earlier, some field names may differ.

## License

MIT — free to use, modify and distribute.

## Contributing

Pull requests welcome at [github.com/usiiel/odoo-connector](https://github.com/usiiel/odoo-connector)
