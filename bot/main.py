"""
Главный файл Telegram бота.
Инициализация, настройка обработчиков, запуск бота.
"""

import asyncio
import logging
import logging.config
import sys
from contextlib import asynccontextmanager
from typing import Optional
from telegram import Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    PreCheckoutQueryHandler,
    ConversationHandler,
    filters
)

from bot.config import settings, validate_bot_configuration, get_log_config
from bot.utils.state_manager import StateManager
from bot.shared.database import init_database, check_database_connection
from bot.utils.i18n import i18n
from bot.handlers.main_handlers import create_main_handlers
from bot.handlers.lesson_handlers import create_lesson_handlers
from bot.handlers.payment_handlers import create_payment_handlers
from bot.handlers.support_handlers import create_support_handlers
from bot.handlers.admin_handlers import (
    create_admin_handlers, 
    ADMIN_MENU, LESSON_MANAGEMENT, ADD_LESSON, EDIT_LESSON,
    USER_STATS, BROADCAST, SETTINGS, WAITING_LESSON_TITLE,
    WAITING_LESSON_DESCRIPTION, WAITING_LESSON_PRICE, WAITING_LESSON_CONTENT,
    WAITING_BROADCAST_MESSAGE, WAITING_SETTING_VALUE
)
from bot.handlers.lesson_admin_handlers import create_lesson_admin_handlers
from bot.handlers.broadcast_settings_handlers import create_broadcast_settings_handlers


# Настройка логирования
logging.config.dictConfig(get_log_config())
logger = logging.getLogger(__name__)


