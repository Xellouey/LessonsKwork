"""
Обработчики системы поддержки и обратной связи.
Создание тикетов, отправка сообщений администратору.
"""

import logging
from datetime import datetime
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.config import settings
from bot.utils.api_client import BackendAPI
from bot.utils.i18n import get_user_text, get_user_language
from bot.utils.state_manager import StateManager
from bot.states.user_states import BotState
from bot.keyboards.main_keyboards import KeyboardBuilder


logger = logging.getLogger(__name__)


class SupportHandlers:
    """Обработчики системы поддержки."""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.api_client = BackendAPI.get_client()
    
    async def support_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Показать меню поддержки.
        """
        query = update.callback_query
        user_id = update.effective_user.id
        
        if not query or not query.data:
            return
        
        await query.answer()
        
        try:
            user_lang = await get_user_language(user_id)
            
            # Установить состояние поддержки
            self.state_manager.set_user_state(user_id, BotState.SUPPORT_CONTACT)
            
            support_text = await get_user_text(user_id, "support.title")
            keyboard = KeyboardBuilder.support_menu(user_lang)
            
            await query.edit_message_text(
                support_text,
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error in support_menu_callback: {e}")
            await self._send_error_message(query, user_id)
    
    async def send_message_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Начать процесс отправки сообщения в поддержку.
        """
        query = update.callback_query
        user_id = update.effective_user.id
        
        if not query or not query.data:
            return
        
        await query.answer()
        
        try:
            # Установить состояние ввода сообщения
            self.state_manager.set_user_state(user_id, BotState.SUPPORT_MESSAGE_INPUT)
            
            # Показать инструкцию по вводу сообщения
            message_prompt = await get_user_text(user_id, "support.message_prompt")
            user_lang = await get_user_language(user_id)
            keyboard = KeyboardBuilder.back_to_main(user_lang)
            
            await query.edit_message_text(
                message_prompt,
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error in send_message_callback: {e}")
            await self._send_error_message(query, user_id)
    
    async def support_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработать сообщение пользователя в поддержку.
        """
        user_id = update.effective_user.id
        message = update.message
        
        if not message or not message.text:
            return
        
        try:
            # Проверить, что пользователь в правильном состоянии
            current_state, _ = self.state_manager.get_user_state(user_id)
            
            if current_state != BotState.SUPPORT_MESSAGE_INPUT:
                return
            
            user = update.effective_user
            support_message = message.text.strip()
            
            # Создать тикет поддержки через API
            ticket_data = await self.api_client.create_support_ticket(
                user_id=user_id,
                subject=f"Support request from {user.first_name or 'User'}",
                message=support_message
            )
            
            # Отправить подтверждение пользователю
            user_lang = await get_user_language(user_id)
            confirmation_text = await get_user_text(user_id, "support.message_sent")
            keyboard = KeyboardBuilder.main_menu(user_lang)
            
            await message.reply_text(
                confirmation_text,
                reply_markup=keyboard
            )
            
            # Уведомить администратора
            await self._notify_admin_about_ticket(context, user, support_message, ticket_data)
            
            # Сбросить состояние
            self.state_manager.set_user_state(user_id, BotState.MAIN_MENU)
            
            logger.info(f"Support ticket created for user {user_id}: {ticket_data.get('id')}")
            
        except Exception as e:
            logger.error(f"Error in support_message_handler: {e}")
            error_text = await get_user_text(user_id, "errors.general")
            await message.reply_text(error_text)
    
    async def _notify_admin_about_ticket(self, context: ContextTypes.DEFAULT_TYPE, user, message: str, ticket_data: dict):
        """
        Уведомить администратора о новом тикете.
        """
        if not settings.admin_chat_id:
            return
        
        try:
            # Форматировать информацию о пользователе
            user_info = f"👤 User: {user.first_name or 'Unknown'}"
            if user.last_name:
                user_info += f" {user.last_name}"
            if user.username:
                user_info += f" (@{user.username})"
            user_info += f"\n🆔 ID: {user.id}"
            
            # Сформировать уведомление
            admin_notification = (
                f"🆘 <b>New Support Ticket #{ticket_data.get('id', 'N/A')}</b>\n\n"
                f"{user_info}\n"
                f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"💬 <b>Message:</b>\n{message}"
            )
            
            # Отправить администратору
            await context.bot.send_message(
                chat_id=settings.admin_chat_id,
                text=admin_notification,
                parse_mode=ParseMode.HTML
            )
            
            # Также отправить в логи ошибок, если настроено
            if settings.error_log_chat_id and settings.error_log_chat_id != settings.admin_chat_id:
                await context.bot.send_message(
                    chat_id=settings.error_log_chat_id,
                    text=f"📋 Support ticket #{ticket_data.get('id')} created by user {user.id}",
                    parse_mode=ParseMode.HTML
                )
            
        except Exception as e:
            logger.error(f"Error notifying admin about ticket: {e}")
    
    async def faq_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Показать часто задаваемые вопросы.
        """
        query = update.callback_query
        user_id = update.effective_user.id
        
        if not query or not query.data:
            return
        
        await query.answer()
        
        try:
            user_lang = await get_user_language(user_id)
            
            # Создать FAQ текст
            faq_text = await self._get_faq_text(user_id, user_lang)
            keyboard = KeyboardBuilder.support_menu(user_lang)
            
            await query.edit_message_text(
                faq_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            
        except Exception as e:
            logger.error(f"Error in faq_callback: {e}")
            await self._send_error_message(query, user_id)
    
    async def _get_faq_text(self, user_id: int, lang: str) -> str:
        """
        Получить текст FAQ.
        
        Args:
            user_id: ID пользователя
            lang: Код языка
            
        Returns:
            str: Текст FAQ
        """
        if lang == 'ru':
            return """
❓ <b>Часто задаваемые вопросы</b>

<b>Q: Как купить урок?</b>
A: Выберите урок в каталоге, нажмите кнопку "Купить" и оплатите через Telegram Stars.

<b>Q: Где мои купленные уроки?</b>
A: Перейдите в раздел "👤 Мои уроки" в главном меню.

<b>Q: Можно ли получить возврат?</b>
A: Да, обратитесь в поддержку в течение 24 часов после покупки.

<b>Q: Как работают промокоды?</b>
A: Введите промокод при покупке урока для получения скидки.

<b>Q: Проблемы с воспроизведением?</b>
A: Проверьте интернет-соединение. Если проблема сохраняется, напишите в поддержку.

<b>Q: Как изменить язык?</b>
A: Нажмите "🌐 Язык" в главном меню и выберите предпочитаемый язык.
"""
        else:
            return """
❓ <b>Frequently Asked Questions</b>

<b>Q: How to buy a lesson?</b>
A: Select a lesson from the catalog, click "Buy" button and pay with Telegram Stars.

<b>Q: Where are my purchased lessons?</b>
A: Go to "👤 My Lessons" section in the main menu.

<b>Q: Can I get a refund?</b>
A: Yes, contact support within 24 hours after purchase.

<b>Q: How do promo codes work?</b>
A: Enter the promo code when buying a lesson to get a discount.

<b>Q: Playback issues?</b>
A: Check your internet connection. If the problem persists, contact support.

<b>Q: How to change language?</b>
A: Click "🌐 Language" in the main menu and select your preferred language.
"""
    
    async def admin_reply_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработчик ответа администратора на тикет.
        Только для администраторов, которые отвечают на сообщения поддержки.
        """
        user_id = update.effective_user.id
        message = update.message
        
        # Проверить, что это администратор
        if not settings.is_admin(user_id):
            return
        
        # Проверить, что это ответ на сообщение
        if not message or not message.reply_to_message:
            return
        
        try:
            # Попытаться извлечь ID пользователя из оригинального сообщения
            original_text = message.reply_to_message.text or ""
            
            # Поиск паттерна "ID: XXXXX" в тексте
            import re
            user_id_match = re.search(r'ID: (\d+)', original_text)
            
            if not user_id_match:
                await message.reply_text("❌ Cannot find user ID in the original message")
                return
            
            target_user_id = int(user_id_match.group(1))
            admin_reply = message.text
            
            # Отправить ответ пользователю
            user_lang = await get_user_language(target_user_id)
            
            if user_lang == 'ru':
                reply_header = "📞 <b>Ответ службы поддержки:</b>\n\n"
            else:
                reply_header = "📞 <b>Support Team Reply:</b>\n\n"
            
            full_reply = reply_header + admin_reply
            
            await context.bot.send_message(
                chat_id=target_user_id,
                text=full_reply,
                parse_mode=ParseMode.HTML
            )
            
            # Подтвердить администратору
            await message.reply_text("✅ Reply sent to user")
            
            logger.info(f"Admin reply sent from {user_id} to user {target_user_id}")
            
        except Exception as e:
            logger.error(f"Error in admin_reply_handler: {e}")
            await message.reply_text(f"❌ Error sending reply: {str(e)}")
    
    async def contact_admin_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Прямой контакт с администратором.
        """
        query = update.callback_query
        user_id = update.effective_user.id
        
        if not query:
            return
        
        await query.answer()
        
        try:
            user_lang = await get_user_language(user_id)
            
            if user_lang == 'ru':
                contact_text = (
                    "👨‍💻 <b>Связь с администратором</b>\n\n"
                    "Для прямой связи с администратором используйте кнопку 'Отправить сообщение' выше.\n\n"
                    "Мы стараемся отвечать в течение 24 часов."
                )
            else:
                contact_text = (
                    "👨‍💻 <b>Contact Administrator</b>\n\n"
                    "To contact the administrator directly, use the 'Send Message' button above.\n\n"
                    "We try to respond within 24 hours."
                )
            
            keyboard = KeyboardBuilder.support_menu(user_lang)
            
            await query.edit_message_text(
                contact_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            
        except Exception as e:
            logger.error(f"Error in contact_admin_callback: {e}")
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


class AdminSupportTools:
    """Инструменты администратора для работы с поддержкой."""
    
    def __init__(self):
        self.api_client = BackendAPI.get_client()
    
    async def get_open_tickets(self) -> list:
        """
        Получить список открытых тикетов.
        TODO: Реализовать когда в API будет endpoint для получения тикетов.
        """
        try:
            # В будущем: return await self.api_client.get_support_tickets(status='open')
            return []
        except Exception as e:
            logger.error(f"Error getting open tickets: {e}")
            return []
    
    async def close_ticket(self, ticket_id: int, admin_response: str = None) -> bool:
        """
        Закрыть тикет поддержки.
        TODO: Реализовать когда в API будет соответствующий endpoint.
        """
        try:
            # В будущем: 
            # return await self.api_client.update_support_ticket(
            #     ticket_id, status='closed', admin_response=admin_response
            # )
            return True
        except Exception as e:
            logger.error(f"Error closing ticket {ticket_id}: {e}")
            return False


# Фабрика для создания обработчиков поддержки
def create_support_handlers(state_manager: StateManager) -> SupportHandlers:
    """Создать обработчики поддержки."""
    return SupportHandlers(state_manager)


# Создание инструментов администратора
admin_support_tools = AdminSupportTools()