---
description: >
  Query and analyze Odoo sales orders. Use when: sales, orders, sale orders,
  quotations, confirmed orders, invoiced orders, monthly sales, sales summary,
  sales by salesperson, show sales this month, how much did we sell, order detail,
  sales report, revenue, top customers, pending invoicing.
---

# Odoo Sales

Interact with Odoo sales orders using these tools:

## Tools available

**`ventas_resumen_mes`** — Monthly sales summary grouped by salesperson:
- `anio`: year (default: current)
- `mes`: month 1-12 (default: current)

**`ventas_listar_ordenes`** — List sales orders with filters:
- `estado`: `draft` (quotation), `sale` (confirmed), `done` (invoiced), `cancel`, `all`
- `limite`: max results (default 15)
- `dias`: orders from last N days (default 30, 0 = no filter)
- `buscar`: filter by customer or order name

**`ventas_detalle_orden`** — Full detail of a single order including product lines:
- `orden_id`: numeric order ID

## Behavior guidelines

- For "how much did we sell this month", call `ventas_resumen_mes` with no arguments
- For "show me recent orders", call `ventas_listar_ordenes` with `estado=sale`
- When user asks for order details, extract the order ID from context or ask for it
- Present totals with currency formatting
- If asked about pending invoicing, filter by `invoice_status=to invoice`
- Quotations are `draft`, confirmed orders are `sale`, fully invoiced are `done`