class LessonsBot:
    """Главный класс Telegram бота."""
    
    def __init__(self):
        self.app: Optional[Application] = None
        self.state_manager: Optional[StateManager] = None
        self.handlers = {}
    
    async def initialize(self):
        """Инициализация бота."""
        logger.info("🚀 Initializing Lessons Bot...")
        
        try:
            # Валидация конфигурации
            if not validate_bot_configuration():
                raise ValueError("Bot configuration validation failed")
            
            # Инициализация базы данных
            if not check_database_connection():
                logger.info("📊 Initializing database...")
                init_database()
                logger.info("✅ Database initialized successfully")
            else:
                logger.info("✅ Database connection is healthy")
            
            # Инициализация менеджера состояний
            self.state_manager = StateManager(
                use_redis=settings.use_redis,
                redis_url=settings.redis_url
            )
            
            # Загрузка переводов
            i18n.reload_translations()
            logger.info(f"✅ Loaded translations for: {', '.join(i18n.supported_languages)}")
            
            # Создание приложения бота
            self.app = Application.builder().token(settings.telegram_bot_token).build()
            
            # Создание обработчиков
            self.handlers = {
                'main': create_main_handlers(self.state_manager),
                'lessons': create_lesson_handlers(self.state_manager),
                'payments': create_payment_handlers(self.state_manager),
                'support': create_support_handlers(self.state_manager),
                'admin': create_admin_handlers(self.state_manager),
                'lesson_admin': create_lesson_admin_handlers(self.state_manager),
                'broadcast_settings': create_broadcast_settings_handlers(self.state_manager)
            }
            
            # Настройка обработчиков
            self._setup_handlers()
            
            logger.info("✅ Bot initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Bot initialization failed: {e}")
            raise
    
    def _setup_handlers(self):
        """Настройка всех обработчиков бота."""
        logger.info("📋 Setting up bot handlers...")
        
        # Основные команды
        self.app.add_handler(
            CommandHandler("start", self.handlers['main'].start_command)
        )
        self.app.add_handler(
            CommandHandler("help", self.handlers['main'].help_command)
        )
        
        # Админ-панель ConversationHandler
        admin_conversation = ConversationHandler(
            entry_points=[
                CommandHandler('admin', self.handlers['admin'].admin_command)
            ],
            states={
                ADMIN_MENU: [
                    CallbackQueryHandler(
                        self.handlers['admin'].admin_menu_callback,
                        pattern=r"^admin:"
                    )
                ],
                LESSON_MANAGEMENT: [
                    CallbackQueryHandler(
                        self.handlers['admin'].lesson_callback,
                        pattern=r"^lesson:"
                    ),
                    CallbackQueryHandler(
                        self.handlers['admin'].admin_menu_callback,
                        pattern=r"^admin:"
                    )
                ],
                ADD_LESSON: [
                    CallbackQueryHandler(
                        self.handlers['admin'].lesson_callback,
                        pattern=r"^lesson:"
                    )
                ],
                EDIT_LESSON: [
                    CallbackQueryHandler(
                        self.handlers['admin'].edit_lesson_callback,
                        pattern=r"^lesson:"
                    ),
                    CallbackQueryHandler(
                        self.handlers['admin'].delete_lesson_callback,
                        pattern=r"^lesson:"
                    ),
                    CallbackQueryHandler(
                        self.handlers['admin'].admin_menu_callback,
                        pattern=r"^admin:"
                    )
                ],
                USER_STATS: [
                    CallbackQueryHandler(
                        self.handlers['admin'].admin_menu_callback,
                        pattern=r"^admin:"
                    )
                ],
                BROADCAST: [
                    CallbackQueryHandler(
                        self.handlers['admin'].broadcast_callback,
                        pattern=r"^admin:broadcast"
                    ),
                    CallbackQueryHandler(
                        self.handlers['admin'].send_broadcast_message,
                        pattern=r"^broadcast:send_confirmed"
                    ),
                    CallbackQueryHandler(
                        self.handlers['admin'].admin_menu_callback,
                        pattern=r"^admin:"
                    )
                ],
                SETTINGS: [
                    CallbackQueryHandler(
                        self.handlers['admin'].settings_callback,
                        pattern=r"^settings:"
                    ),
                    CallbackQueryHandler(
                        self.handlers['admin'].admin_menu_callback,
                        pattern=r"^admin:"
                    )
                ],
                WAITING_LESSON_TITLE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.handlers['admin'].waiting_lesson_title
                    )
                ],
                WAITING_LESSON_DESCRIPTION: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.handlers['admin'].waiting_lesson_description
                    )
                ],
                WAITING_LESSON_PRICE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.handlers['admin'].waiting_lesson_price
                    )
                ],
                WAITING_LESSON_CONTENT: [
                    MessageHandler(
                        filters.TEXT | filters.VIDEO,
                        self.handlers['admin'].waiting_lesson_content
                    )
                ],
                WAITING_BROADCAST_MESSAGE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.handlers['admin'].waiting_broadcast_message
                    )
                ],
                WAITING_SETTING_VALUE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.handlers['admin'].waiting_setting_value
                    )
                ]
            },
            fallbacks=[
                CommandHandler('cancel', self.handlers['admin'].cancel),
                CallbackQueryHandler(
                    self.handlers['admin'].cancel,
                    pattern=r"^cancel"
                )
            ],
            allow_reentry=True
        )
        
        self.app.add_handler(admin_conversation)
        
        # Обработчики главного меню
        self.app.add_handler(
            CallbackQueryHandler(
                self.handlers['main'].main_menu_callback,
                pattern=r"^menu:"
            )
        )
        
        # Обработчики каталога уроков
        self.app.add_handler(
            CallbackQueryHandler(
                self.handlers['main'].catalog_pagination_callback,
                pattern=r"^catalog:page:\d+$"
            )
        )
        
        # Обработчики уроков
        self.app.add_handler(
            CallbackQueryHandler(
                self.handlers['lessons'].lesson_detail_callback,
                pattern=r"^lesson:view:\d+$"
            )
        )
        self.app.add_handler(
            CallbackQueryHandler(
                self.handlers['lessons'].open_lesson_callback,
                pattern=r"^lesson:open:\d+$"
            )
        )
        
        # Обработчики платежей
        self.app.add_handler(
            CallbackQueryHandler(
                self.handlers['payments'].start_payment_callback,
                pattern=r"^payment:start:\d+$"
            )
        )
        self.app.add_handler(
            CallbackQueryHandler(
                self.handlers['payments'].skip_promo_callback,
                pattern=r"^payment:skip_promo:\d+$"
            )
        )
        
        # Обработчик pre-checkout запросов
        self.app.add_handler(
            PreCheckoutQueryHandler(
                self.handlers['payments'].pre_checkout_query_handler
            )
        )
        
        # Обработчик успешных платежей
        self.app.add_handler(
            MessageHandler(
                filters.SUCCESSFUL_PAYMENT,
                self.handlers['payments'].successful_payment_handler
            )
        )
        
        # Обработчики поддержки
        self.app.add_handler(
            CallbackQueryHandler(
                self.handlers['support'].support_menu_callback,
                pattern=r"^support:menu$"
            )
        )
        self.app.add_handler(
            CallbackQueryHandler(
                self.handlers['support'].send_message_callback,
                pattern=r"^support:send_message$"
            )
        )
        self.app.add_handler(
            CallbackQueryHandler(
                self.handlers['support'].faq_callback,
                pattern=r"^support:faq$"
            )
        )
        
        # Обработчик языков
        self.app.add_handler(
            CallbackQueryHandler(
                self.handlers['main'].language_callback,
                pattern=r"^language:set:"
            )
        )
        
        # Обработчики сообщений
        self.app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self._message_router
            )
        )
        
        # Обработчик неизвестных коллбэков
        self.app.add_handler(
            CallbackQueryHandler(
                self.handlers['main'].unknown_callback
            )
        )
        
        # Обработчик ошибок
        self.app.add_error_handler(
            self.handlers['main'].error_handler
        )
        
        logger.info("✅ Bot handlers configured")
    
    async def _message_router(self, update: Update, context):
        """
        Маршрутизатор текстовых сообщений на основе состояния пользователя.
        """
        user_id = update.effective_user.id
        current_state, _ = self.state_manager.get_user_state(user_id)
        
        from bot.states.user_states import BotState
        
        if current_state == BotState.PROMO_CODE_INPUT:
            # Обработать ввод промокода
            await self.handlers['payments'].promo_code_message_handler(update, context)
        elif current_state == BotState.SUPPORT_MESSAGE_INPUT:
            # Обработать сообщение в поддержку
            await self.handlers['support'].support_message_handler(update, context)
        elif settings.is_admin(user_id):
            # Обработать ответ администратора
            await self.handlers['support'].admin_reply_handler(update, context)
        else:
            # Неожиданное сообщение - показать главное меню
            await self.handlers['main'].start_command(update, context)
    
    async def start(self):
        """Запустить бота."""
        logger.info("🤖 Starting Lessons Bot...")
        
        try:
            # Инициализация
            await self.initialize()
            
            # Запуск бота
            logger.info(f"🌟 Bot is running as @{settings.bot_username or 'unknown'}")
            logger.info(f"🔧 Debug mode: {settings.debug}")
            logger.info(f"🌐 Supported languages: {', '.join(i18n.supported_languages)}")
            
            await self.app.run_polling(
                drop_pending_updates=True,
                allowed_updates=['message', 'callback_query', 'pre_checkout_query']
            )
            
        except Exception as e:
            logger.error(f"❌ Bot startup failed: {e}")
            raise
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Очистка ресурсов."""
        logger.info("🧹 Cleaning up bot resources...")
        
        try:
            # Очистить состояния (если нужно)
            if self.state_manager:
                self.state_manager.cleanup_expired_states()
            
            logger.info("✅ Cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")
    
    async def send_admin_notification(self, message: str):
        """
        Отправить уведомление администратору.
        
        Args:
            message: Текст уведомления
        """
        if settings.admin_chat_id and self.app:
            try:
                await self.app.bot.send_message(
                    chat_id=settings.admin_chat_id,
                    text=f"🤖 Bot Notification:\n\n{message}"
                )
            except Exception as e:
                logger.error(f"Error sending admin notification: {e}")


async def main():
    """Главная функция запуска бота."""
    bot = LessonsBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    """Точка входа в приложение."""
    try:
        # Проверить версию Python
        if sys.version_info < (3, 8):
            print("❌ Python 3.8+ is required")
            sys.exit(1)
        
        # Запустить бота
        asyncio.run(main())
        
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)