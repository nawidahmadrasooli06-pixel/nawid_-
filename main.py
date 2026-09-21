import asyncio
import logging
import os
from telegram import BotCommand, MenuButtonCommands, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ChatMemberHandler, MessageReactionHandler, filters
from config import BOT_TOKEN
from database import is_blocked
from handlers.start import start_command, language_callback, menu_callback
from handlers.owner import stars_toggle_callback, preview_callback, day_callback, timezone_callback, calendar_callback, emoji_callback
from handlers.like import like_callback, chat_member_update
from handlers.about import about_callback
from handlers.stars import message_reaction_count_update
from handlers.countdown import start_scheduler
from handlers.router import text_router, photo_router, general_nontext_router
from handlers.admin import stats_command, block_command

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def create_application():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("block", block_command))
    app.add_handler(CallbackQueryHandler(language_callback, pattern=r"^lang_(fa|en)$"))
    app.add_handler(CallbackQueryHandler(stars_toggle_callback, pattern=r"^stars_(yes|no)$"))
    app.add_handler(CallbackQueryHandler(preview_callback, pattern=r"^preview_(confirm|cancel|emoji|back)$"))
    app.add_handler(CallbackQueryHandler(day_callback, pattern=r"^owner_day_"))
    app.add_handler(CallbackQueryHandler(timezone_callback, pattern=r"^tz_(af|ir|de)$"))
    app.add_handler(CallbackQueryHandler(calendar_callback, pattern=r"^calendar_(gregorian|iran|afghan)$"))
    app.add_handler(CallbackQueryHandler(emoji_callback, pattern=r"^emoji_(add|continue)$"))
    app.add_handler(CallbackQueryHandler(like_callback, pattern=r"^like_"))
    app.add_handler(CallbackQueryHandler(menu_callback))
    app.add_handler(MessageHandler(filters.PHOTO, photo_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    app.add_handler(MessageHandler(~filters.COMMAND & ~filters.TEXT & ~filters.PHOTO, general_nontext_router))
    app.add_handler(ChatMemberHandler(chat_member_update, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageReactionHandler(message_reaction_count_update, message_reaction_types=(MessageReactionHandler.MESSAGE_REACTION_COUNT_UPDATED,)))
    return app

async def post_init(app):
    await app.bot.set_my_commands([BotCommand("start", "باز کردن پنل ربات")])
    await app.bot.set_chat_menu_button(menu_button=MenuButtonCommands())

async def error_handler(update: object, context):
    logger.exception("Unhandled Telegram error", exc_info=context.error)

async def main():
    app = create_application()
    app.post_init = post_init
    app.add_error_handler(error_handler)
    await app.initialize()
    await post_init(app)
    app.bot_data["challenge_scheduler"] = start_scheduler(app.bot)
    await app.start()
    await app.updater.start_polling(allowed_updates=["message", "callback_query", "chat_member", "message_reaction_count"])
    logger.info("Challenge bot started")
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        scheduler = app.bot_data.get("challenge_scheduler")
        if scheduler:
            scheduler.shutdown(wait=False)
        if app.updater.running:
            await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
