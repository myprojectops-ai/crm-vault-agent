from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from crm_vault_agent.config import Settings
from crm_vault_agent.dry_run import fetch_crm_records, write_dry_run_outputs
from crm_vault_agent.editing import PendingEdit, apply_edit, prepare_edit
from crm_vault_agent.git_publish import publish_to_github
from crm_vault_agent.qa import answer_question
from crm_vault_agent.vault_writer import write_vault


settings = Settings.from_env()
pending_edits: dict[int, PendingEdit] = {}


def allowed(update: Update) -> bool:
    if settings.telegram_allowed_user_id is None:
        return True
    user = update.effective_user
    return bool(user and user.id == settings.telegram_allowed_user_id)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        return
    await update.message.reply_text(
        "Listo. Puedes preguntarme por el vault, usar /sync o editar con:\n"
        "/editar Nombre | Campo | Nuevo valor"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        return
    report = settings.raw_dir / "_sync_dry_run.md"
    if report.exists():
        await update.message.reply_text(report.read_text(encoding="utf-8", errors="ignore")[:3500])
    else:
        await update.message.reply_text("Todavia no hay sync registrado.")


async def sync(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        return
    await update.message.reply_text("Sincronizando Notion -> vault...")
    records = fetch_crm_records(settings)
    write_dry_run_outputs(settings, records)
    summary = write_vault(settings, records)
    publish_result = publish_to_github(settings)
    await update.message.reply_text(
        f"Listo: {summary['prospect_notes']} notas, {summary['closed_clients']} clientes cerrados.\n"
        f"{publish_result}"
    )


async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        return
    user_id = update.effective_user.id
    try:
        pending = prepare_edit(settings, update.message.text)
    except Exception as exc:
        await update.message.reply_text(str(exc))
        return
    pending_edits[user_id] = pending
    await update.message.reply_text(
        "Confirma este cambio respondiendo SI CONFIRMO:\n\n"
        f"Prospecto: {pending.prospect_name}\n"
        f"Campo: {pending.field}\n"
        f"Antes: {pending.old_value}\n"
        f"Despues: {pending.new_value}"
    )


async def message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        return
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if text.upper() == "SI CONFIRMO" and user_id in pending_edits:
        pending = pending_edits.pop(user_id)
        apply_edit(settings, pending)
        await update.message.reply_text("Cambio aplicado en Notion. Usa /sync para actualizar el vault ahora.")
        return
    try:
        answer = answer_question(text, settings)
    except Exception as exc:
        answer = f"Tuve un error consultando el vault: {str(exc)[:500]}"
    await update.message.reply_text(answer[:3900])


async def scheduled_sync(context: ContextTypes.DEFAULT_TYPE) -> None:
    records = fetch_crm_records(settings)
    write_dry_run_outputs(settings, records)
    write_vault(settings, records)
    publish_to_github(settings)


def main() -> None:
    settings.require_telegram()
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("sync", sync))
    app.add_handler(CommandHandler("editar", edit))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))
    app.job_queue.run_repeating(scheduled_sync, interval=settings.sync_interval_hours * 3600, first=60)
    app.run_polling()


if __name__ == "__main__":
    main()
