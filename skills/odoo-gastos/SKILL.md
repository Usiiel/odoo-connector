---
description: >
  Query and manage employee expenses in Odoo. Use when: expenses, employee expenses,
  pending expenses, expense approval, approve expenses, expense report,
  submitted expenses, draft expenses, expenses by employee, create expense,
  log expense, register expense, how much did we spend, expense summary.
---

# Odoo Expenses

Interact with Odoo employee expense management using these tools:

## Tools available

**`gastos_listar`** — List expenses with filters:
- `estado`: `draft` (pending submission), `reported`/`submitted` (awaiting approval), `approved`, `done` (paid), `refused`, `all`
- `empleado`: partial employee name filter
- `limite`: max results (default 20)

**`gastos_resumen_empleado`** — Summary of expenses grouped by employee:
- `empleado`: partial name (empty = all employees)
- `anio`: year filter (0 = all)
- `mes`: month filter (0 = all)

**`gastos_crear`** — Register a new expense:
- `descripcion`: expense description (required)
- `monto`: amount (required)
- `empleado_nombre`: employee name as it appears in Odoo (required)
- `fecha`: date YYYY-MM-DD (default: today)
- `categoria`: expense product category name

## Behavior guidelines

- "Pending approval" = expenses with `estado=reported` (submitted but not yet approved)
- "Draft" expenses are not yet submitted by the employee
- When listing pending expenses, always show `reported` state
- For expense summaries, call `gastos_resumen_empleado` 
- Present amounts with thousand separators and currency
- If an expense creation fails due to employee not found, ask the user to confirm the exact name as it appears in Odoo
