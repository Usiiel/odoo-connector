---
description: >
  Query and manage the Odoo CRM pipeline. Use when: crm, pipeline, opportunities,
  leads, sales pipeline, show opportunities, open deals, won deals, lost deals,
  create opportunity, move stage, update stage, pipeline summary, forecast,
  expected revenue, sales funnel, which deals are closing.
---

# Odoo CRM

Interact with the Odoo CRM pipeline using these tools:

## Tools available

**`crm_resumen_pipeline`** — Call first for a high-level view. Shows all open opportunities grouped by stage with total and weighted revenue. No arguments needed.

**`crm_listar_oportunidades`** — List opportunities with filters:
- `estado`: `open` (default), `won`, `lost`, `all`
- `limite`: max results (default 15)
- `buscar`: filter by name or customer

**`crm_crear_oportunidad`** — Create a new opportunity:
- `nombre`: title (required)
- `cliente`: company/contact name
- `valor_esperado`: estimated deal value
- `fecha_cierre`: closing date YYYY-MM-DD
- `vendedor_email`: assigned salesperson email
- `notas`: internal description

**`crm_actualizar_etapa`** — Move an opportunity to a new pipeline stage:
- `oportunidad_id`: numeric ID
- `etapa_nombre`: partial stage name (e.g., "propuesta", "ganado")

## Behavior guidelines

- When asked for pipeline overview, call `crm_resumen_pipeline` first
- When asked about specific deals, use `crm_listar_oportunidades` with appropriate filters
- Present currency amounts formatted with thousand separators
- If user asks "which deals are closing soon", filter by `estado=open` and sort by `fecha_cierre`
- Always show weighted revenue alongside total in summaries
