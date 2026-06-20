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
- `buscar`: filter by opportunity name or customer name
- `vendedor`: filter by salesperson name (partial match, e.g. `"Carlos"`)
- `fecha_desde`: start date `YYYY-MM-DD` — applied to `fecha_campo`
- `fecha_hasta`: end date `YYYY-MM-DD` — applied to `fecha_campo`
- `fecha_campo`: date field to filter — `"date_deadline"` (closing date, default), `"create_date"` (creation), `"date_closed"` (won/lost date)

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

**`crm_asignar_vendedor`** — Reassign one or more leads/opportunities to a different salesperson:
- `oportunidad_ids`: list of opportunity IDs (e.g. `[12, 34, 56]`)
- `vendedor`: salesperson name (partial match) or exact email — if multiple users match, Claude will ask to clarify

## Customer tools

**`odoo_buscar_cliente`** — Search contacts by name, email, or RUT/VAT:
- `nombre`: text to match against name, email, or VAT/RUT
- `limite`: max results (default 10)

**`odoo_actualizar_cliente`** — Update fields on an existing contact:
- `cliente_id`: numeric ID (find it first with `odoo_buscar_cliente`)
- `nombre`: new display name
- `vat`: RUT or tax ID (e.g. `"76.123.456-7"`)
- `email`: email address
- `telefono`: main phone
- `movil`: mobile number
- `ciudad`: city
- `direccion`: street address

All fields except `cliente_id` are optional — only provided fields are updated. The tool shows a before/after diff of every changed field.

## Behavior guidelines

- When asked for pipeline overview, call `crm_resumen_pipeline` first
- When asked about specific deals, use `crm_listar_oportunidades` with appropriate filters
- Present currency amounts formatted with thousand separators
- If user asks "which deals are closing soon", filter by `estado=open` and sort by `fecha_cierre`
- Always show weighted revenue alongside total in summaries
- **Salesperson filter**: if the user says "assigned to [name]", "vendedor [name]", or "de [name]", pass `vendedor="name"`
- **Date filter**: if the user mentions "this month", "Q1", "from date X to Y", compute the dates and pass `fecha_desde` / `fecha_hasta`; default `fecha_campo` is `date_deadline` (closing); use `create_date` when user asks about leads created in a period
- **Combined filters**: vendedor and date filters can be combined freely with `estado` and `buscar`
- **Reassignment**: when the user says "assign [lead/s] to [person]", "reasignar", "cambiar vendedor", call `crm_asignar_vendedor` with the IDs and the person name/email; if the user hasn't provided IDs, first call `crm_listar_oportunidades` to show them and ask which ones to reassign
- **Update customer**: when the user says "actualizar cliente", "cambiar RUT", "editar contacto", "cambiar nombre de cliente", first call `odoo_buscar_cliente` if no ID is known, then call `odoo_actualizar_cliente` with only the fields to change; always show the before/after confirmation to the user
