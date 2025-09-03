"""
Основные обработчики команд и коллбэков Telegram бота.
Обработка главного меню, навигации, команд.
"""

import logging
from typing import Optional
from telegram import Update, Bot
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.config import settings
from bot.utils.api_client import BackendAPI
from bot.utils.i18n import get_user_text, get_user_language, i18n
from bot.utils.state_manager import StateManager
from bot.states.user_states import BotState
from bot.keyboards.main_keyboards import KeyboardBuilder


logger = logging.getLogger(__name__)


class MainHandlers:
    """Основные обработчики бота."""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.api_client = BackendAPI.get_client()
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработчик команды /start.
        Регистрирует пользователя и показывает главное меню.
        """
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        try:
            logger.info(f"User {user.id} (@{user.username}) started the bot")
            
            # Создать или найти пользователя в API
            user_data = {
                'first_name': user.first_name or '',
                'last_name': user.last_name or '',
                'username': user.username or '',
                'language_code': user.language_code or 'en'
            }
            
            api_user = await self.api_client.create_or_find_user(
                telegram_id=user.id,
                **user_data
            )
            
            # Установить начальное состояние
            self.state_manager.set_user_state(user.id, BotState.MAIN_MENU)
            
            # Получить язык пользователя
            user_lang = await get_user_language(user.id)
            
            # Отправить приветствие и главное меню
            welcome_text = await get_user_text(user.id, "welcome")
            keyboard = KeyboardBuilder.main_menu(user_lang)
            
            if update.message:
                await update.message.reply_text(
                    welcome_text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=welcome_text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
            
            logger.info(f"User {user.id} registered successfully")
            
        except Exception as e:
            logger.error(f"Error in start_command for user {user.id}: {e}")
            error_text = await get_user_text(user.id, "errors.general")
            
            if update.message:
                await update.message.reply_text(error_text)
            else:
                await context.bot.send_message(chat_id=chat_id, text=error_text)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help."""
        user_id = update.effective_user.id
        
        help_text = await get_user_text(user_id, "help", 
            bot_name="Lessons Bot",
            features="📚 Browse and purchase lessons\n👤 Manage your purchased content\n🆘 Get support\n🌐 Multi-language interface"
        )
        
        keyboard = KeyboardBuilder.main_menu(await get_user_language(user_id))
        
        await update.message.reply_text(
            help_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    async def main_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработчик коллбэков главного меню.
        """
        query = update.callback_query
        user_id = update.effective_user.id
        
        if not query or not query.data:
            return
        
        await query.answer()
        
        try:
            # Парсинг коллбэка
            action_parts = query.data.split(':')
            if len(action_parts) < 2:
                return
            
            action_type = action_parts[0]  # "menu"
            action = action_parts[1]       # конкретное действие
            
            user_lang = await get_user_language(user_id)
            
            if action == "main":
                # Вернуться в главное меню
                await self._show_main_menu(query, user_id, user_lang)
                
            elif action == "browse_lessons":
                # Перейти к каталогу уроков
                await self._show_lessons_catalog(query, user_id, user_lang)
                
            elif action == "my_lessons":
                # Показать купленные уроки
                await self._show_my_lessons(query, user_id, user_lang)
                
            elif action == "support":
                # Показать меню поддержки
                await self._show_support_menu(query, user_id, user_lang)
                
            elif action == "language":
                # Показать выбор языка
                await self._show_language_selection(query, user_id, user_lang)
                
            else:
                logger.warning(f"Unknown menu action: {action}")
        
        except Exception as e:
            logger.error(f"Error in main_menu_callback: {e}")
            await self._send_error_message(query, user_id)
    
    async def _show_main_menu(self, query, user_id: int, lang: str):
        """Показать главное меню."""
        self.state_manager.set_user_state(user_id, BotState.MAIN_MENU)
        
        welcome_text = await get_user_text(user_id, "welcome")
        keyboard = KeyboardBuilder.main_menu(lang)
        
        await query.edit_message_text(
            welcome_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    async def _show_lessons_catalog(self, query, user_id: int, lang: str, page: int = 1):
        """Показать каталог уроков."""
        try:
            self.state_manager.set_user_state(user_id, BotState.BROWSE_LESSONS)
            
            # Загрузить уроки из API
            lessons_data = await self.api_client.get_public_lessons(page=page, size=10)
            lessons = lessons_data.get('items', [])
            total_pages = lessons_data.get('pages', 1)
            
            if not lessons:
                # Нет уроков
                no_lessons_text = await get_user_text(user_id, "lessons.no_lessons")
                keyboard = KeyboardBuilder.back_to_main(lang)
                
                await query.edit_message_text(
                    no_lessons_text,
                    reply_markup=keyboard
                )
                return
            
            # Создать клавиатуру каталога
            catalog_text = await get_user_text(user_id, "lessons.catalog_title")
            keyboard = KeyboardBuilder.lessons_catalog(lessons, page, total_pages, lang)
            
            await query.edit_message_text(
                catalog_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            
        except Exception as e:
            logger.error(f"Error showing lessons catalog: {e}")
            await self._send_error_message(query, user_id)
    
    async def _show_my_lessons(self, query, user_id: int, lang: str):
        """Показать купленные уроки пользователя."""
        try:
            self.state_manager.set_user_state(user_id, BotState.MY_LESSONS)
            
            # Получить покупки пользователя
            purchases = await self.api_client.get_user_purchases(user_id)
            
            # Фильтровать только завершенные покупки с уроками
            purchased_lessons = []
            for purchase in purchases:
                if (purchase.get('status') == 'completed' and 
                    purchase.get('lesson') and 
                    purchase.get('lesson_id')):
                    purchased_lessons.append(purchase.get('lesson'))
            
            if not purchased_lessons:
                # Нет купленных уроков
                empty_text = await get_user_text(user_id, "my_lessons.empty")
                keyboard = KeyboardBuilder.main_menu(lang)
                
                await query.edit_message_text(
                    empty_text,
                    reply_markup=keyboard
                )
                return
            
            # Создать клавиатуру с купленными уроками
            my_lessons_text = await get_user_text(user_id, "my_lessons.title")
            keyboard = KeyboardBuilder.my_lessons(purchased_lessons, lang=lang)
            
            await query.edit_message_text(
                my_lessons_text,
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error showing my lessons: {e}")
            await self._send_error_message(query, user_id)
    
    async def _show_support_menu(self, query, user_id: int, lang: str):
        """Показать меню поддержки."""
        self.state_manager.set_user_state(user_id, BotState.SUPPORT_CONTACT)
        
        support_text = await get_user_text(user_id, "support.title")
        keyboard = KeyboardBuilder.support_menu(lang)
        
        await query.edit_message_text(
            support_text,
            reply_markup=keyboard
        )
    
    async def _show_language_selection(self, query, user_id: int, current_lang: str):
        """Показать выбор языка."""
        self.state_manager.set_user_state(user_id, BotState.LANGUAGE_SELECTION)
        
        # Получить поддерживаемые языки
        supported_languages = i18n.get_supported_languages()
        
        language_text = await get_user_text(user_id, "language.title")
        current_text = await get_user_text(user_id, "language.current", language=i18n.get_language_flag(current_lang))
        
        full_text = f"{language_text}\n\n{current_text}\n\n{await get_user_text(user_id, 'language.select')}"
        
        keyboard = KeyboardBuilder.language_selection(supported_languages, current_lang)
        
        await query.edit_message_text(
            full_text,
            reply_markup=keyboard
        )
    
    async def catalog_pagination_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик пагинации каталога."""
        query = update.callback_query
        user_id = update.effective_user.id
        
        if not query or not query.data:
            return
        
        await query.answer()
        
        try:
            # Парсинг коллбэка: "catalog:page:N"
            action_parts = query.data.split(':')
            if len(action_parts) != 3:
                return
            
            page = int(action_parts[2])
            user_lang = await get_user_language(user_id)
            
            await self._show_lessons_catalog(query, user_id, user_lang, page)
            
        except (ValueError, IndexError) as e:
            logger.error(f"Error in catalog pagination: {e}")
    
    async def language_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик смены языка."""
        query = update.callback_query
        user_id = update.effective_user.id
        
        if not query or not query.data:
            return
        
        await query.answer()
        
        try:
            # Парсинг коллбэка: "language:set:lang_code"
            action_parts = query.data.split(':')
            if len(action_parts) != 3:
                return
            
            new_lang = action_parts[2]
            
            # Установить новый язык
            success = await i18n.set_user_language(user_id, new_lang)
            
            if success:
                # Показать подтверждение и вернуться в главное меню
                success_text = await get_user_text(user_id, "language.changed", 
                                                 language=i18n.get_language_flag(new_lang))
                keyboard = KeyboardBuilder.main_menu(new_lang)
                
                await query.edit_message_text(
                    success_text,
                    reply_markup=keyboard
                )
                
                # Обновить состояние
                self.state_manager.set_user_state(user_id, BotState.MAIN_MENU)
                
            else:
                # Ошибка смены языка
                error_text = await get_user_text(user_id, "language.change_failed")
                await query.edit_message_text(error_text)
                
        except Exception as e:
            logger.error(f"Error in language_callback: {e}")
            await self._send_error_message(query, user_id)
    
    async def _send_error_message(self, query, user_id: int):
        """Отправить сообщение об ошибке."""
        try:
            error_text = await get_user_text(user_id, "errors.general")
            keyboard = KeyboardBuilder.back_to_main(await get_user_language(user_id))
            
            await query.edit_message_text(
                error_text,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error sending error message: {e}")
    
    async def unknown_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик неизвестных коллбэков."""
        query = update.callback_query
        user_id = update.effective_user.id
        
        if query:
            await query.answer("❓ Unknown action")
            logger.warning(f"Unknown callback: {query.data} from user {user_id}")
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Общий обработчик ошибок."""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_user:
            user_id = update.effective_user.id
            error_text = await get_user_text(user_id, "errors.general")
            
            try:
                if update.callback_query:
                    await update.callback_query.message.reply_text(error_text)
                elif update.message:
                    await update.message.reply_text(error_text)
                else:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=error_text
                    )
            except Exception as e:
                logger.error(f"Error in error_handler: {e}")


# Создание обработчиков с использованием dependency injection
def create_main_handlers(state_manager: StateManager) -> MainHandlers:
    """Фабрика для создания обработчиков."""
    return MainHandlers(state_manager)