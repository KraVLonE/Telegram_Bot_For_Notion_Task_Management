from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, filters
from src.config import Config
from src.services.notion_service import NotionService
from src.services.ai_service import AIService
from src.bot.handlers import handle_message, handle_callback, error_handler
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

def main():
    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return

    # Initialize Services
    notion_service = NotionService()
    ai_service = AIService()

    # Build Application
    app = (
        ApplicationBuilder()
        .token(Config.TELEGRAM_TOKEN)
        .get_updates_connect_timeout(30)
        .get_updates_read_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .build()
    )

    # Inject Services into Bot Data
    app.bot_data["notion_service"] = notion_service
    app.bot_data["ai_service"] = ai_service

    # Register Handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_error_handler(error_handler)

    logger.info("Bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
