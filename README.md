# CRM Vault Agent

Agente para mantener actualizado un vault de Obsidian a partir de `CRM - Acelera` en Notion.

Estado actual: **fase 1, lectura segura / dry-run**.

## Flujo objetivo

```text
Notion CRM - Acelera
        |
Railway
        |
Vault Markdown
        |
Commit + push a GitHub
        |
Telegram consulta/edita con confirmacion
```

## Configuracion local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Luego llenar en `.env`:

```env
NOTION_TOKEN=
NOTION_CRM_DATABASE_ID=9b8e0b5662a143a7b7bd578722707b94
```

## Dry run

```powershell
python scripts\sync_notion_to_vault.py
```

Por ahora este comando solo:

- lee Notion
- guarda `raw/_latest_crm_query.json`
- guarda `raw/_sync_dry_run.md`

No modifica notas del vault todavia.
