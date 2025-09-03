"""
Обработчики админ-панели в боте.
Включает управление уроками, статистику, рассылки и настройки.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy.orm import Session
from sqlalchemy import func

from bot.shared.database import get_db
from bot.shared.models import User, Lesson, Course, Purchase, PromoCode, BotSettings
from bot.utils.state_manager import StateManager
from bot.keyboards.admin_keyboards import AdminKeyboards

logger = logging.getLogger(__name__)

# Состояния для админ-панели
(
    ADMIN_MENU,
    LESSON_MANAGEMENT,
    ADD_LESSON,
    EDIT_LESSON,
    USER_STATS,
    BROADCAST,
    SETTINGS,
    WAITING_LESSON_TITLE,
    WAITING_LESSON_DESCRIPTION,
    WAITING_LESSON_PRICE,
    WAITING_LESSON_CONTENT,
    WAITING_BROADCAST_MESSAGE,
    WAITING_SETTING_VALUE
) = range(13)


class AdminHandlers:
    """Обработчики админ-панели."""
    
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
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Главная команда входа в админ-панель."""
        user = update.effective_user
        
        if not await self.is_admin(user.id):
            await update.message.reply_text(
                "❌ У вас нет прав доступа к админ-панели."
            )
            return ConversationHandler.END
        
        await self.show_admin_menu(update, context)
        return ADMIN_MENU
    
    async def show_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать главное меню админ-панели."""
        db = next(get_db())
        try:
            # Получение статистики
            stats = self.get_dashboard_stats(db)
            
            menu_text = (
                f"🎛️ **Админ-панель**\n\n"
                f"📊 **Статистика:**\n"
                f"👥 Пользователей: {stats['total_users']}\n"
                f"📚 Уроков: {stats['total_lessons']}\n"
                f"💰 Доход: ⭐ {stats['total_revenue']}\n"
                f"🛒 Покупок: {stats['total_purchases']}\n\n"
                f"🕐 Обновлено: {datetime.now().strftime('%H:%M:%S')}"
            )
            
            keyboard = self.keyboards.get_admin_main_menu()
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    menu_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    menu_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
        finally:
            db.close()
    
    def get_dashboard_stats(self, db: Session) -> Dict[str, Any]:
        """Получить статистику для дашборда."""
        total_users = db.query(User).count()
        total_lessons = db.query(Lesson).filter(Lesson.is_active == True).count()
        total_purchases = db.query(Purchase).filter(Purchase.status == "completed").count()
        total_revenue = db.query(func.sum(Purchase.amount)).filter(
            Purchase.status == "completed"
        ).scalar() or 0
        
        return {
            "total_users": total_users,
            "total_lessons": total_lessons,
            "total_purchases": total_purchases,
            "total_revenue": total_revenue
        }
    
    async def admin_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка кнопок главного меню."""
        query = update.callback_query
        await query.answer()
        
        user = update.effective_user
        if not await self.is_admin(user.id):
            await query.edit_message_text("❌ Нет прав доступа.")
            return ConversationHandler.END
        
        action = query.data.split(":")[1] if ":" in query.data else None
        
        if action == "lessons":
            return await self.show_lesson_management(update, context)
        elif action == "users":
            return await self.show_user_stats(update, context)
        elif action == "broadcast":
            return await self.broadcast_callback(update, context)
        elif action == "settings":
            return await self.show_settings_menu(update, context)
        elif action == "refresh":
            await self.show_admin_menu(update, context)
            return ADMIN_MENU
        elif action == "back":
            await self.show_admin_menu(update, context)
            return ADMIN_MENU
        
        return ADMIN_MENU
    
    async def show_lesson_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Показать меню управления уроками."""
        db = next(get_db())
        try:
            lessons = db.query(Lesson).filter(Lesson.is_active == True).all()
            
            text = f"📚 **Управление уроками** ({len(lessons)} уроков)\n\n"
            
            if lessons:
                for lesson in lessons[:10]:  # Показываем первые 10
                    text += f"• {lesson.title} - ⭐{lesson.price}\n"
                if len(lessons) > 10:
                    text += f"\n... и еще {len(lessons) - 10} уроков"
            else:
                text += "Уроков пока нет."
            
            keyboard = self.keyboards.get_lesson_management_menu()
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
            return LESSON_MANAGEMENT
        finally:
            db.close()
    
    async def show_user_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Показать статистику пользователей."""
        db = next(get_db())
        try:
            # Статистика пользователей
            total_users = db.query(User).count()
            active_users = db.query(User).filter(User.is_active == True).count()
            admin_users = db.query(User).filter(User.is_admin == True).count()
            
            # Статистика покупок
            purchases_today = db.query(Purchase).filter(
                func.date(Purchase.created_at) == datetime.now().date(),
                Purchase.status == "completed"
            ).count()
            
            # Топ покупатели
            top_buyers = db.query(
                User.first_name,
                User.username,
                func.count(Purchase.id).label('purchase_count'),
                func.sum(Purchase.amount).label('total_spent')
            ).join(Purchase).filter(
                Purchase.status == "completed"
            ).group_by(User.id).order_by(
                func.sum(Purchase.amount).desc()
            ).limit(5).all()
            
            text = (
                f"👥 **Статистика пользователей**\n\n"
                f"📊 **Общая информация:**\n"
                f"• Всего пользователей: {total_users}\n"
                f"• Активных: {active_users}\n"
                f"• Администраторов: {admin_users}\n"
                f"• Покупок сегодня: {purchases_today}\n\n"
            )
            
            if top_buyers:
                text += "🏆 **Топ покупатели:**\n"
                for i, buyer in enumerate(top_buyers, 1):
                    name = buyer.first_name
                    if buyer.username:
                        name += f" (@{buyer.username})"
                    text += f"{i}. {name} - ⭐{buyer.total_spent} ({buyer.purchase_count} покупок)\n"
            
            keyboard = self.keyboards.get_back_to_admin_menu()
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
            return USER_STATS
        finally:
            db.close()
    
    async def show_settings_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Показать меню настроек."""
        db = next(get_db())
        try:
            settings = db.query(BotSettings).filter(BotSettings.is_active == True).all()
            
            text = "⚙️ **Настройки бота**\n\n"
            
            if settings:
                text += "📝 **Текущие настройки:**\n"
                for setting in settings[:10]:  # Показываем первые 10
                    text += f"• {setting.key}: {setting.value[:50]}{'...' if len(setting.value) > 50 else ''}\n"
            else:
                text += "Настроек пока нет."
            
            keyboard = self.keyboards.get_settings_menu()
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
            return SETTINGS
        finally:
            db.close()
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Отмена операции и возврат в главное меню."""
        context.user_data.clear()
        
        if update.callback_query:
            await self.show_admin_menu(update, context)
        else:
            await update.message.reply_text(
                "❌ Операция отменена.",
                reply_markup=InlineKeyboardMarkup(self.keyboards.get_back_to_admin_menu())
            )
        
        return ADMIN_MENU


