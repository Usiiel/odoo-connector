---
description: >
  First-time setup and connection for the Odoo connector. Use when:
  configure odoo, connect to odoo, set up odoo, odoo setup, odoo wizard,
  odoo not configured, odoo credentials, connect to my erp,
  odoo_setup, test odoo connection, odoo ping, verify odoo, odoo not working.
---

# Odoo Connector Setup

When the user wants to connect Claude to their Odoo instance, run **odoo_setup**.

## Automatic wizard

Call `odoo_setup` — it launches an interactive 4-step wizard that asks the user for:
1. Odoo URL (e.g., https://mycompany.odoo.com)
2. Database name (subdomain for SaaS)
3. Login email
4. API key

The wizard saves credentials automatically and tests the connection at the end.

## Getting an API key

If the user does not have an API key, guide them:
1. Log into Odoo → click avatar (top right) → **Preferences**
2. **Security** tab → **API Keys** → **New Key**
3. Name it anything (e.g., "Claude") and copy the key

## After setup

Once connected, suggest these first actions:
- "Show me the CRM pipeline"
- "What sales did we confirm this month?"
- "Are there expenses pending approval?"
- "Show unreconciled bank movements"

## Troubleshooting

If connection fails after setup:
- URL must not have a trailing slash
- Database name is case-sensitive (for SaaS = subdomain only, no .odoo.com)
- API key must be active (check in Odoo > Preferences > Security)
- User must have access rights to the modules being queried

Run `odoo_setup` again to re-enter credentials.
