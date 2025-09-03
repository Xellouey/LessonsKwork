"""
Обработчики управления уроками в админ-панели.
CRUD операции для уроков, курсов и промокодов.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from telegram import Update, InlineKeyboardMarkup, ParseMode
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy.orm import Session
from sqlalchemy import desc

from bot.shared.database import get_db
from bot.shared.models import User, Lesson, Course, Purchase, PromoCode, CourseLesson
from bot.keyboards.admin_keyboards import AdminKeyboards
from bot.utils.state_manager import StateManager

logger = logging.getLogger(__name__)

# Состояния для управления уроками
(
    LESSON_ADD_TITLE,
    LESSON_ADD_DESCRIPTION,
    LESSON_ADD_PRICE,
    LESSON_ADD_CONTENT,
    LESSON_EDIT_TITLE,
    LESSON_EDIT_DESCRIPTION,
    LESSON_EDIT_PRICE,
    LESSON_EDIT_CONTENT,
    PROMO_ADD_CODE,
    PROMO_ADD_DISCOUNT,
    PROMO_ADD_LIMIT
) = range(11)


class LessonAdminHandlers:
    """Обработчики управления уроками."""
    
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
    
    # === УПРАВЛЕНИЕ УРОКАМИ ===
    
    async def add_lesson_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Начать добавление нового урока."""
        query = update.callback_query
        await query.answer()
        
        if not await self.is_admin(update.effective_user.id):
            await query.edit_message_text("❌ Нет прав доступа.")
            return ConversationHandler.END
        
        await query.edit_message_text(
            "📚 **Добавление нового урока**\n\n"
            "Введите название урока:",
            parse_mode=ParseMode.MARKDOWN
        )
        
        return LESSON_ADD_TITLE
    
    async def add_lesson_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получить название урока."""
        title = update.message.text.strip()
        
        if len(title) < 3 or len(title) > 255:
            await update.message.reply_text(
                "❌ Название должно быть от 3 до 255 символов. Попробуйте еще раз:"
            )
            return LESSON_ADD_TITLE
        
        context.user_data['lesson_title'] = title
        
        await update.message.reply_text(
            f"✅ Название: {title}\n\n"
            "Теперь введите описание урока:"
        )
        
        return LESSON_ADD_DESCRIPTION
    
    async def add_lesson_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получить описание урока."""
        description = update.message.text.strip()
        
        if len(description) < 10:
            await update.message.reply_text(
                "❌ Описание должно быть не менее 10 символов. Попробуйте еще раз:"
            )
            return LESSON_ADD_DESCRIPTION
        
        context.user_data['lesson_description'] = description
        
        await update.message.reply_text(
            f"✅ Описание сохранено\n\n"
            "Введите цену урока в Telegram Stars (число):"
        )
        
        return LESSON_ADD_PRICE
    
    async def add_lesson_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получить цену урока."""
        try:
            price = int(update.message.text.strip())
            if price < 0:
                raise ValueError("Отрицательная цена")
        except ValueError:
            await update.message.reply_text(
                "❌ Введите корректную цену (положительное число):"
            )
            return LESSON_ADD_PRICE
        
        context.user_data['lesson_price'] = price
        
        await update.message.reply_text(
            f"✅ Цена: ⭐{price}\n\n"
            "Теперь отправьте контент урока:\n"
            "- Текстовое содержание\n"
            "- Видео файл\n"
            "- Или напишите 'пропустить' для добавления позже"
        )
        
        return LESSON_ADD_CONTENT
    
    async def add_lesson_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получить контент урока."""
        content = None
        video_path = None
        
        if update.message.text:
            if update.message.text.strip().lower() == 'пропустить':
                content = ""
            else:
                content = update.message.text.strip()
        
        if update.message.video:
            # Сохранить видео файл
            file = await update.message.video.get_file()
            video_path = f"storage/videos/lesson_{datetime.now().timestamp()}.mp4"
            await file.download_to_drive(video_path)
        
        # Создать урок в базе данных
        db = next(get_db())
        try:
            lesson = Lesson(
                title=context.user_data['lesson_title'],
                description=context.user_data['lesson_description'],
                price=context.user_data['lesson_price'],
                text_content=content,
                video_path=video_path,
                is_active=True,
                is_free=context.user_data['lesson_price'] == 0
            )
            
            db.add(lesson)
            db.commit()
            db.refresh(lesson)
            
            await update.message.reply_text(
                f"✅ **Урок успешно создан!**\n\n"
                f"📚 Название: {lesson.title}\n"
                f"💰 Цена: ⭐{lesson.price}\n"
                f"🆔 ID: {lesson.id}\n\n"
                f"Урок активен и доступен для покупки.",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Очистить данные
            context.user_data.clear()
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Ошибка создания урока: {e}")
            await update.message.reply_text(
                "❌ Ошибка при создании урока. Попробуйте еще раз позже."
            )
            return ConversationHandler.END
        finally:
            db.close()
    
    async def list_lessons(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0) -> None:
        """Показать список уроков."""
        db = next(get_db())
        try:
            per_page = 10
            offset = page * per_page
            
            lessons = db.query(Lesson).order_by(desc(Lesson.created_at)).offset(offset).limit(per_page).all()
            total_lessons = db.query(Lesson).count()
            
            if not lessons:
                text = "📚 Уроков пока нет."
            else:
                text = f"📚 **Список уроков** (страница {page + 1})\n\n"
                
                for i, lesson in enumerate(lessons, start=offset + 1):
                    status = "✅" if lesson.is_active else "❌"
                    free_mark = "🆓" if lesson.is_free else ""
                    text += (
                        f"{i}. {status} {free_mark} **{lesson.title}**\n"
                        f"   💰 ⭐{lesson.price} | 🆔 {lesson.id}\n"
                        f"   📝 {lesson.description[:50]}{'...' if len(lesson.description) > 50 else ''}\n\n"
                    )
                
                text += f"📊 Всего уроков: {total_lessons}"
            
            keyboard = self.keyboards.get_lesson_list_menu(page)
            
            # Добавляем кнопки для редактирования уроков
            if lessons:
                edit_buttons = []
                for lesson in lessons[:5]:  # Показываем кнопки для первых 5 уроков
                    edit_buttons.append([
                        InlineKeyboardButton(
                            f"✏️ {lesson.title[:20]}...", 
                            callback_data=f"lesson:edit:{lesson.id}"
                        )
                    ])
                keyboard = edit_buttons + keyboard
            
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
    
    async def edit_lesson(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать меню редактирования урока."""
        query = update.callback_query
        await query.answer()
        
        lesson_id = int(query.data.split(":")[-1])
        
        db = next(get_db())
        try:
            lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
            
            if not lesson:
                await query.edit_message_text("❌ Урок не найден.")
                return
            
            text = (
                f"📝 **Редактирование урока**\n\n"
                f"📚 **Название:** {lesson.title}\n"
                f"📄 **Описание:** {lesson.description[:100]}{'...' if len(lesson.description) > 100 else ''}\n"
                f"💰 **Цена:** ⭐{lesson.price}\n"
                f"📊 **Статус:** {'Активный' if lesson.is_active else 'Неактивный'}\n"
                f"🆓 **Бесплатный:** {'Да' if lesson.is_free else 'Нет'}\n"
                f"📹 **Видео:** {'Есть' if lesson.video_path else 'Нет'}\n"
                f"🆔 **ID:** {lesson.id}"
            )
            
            keyboard = self.keyboards.get_lesson_edit_menu(lesson_id)
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        finally:
            db.close()
    
    async def delete_lesson(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Удалить урок."""
        query = update.callback_query
        await query.answer()
        
        lesson_id = int(query.data.split(":")[-1])
        
        db = next(get_db())
        try:
            lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
            
            if not lesson:
                await query.edit_message_text("❌ Урок не найден.")
                return
            
            # Проверяем, есть ли покупки этого урока
            purchases = db.query(Purchase).filter(Purchase.lesson_id == lesson_id).count()
            
            if purchases > 0:
                # Деактивируем урок вместо удаления
                lesson.is_active = False
                db.commit()
                
                await query.edit_message_text(
                    f"⚠️ Урок '{lesson.title}' был деактивирован, так как имеет {purchases} покупок.\n"
                    f"Урок больше не будет показываться пользователям, но останется в системе."
                )
            else:
                # Удаляем урок полностью
                db.delete(lesson)
                db.commit()
                
                await query.edit_message_text(
                    f"✅ Урок '{lesson.title}' был удален."
                )
        
        except Exception as e:
            logger.error(f"Ошибка удаления урока: {e}")
            await query.edit_message_text("❌ Ошибка при удалении урока.")
        finally:
            db.close()
    
    # === УПРАВЛЕНИЕ ПРОМОКОДАМИ ===
    
    async def create_promo_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Начать создание промокода."""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "🎁 **Создание промокода**\n\n"
            "Введите код промокода (латинские буквы и цифры):",
            parse_mode=ParseMode.MARKDOWN
        )
        
        return PROMO_ADD_CODE
    
    async def create_promo_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получить код промокода."""
        code = update.message.text.strip().upper()
        
        if not code.isalnum() or len(code) < 3 or len(code) > 20:
            await update.message.reply_text(
                "❌ Код должен содержать только латинские буквы и цифры, длина 3-20 символов:"
            )
            return PROMO_ADD_CODE
        
        # Проверяем уникальность кода
        db = next(get_db())
        try:
            existing = db.query(PromoCode).filter(PromoCode.code == code).first()
            if existing:
                await update.message.reply_text(
                    "❌ Такой промокод уже существует. Введите другой код:"
                )
                return PROMO_ADD_CODE
        finally:
            db.close()
        
        context.user_data['promo_code'] = code
        
        await update.message.reply_text(
            f"✅ Код: {code}\n\n"
            "Введите размер скидки в процентах (1-99):"
        )
        
        return PROMO_ADD_DISCOUNT
    
    async def create_promo_discount(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получить размер скидки."""
        try:
            discount = int(update.message.text.strip())
            if discount < 1 or discount > 99:
                raise ValueError("Неверный диапазон")
        except ValueError:
            await update.message.reply_text(
                "❌ Введите размер скидки от 1 до 99 процентов:"
            )
            return PROMO_ADD_DISCOUNT
        
        context.user_data['promo_discount'] = discount
        
        await update.message.reply_text(
            f"✅ Скидка: {discount}%\n\n"
            "Введите максимальное количество использований (или 0 для неограниченного):"
        )
        
        return PROMO_ADD_LIMIT
    
    async def create_promo_limit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получить лимит использований и создать промокод."""
        try:
            max_uses = int(update.message.text.strip())
            if max_uses < 0:
                raise ValueError("Отрицательное число")
        except ValueError:
            await update.message.reply_text(
                "❌ Введите корректное число (0 или больше):"
            )
            return PROMO_ADD_LIMIT
        
        # Создаем промокод
        db = next(get_db())
        try:
            promo = PromoCode(
                code=context.user_data['promo_code'],
                discount_percent=context.user_data['promo_discount'],
                max_uses=max_uses if max_uses > 0 else None,
                current_uses=0,
                is_active=True
            )
            
            db.add(promo)
            db.commit()
            db.refresh(promo)
            
            await update.message.reply_text(
                f"✅ **Промокод создан!**\n\n"
                f"🎁 Код: `{promo.code}`\n"
                f"💰 Скидка: {promo.discount_percent}%\n"
                f"🔄 Лимит: {'Неограниченно' if not promo.max_uses else promo.max_uses}\n"
                f"🆔 ID: {promo.id}",
                parse_mode=ParseMode.MARKDOWN
            )
            
            context.user_data.clear()
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Ошибка создания промокода: {e}")
            await update.message.reply_text("❌ Ошибка при создании промокода.")
            return ConversationHandler.END
        finally:
            db.close()
    
    async def list_promos(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать список промокодов."""
        db = next(get_db())
        try:
            promos = db.query(PromoCode).order_by(desc(PromoCode.created_at)).limit(20).all()
            
            if not promos:
                text = "🎁 Промокодов пока нет."
            else:
                text = "🎁 **Список промокодов**\n\n"
                
                for promo in promos:
                    status = "✅" if promo.is_active else "❌"
                    usage = f"{promo.current_uses}"
                    if promo.max_uses:
                        usage += f"/{promo.max_uses}"
                    else:
                        usage += "/∞"
                    
                    text += (
                        f"{status} **{promo.code}**\n"
                        f"   💰 -{promo.discount_percent}% | 🔄 {usage}\n"
                        f"   🆔 {promo.id}\n\n"
                    )
            
            keyboard = self.keyboards.get_back_to_admin_menu()
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


def create_lesson_admin_handlers(state_manager: StateManager) -> LessonAdminHandlers:
    """Создать обработчики управления уроками."""
    return LessonAdminHandlers(state_manager)