def create_admin_handlers(state_manager: StateManager) -> AdminHandlers:
    """Создать обработчики админ-панели."""
    return AdminHandlers(state_manager)   
 # === ОБРАБОТЧИКИ УПРАВЛЕНИЯ УРОКАМИ ===
    
    async def lesson_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка действий с уроками."""
        query = update.callback_query
        await query.answer()
        
        user = update.effective_user
        if not await self.is_admin(user.id):
            await query.edit_message_text("❌ Нет прав доступа.")
            return ConversationHandler.END
        
        action_parts = query.data.split(":")
        action = action_parts[1] if len(action_parts) > 1 else None
        
        if action == "add":
            return await self.start_add_lesson(update, context)
        elif action == "edit":
            return await self.show_lesson_list_for_edit(update, context)
        elif action == "list":
            return await self.show_lesson_list(update, context)
        elif action == "delete":
            return await self.show_lesson_list_for_delete(update, context)
        elif action == "page":
            page = int(action_parts[2]) if len(action_parts) > 2 else 0
            return await self.show_lesson_list(update, context, page)
        
        return LESSON_MANAGEMENT
    
    async def start_add_lesson(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Начать процесс добавления урока."""
        text = (
            "➕ **Добавление нового урока**\n\n"
            "Введите название урока:"
        )
        
        keyboard = self.keyboards.get_back_to_admin_menu()
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
        # Очищаем данные урока
        context.user_data.clear()
        
        return WAITING_LESSON_TITLE
    
    async def waiting_lesson_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Ожидание ввода названия урока."""
        title = update.message.text.strip()
        
        if len(title) < 3:
            await update.message.reply_text(
                "❌ Название урока должно содержать минимум 3 символа. Попробуйте еще раз:"
            )
            return WAITING_LESSON_TITLE
        
        if len(title) > 255:
            await update.message.reply_text(
                "❌ Название урока слишком длинное (максимум 255 символов). Попробуйте еще раз:"
            )
            return WAITING_LESSON_TITLE
        
        context.user_data['lesson_title'] = title
        
        await update.message.reply_text(
            f"✅ Название: {title}\n\n"
            "Теперь введите описание урока:"
        )
        
        return WAITING_LESSON_DESCRIPTION
    
    async def waiting_lesson_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Ожидание ввода описания урока."""
        description = update.message.text.strip()
        
        if len(description) < 10:
            await update.message.reply_text(
                "❌ Описание урока должно содержать минимум 10 символов. Попробуйте еще раз:"
            )
            return WAITING_LESSON_DESCRIPTION
        
        context.user_data['lesson_description'] = description
        
        await update.message.reply_text(
            f"✅ Описание сохранено\n\n"
            "Введите цену урока в Telegram Stars (или 0 для бесплатного урока):"
        )
        
        return WAITING_LESSON_PRICE
    
    async def waiting_lesson_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Ожидание ввода цены урока."""
        try:
            price = int(update.message.text.strip())
            
            if price < 0:
                await update.message.reply_text(
                    "❌ Цена не может быть отрицательной. Введите корректную цену:"
                )
                return WAITING_LESSON_PRICE
            
            if price > 2500:  # Максимальная цена в Telegram Stars
                await update.message.reply_text(
                    "❌ Максимальная цена 2500 Telegram Stars. Введите корректную цену:"
                )
                return WAITING_LESSON_PRICE
            
            context.user_data['lesson_price'] = price
            context.user_data['lesson_is_free'] = price == 0
            
            await update.message.reply_text(
                f"✅ Цена: {'Бесплатно' if price == 0 else f'⭐{price}'}\n\n"
                "Теперь отправьте контент урока:\n"
                "• Видео файл (для видео урока)\n"
                "• Текстовое сообщение (для текстового урока)\n"
                "• Или напишите 'пропустить' чтобы добавить контент позже"
            )
            
            return WAITING_LESSON_CONTENT
            
        except ValueError:
            await update.message.reply_text(
                "❌ Введите корректное число. Попробуйте еще раз:"
            )
            return WAITING_LESSON_PRICE
    
    async def waiting_lesson_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Ожидание загрузки контента урока."""
        if update.message.text and update.message.text.lower() == 'пропустить':
            # Пропускаем контент
            context.user_data['lesson_content'] = None
            context.user_data['lesson_video_path'] = None
        elif update.message.video:
            # Обработка видео
            video = update.message.video
            context.user_data['lesson_video_path'] = video.file_id
            context.user_data['lesson_content'] = f"Видео: {video.file_name or 'video.mp4'}"
        elif update.message.text:
            # Текстовый контент
            content = update.message.text.strip()
            if len(content) < 10:
                await update.message.reply_text(
                    "❌ Текстовый контент должен содержать минимум 10 символов. Попробуйте еще раз:"
                )
                return WAITING_LESSON_CONTENT
            
            context.user_data['lesson_content'] = content
            context.user_data['lesson_video_path'] = None
        else:
            await update.message.reply_text(
                "❌ Неподдерживаемый тип контента. Отправьте видео, текст или напишите 'пропустить':"
            )
            return WAITING_LESSON_CONTENT
        
        return await self.save_lesson(update, context)
    
    async def save_lesson(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Сохранение урока в базу данных."""
        db = next(get_db())
        try:
            lesson_data = context.user_data
            
            # Создаем новый урок
            lesson = Lesson(
                title=lesson_data['lesson_title'],
                description=lesson_data['lesson_description'],
                price=lesson_data['lesson_price'],
                is_free=lesson_data['lesson_is_free'],
                text_content=lesson_data.get('lesson_content'),
                video_path=lesson_data.get('lesson_video_path'),
                is_active=True
            )
            
            db.add(lesson)
            db.commit()
            db.refresh(lesson)
            
            # Формируем сообщение об успехе
            content_info = "Без контента"
            if lesson.video_path:
                content_info = "Видео"
            elif lesson.text_content:
                content_info = "Текст"
            
            success_text = (
                f"✅ **Урок успешно создан!**\n\n"
                f"📚 **Название:** {lesson.title}\n"
                f"📄 **Описание:** {lesson.description[:100]}{'...' if len(lesson.description) > 100 else ''}\n"
                f"💰 **Цена:** {'Бесплатно' if lesson.is_free else f'⭐{lesson.price}'}\n"
                f"📹 **Контент:** {content_info}\n"
                f"🆔 **ID:** {lesson.id}"
            )
            
            keyboard = self.keyboards.get_lesson_management_menu()
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                success_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
            # Очищаем данные
            context.user_data.clear()
            
            return LESSON_MANAGEMENT
            
        except Exception as e:
            db.rollback()
            logger.error(f"Ошибка сохранения урока: {e}")
            
            await update.message.reply_text(
                f"❌ Ошибка при сохранении урока: {str(e)}\n\n"
                "Попробуйте еще раз или обратитесь к разработчику."
            )
            
            return LESSON_MANAGEMENT
        finally:
            db.close()
    
    async def show_lesson_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0) -> int:
        """Показать список уроков с пагинацией."""
        db = next(get_db())
        try:
            # Получаем уроки с пагинацией
            lessons_per_page = 5
            offset = page * lessons_per_page
            
            lessons = db.query(Lesson).filter(
                Lesson.is_active == True
            ).offset(offset).limit(lessons_per_page + 1).all()  # +1 для проверки наличия следующей страницы
            
            has_next = len(lessons) > lessons_per_page
            if has_next:
                lessons = lessons[:-1]  # Убираем лишний элемент
            
            total_lessons = db.query(Lesson).filter(Lesson.is_active == True).count()
            
            if not lessons:
                text = "📚 **Список уроков**\n\nУроков пока нет."
            else:
                text = f"📚 **Список уроков** (страница {page + 1})\n\n"
                
                for i, lesson in enumerate(lessons, 1):
                    status = "🟢" if lesson.is_active else "🔴"
                    price = "🆓" if lesson.is_free else f"⭐{lesson.price}"
                    text += f"{status} **{lesson.title}**\n"
                    text += f"   💰 {price} | 🆔 {lesson.id}\n"
                    text += f"   📄 {lesson.description[:50]}{'...' if len(lesson.description) > 50 else ''}\n\n"
                
                text += f"Всего уроков: {total_lessons}"
            
            # Создаем клавиатуру с навигацией
            keyboard = []
            
            # Кнопки навигации
            nav_row = []
            if page > 0:
                nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"lesson:page:{page-1}"))
            if has_next:
                nav_row.append(InlineKeyboardButton("➡️ Далее", callback_data=f"lesson:page:{page+1}"))
            
            if nav_row:
                keyboard.append(nav_row)
            
            # Кнопка возврата
            keyboard.append([
                InlineKeyboardButton("🔙 К управлению", callback_data="admin:lessons")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
            return LESSON_MANAGEMENT
            
        finally:
            db.close()
    
    async def show_lesson_list_for_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Показать список уроков для редактирования."""
        db = next(get_db())
        try:
            lessons = db.query(Lesson).filter(Lesson.is_active == True).limit(10).all()
            
            if not lessons:
                text = "📝 **Редактирование уроков**\n\nУроков для редактирования нет."
                keyboard = self.keyboards.get_back_to_admin_menu()
            else:
                text = "📝 **Выберите урок для редактирования:**\n\n"
                
                keyboard = []
                for lesson in lessons:
                    price = "🆓" if lesson.is_free else f"⭐{lesson.price}"
                    keyboard.append([
                        InlineKeyboardButton(
                            f"{lesson.title} ({price})",
                            callback_data=f"lesson:edit_select:{lesson.id}"
                        )
                    ])
                
                keyboard.append([
                    InlineKeyboardButton("🔙 К управлению", callback_data="admin:lessons")
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
            return EDIT_LESSON
            
        finally:
            db.close()
    
    async def show_lesson_list_for_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Показать список уроков для удаления."""
        db = next(get_db())
        try:
            lessons = db.query(Lesson).filter(Lesson.is_active == True).limit(10).all()
            
            if not lessons:
                text = "🗑️ **Удаление уроков**\n\nУроков для удаления нет."
                keyboard = self.keyboards.get_back_to_admin_menu()
            else:
                text = "🗑️ **Выберите урок для удаления:**\n\n⚠️ **Внимание!** Удаление урока необратимо.\n\n"
                
                keyboard = []
                for lesson in lessons:
                    price = "🆓" if lesson.is_free else f"⭐{lesson.price}"
                    keyboard.append([
                        InlineKeyboardButton(
                            f"🗑️ {lesson.title} ({price})",
                            callback_data=f"lesson:confirm_delete:{lesson.id}"
                        )
                    ])
                
                keyboard.append([
                    InlineKeyboardButton("🔙 К управлению", callback_data="admin:lessons")
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
            return LESSON_MANAGEMENT
            
        finally:
            db.close()  
  # === ОБРАБОТЧИКИ РАССЫЛКИ ===
    
    async def broadcast_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка рассылки сообщений."""
        query = update.callback_query
        await query.answer()
        
        user = update.effective_user
        if not await self.is_admin(user.id):
            await query.edit_message_text("❌ Нет прав доступа.")
            return ConversationHandler.END
        
        text = (
            "📢 **Рассылка сообщений**\n\n"
            "Отправьте сообщение, которое хотите разослать всем пользователям.\n"
            "Поддерживается форматирование Markdown.\n\n"
            "⚠️ Будьте осторожны - сообщение будет отправлено всем пользователям!"
        )
        
        keyboard = self.keyboards.get_back_to_admin_menu()
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
        return WAITING_BROADCAST_MESSAGE
    
    async def waiting_broadcast_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Ожидание сообщения для рассылки."""
        message_text = update.message.text.strip()
        
        if len(message_text) < 5:
            await update.message.reply_text(
                "❌ Сообщение слишком короткое (минимум 5 символов). Попробуйте еще раз:"
            )
            return WAITING_BROADCAST_MESSAGE
        
        if len(message_text) > 4000:
            await update.message.reply_text(
                "❌ Сообщение слишком длинное (максимум 4000 символов). Попробуйте еще раз:"
            )
            return WAITING_BROADCAST_MESSAGE
        
        # Сохраняем сообщение
        context.user_data['broadcast_message'] = message_text
        
        # Показываем превью и подтверждение
        db = next(get_db())
        try:
            total_users = db.query(User).filter(User.is_active == True).count()
            
            preview_text = (
                f"📢 **Предварительный просмотр рассылки**\n\n"
                f"👥 **Получателей:** {total_users} пользователей\n\n"
                f"📝 **Сообщение:**\n"
                f"─────────────────\n"
                f"{message_text}\n"
                f"─────────────────\n\n"
                f"Отправить рассылку?"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Отправить", callback_data="broadcast:send_confirmed"),
                    InlineKeyboardButton("❌ Отмена", callback_data="admin:broadcast")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                preview_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
            return BROADCAST
            
        finally:
            db.close()
    
    async def send_broadcast_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Отправка рассылки всем пользователям."""
        query = update.callback_query
        await query.answer()
        
        message_text = context.user_data.get('broadcast_message')
        if not message_text:
            await query.edit_message_text(
                "❌ Сообщение для рассылки не найдено.",
                reply_markup=InlineKeyboardMarkup(self.keyboards.get_back_to_admin_menu())
            )
            return ADMIN_MENU
        
        db = next(get_db())
        try:
            # Получаем всех активных пользователей
            users = db.query(User).filter(User.is_active == True).all()
            
            await query.edit_message_text(
                f"📤 Начинаю рассылку для {len(users)} пользователей...",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Отправляем сообщения
            sent_count = 0
            failed_count = 0
            
            for user in users:
                try:
                    await context.bot.send_message(
                        chat_id=user.telegram_id,
                        text=f"📢 **Сообщение от администрации:**\n\n{message_text}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    sent_count += 1
                    
                    # Небольшая задержка чтобы не превысить лимиты
                    import asyncio
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Ошибка отправки сообщения пользователю {user.telegram_id}: {e}")
                    failed_count += 1
            
            # Результат рассылки
            result_text = (
                f"✅ **Рассылка завершена!**\n\n"
                f"📤 **Отправлено:** {sent_count}\n"
                f"❌ **Ошибок:** {failed_count}\n"
                f"👥 **Всего пользователей:** {len(users)}"
            )
            
            keyboard = self.keyboards.get_back_to_admin_menu()
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                result_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
            # Очищаем данные
            context.user_data.clear()
            
            return ADMIN_MENU
            
        finally:
            db.close()
    
    # === ОБРАБОТЧИКИ НАСТРОЕК ===
    
    async def settings_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка настроек бота."""
        query = update.callback_query
        await query.answer()
        
        action_parts = query.data.split(":")
        action = action_parts[1] if len(action_parts) > 1 else None
        
        if action == "messages":
            return await self.show_message_settings(update, context)
        elif action == "buttons":
            return await self.show_button_settings(update, context)
        elif action == "add":
            return await self.start_add_setting(update, context)
        elif action == "list":
            return await self.show_all_settings(update, context)
        
        return SETTINGS
    
    async def show_message_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Показать настройки сообщений."""
        db = next(get_db())
        try:
            settings = db.query(BotSettings).filter(
                BotSettings.category == "messages",
                BotSettings.is_active == True
            ).all()
            
            text = "📝 **Настройки сообщений**\n\n"
            
            if settings:
                for setting in settings:
                    text += f"• **{setting.key}**\n"
                    text += f"  {setting.value[:100]}{'...' if len(setting.value) > 100 else ''}\n\n"
            else:
                text += "Настроек сообщений пока нет."
            
            keyboard = [
                [
                    InlineKeyboardButton("➕ Добавить", callback_data="settings:add:messages"),
                    InlineKeyboardButton("📝 Редактировать", callback_data="settings:edit:messages")
                ],
                [
                    InlineKeyboardButton("🔙 К настройкам", callback_data="admin:settings")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
            return SETTINGS
            
        finally:
            db.close()
    
    async def show_button_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Показать настройки кнопок."""
        db = next(get_db())
        try:
            settings = db.query(BotSettings).filter(
                BotSettings.category == "buttons",
                BotSettings.is_active == True
            ).all()
            
            text = "🔘 **Настройки кнопок**\n\n"
            
            if settings:
                for setting in settings:
                    text += f"• **{setting.key}:** {setting.value}\n"
            else:
                text += "Настроек кнопок пока нет."
            
            keyboard = [
                [
                    InlineKeyboardButton("➕ Добавить", callback_data="settings:add:buttons"),
                    InlineKeyboardButton("📝 Редактировать", callback_data="settings:edit:buttons")
                ],
                [
                    InlineKeyboardButton("🔙 К настройкам", callback_data="admin:settings")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
            return SETTINGS
            
        finally:
            db.close()
    
    async def start_add_setting(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Начать добавление новой настройки."""
        text = (
            "⚙️ **Добавление новой настройки**\n\n"
            "Введите ключ настройки (например: welcome_message, button_catalog):"
        )
        
        keyboard = self.keyboards.get_back_to_admin_menu()
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
        context.user_data.clear()
        
        return WAITING_SETTING_VALUE
    
    async def waiting_setting_value(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Ожидание ввода значения настройки."""
        if 'setting_key' not in context.user_data:
            # Первый шаг - ввод ключа
            key = update.message.text.strip()
            
            if len(key) < 3:
                await update.message.reply_text(
                    "❌ Ключ настройки должен содержать минимум 3 символа. Попробуйте еще раз:"
                )
                return WAITING_SETTING_VALUE
            
            # Проверяем уникальность ключа
            db = next(get_db())
            try:
                existing = db.query(BotSettings).filter(BotSettings.key == key).first()
                if existing:
                    await update.message.reply_text(
                        f"❌ Настройка с ключом '{key}' уже существует. Введите другой ключ:"
                    )
                    return WAITING_SETTING_VALUE
            finally:
                db.close()
            
            context.user_data['setting_key'] = key
            
            await update.message.reply_text(
                f"✅ Ключ: {key}\n\n"
                "Теперь введите значение настройки:"
            )
            
            return WAITING_SETTING_VALUE
        else:
            # Второй шаг - ввод значения
            value = update.message.text.strip()
            
            if len(value) < 1:
                await update.message.reply_text(
                    "❌ Значение не может быть пустым. Попробуйте еще раз:"
                )
                return WAITING_SETTING_VALUE
            
            return await self.save_setting(update, context, value)
    
    async def save_setting(self, update: Update, context: ContextTypes.DEFAULT_TYPE, value: str) -> int:
        """Сохранение настройки в базу данных."""
        db = next(get_db())
        try:
            key = context.user_data['setting_key']
            
            # Определяем категорию по ключу
            category = "general"
            if "button" in key.lower():
                category = "buttons"
            elif "message" in key.lower() or "text" in key.lower():
                category = "messages"
            elif "notification" in key.lower():
                category = "notifications"
            
            # Создаем новую настройку
            setting = BotSettings(
                key=key,
                value=value,
                category=category,
                description=f"Настройка добавлена через админ-панель",
                is_active=True
            )
            
            db.add(setting)
            db.commit()
            db.refresh(setting)
            
            success_text = (
                f"✅ **Настройка успешно добавлена!**\n\n"
                f"🔑 **Ключ:** {setting.key}\n"
                f"📝 **Значение:** {setting.value}\n"
                f"📂 **Категория:** {setting.category}\n"
                f"🆔 **ID:** {setting.id}"
            )
            
            keyboard = self.keyboards.get_settings_menu()
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                success_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
            # Очищаем данные
            context.user_data.clear()
            
            return SETTINGS
            
        except Exception as e:
            db.rollback()
            logger.error(f"Ошибка сохранения настройки: {e}")
            
            await update.message.reply_text(
                f"❌ Ошибка при сохранении настройки: {str(e)}"
            )
            
            return SETTINGS
        finally:
            db.close()
    
    async def show_all_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Показать все настройки."""
        db = next(get_db())
        try:
            settings = db.query(BotSettings).filter(BotSettings.is_active == True).all()
            
            text = "📋 **Все настройки бота**\n\n"
            
            if settings:
                # Группируем по категориям
                categories = {}
                for setting in settings:
                    if setting.category not in categories:
                        categories[setting.category] = []
                    categories[setting.category].append(setting)
                
                for category, cat_settings in categories.items():
                    category_names = {
                        'general': '🔧 Общие',
                        'messages': '📝 Сообщения',
                        'buttons': '🔘 Кнопки',
                        'notifications': '🔔 Уведомления'
                    }
                    
                    text += f"**{category_names.get(category, category.title())}:**\n"
                    
                    for setting in cat_settings:
                        text += f"• {setting.key}: {setting.value[:30]}{'...' if len(setting.value) > 30 else ''}\n"
                    
                    text += "\n"
            else:
                text += "Настроек пока нет."
            
            keyboard = [
                [
                    InlineKeyboardButton("➕ Добавить настройку", callback_data="settings:add")
                ],
                [
                    InlineKeyboardButton("🔙 К настройкам", callback_data="admin:settings")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
            return SETTINGS
            
        finally:
            db.close()