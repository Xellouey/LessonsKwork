"""
Обработчики рассылки сообщений и управления настройками бота.
Включает массовую рассылку и управление текстами интерфейса.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from telegram import Update, InlineKeyboardMarkup, ParseMode
from telegram.ext import ContextTypes, ConversationHandler
from telegram.error import TelegramError, Forbidden, BadRequest
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from shared.database import get_db
from shared.models import User, Purchase, BotSettings
from bot.keyboards.admin_keyboards import AdminKeyboards
from bot.utils.state_manager import StateManager

logger = logging.getLogger(__name__)

# Состояния для рассылки и настроек
(
    BROADCAST_MESSAGE,
    BROADCAST_CONFIRM,
    SETTINGS_ADD_KEY,
    SETTINGS_ADD_VALUE,
    SETTINGS_EDIT_VALUE
) = range(5)


class BroadcastSettingsHandlers:
    """Обработчики рассылки и настроек."""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.keyboards = AdminKeyboards()
    
    async def is_admin(self, telegram_id: int) -> bool:
        """Проверка прав администратора."""
        db = next(get_db())
        try:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            return user and user.is_admin
        finally:
            db.close()
    
    # === РАССЫЛКА СООБЩЕНИЙ ===
    
    async def broadcast_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Начать создание рассылки."""
        query = update.callback_query
        await query.answer()
        
        if not await self.is_admin(update.effective_user.id):
            await query.edit_message_text("❌ Нет прав доступа.")
            return ConversationHandler.END
        
        text = (
            "📢 **Создание рассылки**\n\n"
            "Отправьте сообщение для рассылки. Поддерживается:\n"
            "• Текстовые сообщения с Markdown разметкой\n"
            "• Фото с подписями\n"
            "• Видео с подписями\n"
            "• Документы\n\n"
            "⚠️ Сообщение будет отправлено всем активным пользователям!"
        )
        
        keyboard = self.keyboards.get_back_to_admin_menu()
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
        return BROADCAST_MESSAGE
    
    async def broadcast_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получить сообщение для рассылки."""
        # Сохраняем сообщение
        context.user_data['broadcast_message'] = update.message
        
        # Получаем статистику получателей
        db = next(get_db())
        try:
            total_users = db.query(User).filter(User.is_active == True).count()
            
            # Показываем превью и подтверждение
            text = (
                f"📢 **Подтверждение рассылки**\n\n"
                f"👥 Получателей: {total_users} пользователей\n\n"
                f"📝 **Превью сообщения:**\n"
            )
            
            if update.message.text:
                text += f"```\n{update.message.text[:200]}{'...' if len(update.message.text) > 200 else ''}\n```"
            elif update.message.photo:
                text += "📷 Фото с подписью"
            elif update.message.video:
                text += "📹 Видео с подписью"
            elif update.message.document:
                text += "📄 Документ"
            
            keyboard = self.keyboards.get_confirm_broadcast_menu("all")
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
            return BROADCAST_CONFIRM
            
        finally:
            db.close()
    
    async def broadcast_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Подтвердить и запустить рассылку."""
        query = update.callback_query
        await query.answer()
        
        action = query.data.split(":")[-1]
        
        if action == "all":
            await self.start_broadcast(update, context, "all")
        else:
            await query.edit_message_text("❌ Рассылка отменена.")
        
        context.user_data.clear()
        return ConversationHandler.END
    
    async def start_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE, target: str) -> None:
        """Запустить рассылку."""
        query = update.callback_query
        broadcast_message = context.user_data.get('broadcast_message')
        
        if not broadcast_message:
            await query.edit_message_text("❌ Сообщение для рассылки не найдено.")
            return
        
        # Получаем список получателей
        db = next(get_db())
        try:
            if target == "all":
                users = db.query(User).filter(User.is_active == True).all()
            elif target == "admins":
                users = db.query(User).filter(
                    and_(User.is_active == True, User.is_admin == True)
                ).all()
            elif target == "buyers":
                # Пользователи с покупками
                user_ids = db.query(Purchase.user_id).filter(
                    Purchase.status == "completed"
                ).distinct().all()
                users = db.query(User).filter(
                    and_(User.is_active == True, User.id.in_([uid[0] for uid in user_ids]))
                ).all()
            elif target == "new":
                # Пользователи за последние 7 дней
                week_ago = datetime.now() - timedelta(days=7)
                users = db.query(User).filter(
                    and_(User.is_active == True, User.created_at >= week_ago)
                ).all()
            else:
                users = []
            
            total_users = len(users)
            
            await query.edit_message_text(
                f"📢 **Рассылка запущена**\n\n"
                f"👥 Получателей: {total_users}\n"
                f"⏳ Начинаем отправку...",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Запускаем рассылку в фоне
            asyncio.create_task(
                self.send_broadcast_messages(
                    context.bot, 
                    users, 
                    broadcast_message, 
                    query.message.chat_id,
                    query.message.message_id
                )
            )
            
        finally:
            db.close()
    
    async def send_broadcast_messages(
        self, 
        bot, 
        users: List[User], 
        message, 
        admin_chat_id: int, 
        status_message_id: int
    ) -> None:
        """Отправить сообщения рассылки всем пользователям."""
        total_users = len(users)
        sent_count = 0
        failed_count = 0
        
        # Обновляем статус каждые 10 отправок
        update_interval = max(1, total_users // 20)
        
        for i, user in enumerate(users):
            try:
                # Определяем тип сообщения и отправляем
                if message.text:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=message.text,
                        parse_mode=ParseMode.MARKDOWN
                    )
                elif message.photo:
                    await bot.send_photo(
                        chat_id=user.telegram_id,
                        photo=message.photo[-1].file_id,
                        caption=message.caption,
                        parse_mode=ParseMode.MARKDOWN
                    )
                elif message.video:
                    await bot.send_video(
                        chat_id=user.telegram_id,
                        video=message.video.file_id,
                        caption=message.caption,
                        parse_mode=ParseMode.MARKDOWN
                    )
                elif message.document:
                    await bot.send_document(
                        chat_id=user.telegram_id,
                        document=message.document.file_id,
                        caption=message.caption,
                        parse_mode=ParseMode.MARKDOWN
                    )
                
                sent_count += 1
                
                # Пауза между отправками
                await asyncio.sleep(0.05)  # 50ms задержка
                
            except (Forbidden, BadRequest) as e:
                # Пользователь заблокировал бота или удалил аккаунт
                failed_count += 1
                logger.warning(f"Не удалось отправить пользователю {user.telegram_id}: {e}")
                
                # Деактивируем пользователя если он заблокировал бота
                if isinstance(e, Forbidden):
                    db = next(get_db())
                    try:
                        user.is_active = False
                        db.commit()
                    finally:
                        db.close()
                        
            except TelegramError as e:
                failed_count += 1
                logger.error(f"Ошибка отправки пользователю {user.telegram_id}: {e}")
            
            # Обновляем статус
            if (i + 1) % update_interval == 0 or i == total_users - 1:
                try:
                    progress = (i + 1) / total_users * 100
                    status_text = (
                        f"📢 **Рассылка в процессе**\n\n"
                        f"📊 Прогресс: {progress:.1f}%\n"
                        f"✅ Отправлено: {sent_count}\n"
                        f"❌ Ошибок: {failed_count}\n"
                        f"📝 Осталось: {total_users - i - 1}"
                    )
                    
                    await bot.edit_message_text(
                        text=status_text,
                        chat_id=admin_chat_id,
                        message_id=status_message_id,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception:
                    pass  # Игнорируем ошибки обновления статуса
        
        # Финальный отчет
        try:
            final_text = (
                f"📢 **Рассылка завершена!**\n\n"
                f"👥 Всего пользователей: {total_users}\n"
                f"✅ Успешно отправлено: {sent_count}\n"
                f"❌ Ошибок: {failed_count}\n"
                f"📊 Успешность: {sent_count/total_users*100:.1f}%\n\n"
                f"⏰ Завершено: {datetime.now().strftime('%H:%M:%S')}"
            )
            
            await bot.edit_message_text(
                text=final_text,
                chat_id=admin_chat_id,
                message_id=status_message_id,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            pass
    
    # === УПРАВЛЕНИЕ НАСТРОЙКАМИ ===
    
    async def settings_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать меню настроек."""
        db = next(get_db())
        try:
            settings_count = db.query(BotSettings).filter(BotSettings.is_active == True).count()
            
            text = (
                f"⚙️ **Настройки бота**\n\n"
                f"📊 Всего настроек: {settings_count}\n\n"
                f"Выберите категорию для управления:"
            )
            
            keyboard = self.keyboards.get_settings_menu()
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
        finally:
            db.close()
    
    async def settings_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать настройки по категории."""
        query = update.callback_query
        await query.answer()
        
        category = query.data.split(":")[-1]
        
        db = next(get_db())
        try:
            settings = db.query(BotSettings).filter(
                and_(BotSettings.category == category, BotSettings.is_active == True)
            ).all()
            
            category_names = {
                "messages": "Тексты сообщений",
                "buttons": "Названия кнопок", 
                "general": "Общие настройки",
                "notifications": "Уведомления"
            }
            
            text = f"⚙️ **{category_names.get(category, category)}**\n\n"
            
            if settings:
                for setting in settings:
                    text += (
                        f"🔧 **{setting.key}**\n"
                        f"   {setting.value[:100]}{'...' if len(setting.value) > 100 else ''}\n"
                        f"   {setting.description or 'Без описания'}\n\n"
                    )
            else:
                text += "В этой категории пока нет настроек."
            
            keyboard = self.keyboards.get_settings_category_menu(category)
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        finally:
            db.close()
    
    async def add_setting_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Начать добавление настройки."""
        query = update.callback_query
        await query.answer()
        
        category = query.data.split(":")[-1] if len(query.data.split(":")) > 2 else "general"
        context.user_data['setting_category'] = category
        
        await query.edit_message_text(
            f"⚙️ **Добавление настройки**\n\n"
            f"📂 Категория: {category}\n\n"
            f"Введите ключ настройки (например: welcome_message):",
            parse_mode=ParseMode.MARKDOWN
        )
        
        return SETTINGS_ADD_KEY
    
    async def add_setting_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получить ключ настройки."""
        key = update.message.text.strip().lower()
        
        if not key.replace('_', '').isalnum() or len(key) < 3:
            await update.message.reply_text(
                "❌ Ключ должен содержать только буквы, цифры и подчеркивания, минимум 3 символа:"
            )
            return SETTINGS_ADD_KEY
        
        # Проверяем уникальность
        db = next(get_db())
        try:
            existing = db.query(BotSettings).filter(BotSettings.key == key).first()
            if existing:
                await update.message.reply_text(
                    "❌ Настройка с таким ключом уже существует. Введите другой ключ:"
                )
                return SETTINGS_ADD_KEY
        finally:
            db.close()
        
        context.user_data['setting_key'] = key
        
        await update.message.reply_text(
            f"✅ Ключ: {key}\n\n"
            "Теперь введите значение настройки:"
        )
        
        return SETTINGS_ADD_VALUE
    
    async def add_setting_value(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получить значение и создать настройку."""
        value = update.message.text.strip()
        
        if len(value) < 1:
            await update.message.reply_text(
                "❌ Значение не может быть пустым:"
            )
            return SETTINGS_ADD_VALUE
        
        # Создаем настройку
        db = next(get_db())
        try:
            setting = BotSettings(
                key=context.user_data['setting_key'],
                value=value,
                category=context.user_data['setting_category'],
                is_active=True
            )
            
            db.add(setting)
            db.commit()
            db.refresh(setting)
            
            await update.message.reply_text(
                f"✅ **Настройка создана!**\n\n"
                f"🔧 Ключ: `{setting.key}`\n"
                f"📂 Категория: {setting.category}\n"
                f"📝 Значение: {setting.value[:100]}{'...' if len(setting.value) > 100 else ''}",
                parse_mode=ParseMode.MARKDOWN
            )
            
            context.user_data.clear()
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Ошибка создания настройки: {e}")
            await update.message.reply_text("❌ Ошибка при создании настройки.")
            return ConversationHandler.END
        finally:
            db.close()
    
    def get_setting_value(self, key: str, default: str = "") -> str:
        """Получить значение настройки по ключу."""
        db = next(get_db())
        try:
            setting = db.query(BotSettings).filter(
                and_(BotSettings.key == key, BotSettings.is_active == True)
            ).first()
            return setting.value if setting else default
        finally:
            db.close()


def create_broadcast_settings_handlers(state_manager: StateManager) -> BroadcastSettingsHandlers:
    """Создать обработчики рассылки и настроек."""
    return BroadcastSettingsHandlers(state_manager)