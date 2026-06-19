"""
Help command handler.
Routes /help to AI logic layer for dynamic help messages.
"""
from core.database import SessionLocal
from utils.user_helpers import get_or_create_telegram_user
from services.ai_logic import process_user_input


async def help_command(update, context):
    """Handle /help command - routes through ai_logic.py for customization."""
    # Extract Telegram user info
    tg_user = update.effective_user
    chat_id = update.effective_chat.id
    user_id = tg_user.id
    username = tg_user.username
    
    # Get or create user in database (if available)
    db = None
    user = None
    
    if SessionLocal:
        try:
            db = SessionLocal()
            user = get_or_create_telegram_user(
                db=db,
                telegram_user_id=user_id,
                telegram_chat_id=chat_id,
                telegram_username=username
            )
        except Exception as e:
            # Database error - continue without user context
            from utils.logger import logger
            logger.error(f"Database error in help handler: {e}")
    
    # Route through ai_logic.py for customizable help message
    try:
        response = process_user_input("/help", user)
        await update.message.reply_text(response, parse_mode="Markdown")
    except Exception as e:
        from utils.logger import logger
        logger.error(f"Error sending help: {e}")
        # Fallback to basic help if ai_logic fails
        await update.message.reply_text(
            "💡 Available Commands\n\n"
            "/start - Start the bot\n"
            "/help - Show this help message\n"
            "/status - Check bot status\n"
            "/ask <question> - Ask me anything"
        )
    finally:
        if db:
            db.close()
