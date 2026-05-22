---
description: >
  First-time setup and connection verification for the Odoo connector. Use when:
  configure odoo, connect to odoo, set up odoo, test odoo connection, odoo ping,
  verify odoo, check odoo status, odoo not connecting, odoo credentials.
---

# Odoo Connector Setup

Guide the user through connecting Claude to their Odoo instance.

## Step 1 — Get Odoo API Key

Instruct the user to:
1. Log into their Odoo instance
2. Click avatar (top right) → **Preferences**
3. Go to **Security** tab → **API Keys** → **New Key**
4. Name it "Claude MCP" and copy the generated key

## Step 2 — Configure environment variables

Tell the user to set these four variables in their MCP server config or `.env` file:

| Variable | Description | Example |
|----------|-------------|---------|
| `ODOO_URL` | Full URL of their Odoo instance | `https://mycompany.odoo.com` |
| `ODOO_DB` | Database name (subdomain for SaaS) | `mycompany` |
| `ODOO_USERNAME` | Login email | `admin@mycompany.com` |
| `ODOO_API_KEY` | API key from Step 1 | `abc123...` |

> For Odoo SaaS (odoo.com), the database name is the subdomain — e.g., for `mycompany.odoo.com` the DB is `mycompany`.

## Step 3 — Verify connection

Call `odoo_ping` after configuration. A successful response shows:
- Odoo version
- Connected user UID

If the connection fails, check:
- URL has no trailing slash
- DB name is exact (case-sensitive)
- API key is active and not expired
- User has sufficient access rights in Odoo
