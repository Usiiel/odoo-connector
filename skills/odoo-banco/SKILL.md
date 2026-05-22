---
description: >
  Bank reconciliation and payments in Odoo. Use when: bank reconciliation,
  unreconciled transactions, bank movements, reconcile, bank statements,
  pending reconciliation, bank accounts, recent payments, unmatched transactions,
  match bank movements, vendor bills, cross-reference payments, what needs reconciling.
---

# Odoo Bank Reconciliation

Interact with Odoo bank statements and reconciliation using these tools:

## Tools available

**`banco_listar_cuentas`** — List all bank/cash journals configured in Odoo. No arguments. Call this first to get journal IDs.

**`banco_movimientos_sin_conciliar`** — List unreconciled bank statement lines:
- `diario_id`: journal ID (0 = all banks)
- `limite`: max results (default 20)

**`banco_estado_extractos`** — Bank statement status (open vs closed):
- `diario_id`: journal ID (0 = all)
- `limite`: max statements (default 10)

**`banco_pagos_recientes`** — Recent registered payments:
- `dias`: look-back window in days (default 7)
- `limite`: max results (default 20)

**`contabilidad_facturas_proveedor`** — Vendor bills for reconciliation:
- `fecha_desde`: start date YYYY-MM-DD
- `fecha_hasta`: end date YYYY-MM-DD
- `estado`: `posted` (confirmed), `draft`, `all`
- `limite`: max results (default 50)
- `buscar`: filter by vendor or reference

**`contabilidad_cruzar_banco_facturas`** — Cross-reference bank movements with unpaid vendor bills by exact amount match:
- `fecha_desde`: start date YYYY-MM-DD
- `fecha_hasta`: end date YYYY-MM-DD

## Behavior guidelines

- When asked "what needs reconciling", call `banco_movimientos_sin_conciliar` for all banks
- If the user specifies a date range (e.g., "for May"), pass those dates to filter results
- After listing unreconciled movements, offer to cross-reference with vendor bills
- Call `contabilidad_cruzar_banco_facturas` to find exact amount matches automatically
- Distinguish between inbound (+) and outbound (-) movements
- Large outbound transfers without matching bills may be payroll, owner withdrawals, or advance payments — ask the user to clarify
- Present totals summarized by type (transfers, card purchases, commissions, etc.)
