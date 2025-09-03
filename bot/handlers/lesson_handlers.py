"""
Обработчики для работы с уроками.
Просмотр, доставка контента, проверка доступа.
"""

import logging
import os
from typing import Optional, Dict, Any
from telegram import Update, InputFile
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.config import settings
from bot.utils.api_client import BackendAPI
from bot.utils.i18n import get_user_text, get_user_language
from bot.utils.state_manager import StateManager
from bot.states.user_states import BotState
from bot.keyboards.main_keyboards import KeyboardBuilder


logger = logging.getLogger(__name__)


class LessonHandlers:
    """Обработчики для работы с уроками."""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.api_client = BackendAPI.get_client()
    
    async def lesson_detail_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Показать детали урока.
        """
        query = update.callback_query
        user_id = update.effective_user.id
        
        if not query or not query.data:
            return
        
        await query.answer()
        
        try:
            # Парсинг коллбэка: "lesson:view:lesson_id"
            action_parts = query.data.split(':')
            if len(action_parts) != 3:
                return
            
            lesson_id = int(action_parts[2])
            user_lang = await get_user_language(user_id)
            
            # Получить данные урока
            lesson = await self.api_client.get_lesson_public(lesson_id)
            
            # Проверить, купил ли пользователь урок
            user_purchased = await self.api_client.check_user_has_lesson(user_id, lesson_id)
            
            # Сохранить ID урока в состоянии
            self.state_manager.set_user_state(
                user_id, 
                BotState.VIEW_LESSON,
                {'lesson_id': lesson_id}
            )
            
            # Сформировать текст с деталями урока
            lesson_text = await self._format_lesson_details(lesson, user_id, user_purchased)
            
            # Создать клавиатуру
            keyboard = KeyboardBuilder.lesson_detail(lesson, user_purchased, user_lang)
            
            await query.edit_message_text(
                lesson_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            
        except Exception as e:
            logger.error(f"Error in lesson_detail_callback: {e}")
            await self._send_error_message(query, user_id)
    
    async def open_lesson_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Открыть урок для просмотра.
        """
        query = update.callback_query
        user_id = update.effective_user.id
        
        if not query or not query.data:
            return
        
        await query.answer()
        
        try:
            # Парсинг коллбэка: "lesson:open:lesson_id"
            action_parts = query.data.split(':')
            if len(action_parts) != 3:
                return
            
            lesson_id = int(action_parts[2])
            
            # Получить данные урока
            lesson = await self.api_client.get_lesson_public(lesson_id)
            
            # Проверить доступ к уроку
            has_access = await self._check_lesson_access(user_id, lesson)
            
            if not has_access:
                # Нет доступа к уроку
                error_text = await get_user_text(user_id, "errors.access_denied")
                await query.edit_message_text(error_text)
                return
            
            # Отправить контент урока
            await self._deliver_lesson_content(query, user_id, lesson)
            
        except Exception as e:
            logger.error(f"Error in open_lesson_callback: {e}")
            await self._send_error_message(query, user_id)
    
    async def _check_lesson_access(self, user_id: int, lesson: Dict[str, Any]) -> bool:
        """
        Проверить доступ пользователя к уроку.
        
        Args:
            user_id: ID пользователя
            lesson: Данные урока
            
        Returns:
            bool: True если есть доступ
        """
        # Бесплатные уроки доступны всем
        if lesson.get('is_free'):
            return True
        
        # Проверить, купил ли пользователь урок
        return await self.api_client.check_user_has_lesson(user_id, lesson.get('id'))
    
    async def _deliver_lesson_content(self, query, user_id: int, lesson: Dict[str, Any]):
        """
        Доставить контент урока пользователю.
        
        Args:
            query: Callback query
            user_id: ID пользователя
            lesson: Данные урока
        """
        user_lang = await get_user_language(user_id)
        lesson_id = lesson.get('id')
        
        try:
            # Уведомить о начале загрузки
            loading_text = await get_user_text(user_id, "common.loading")
            await query.edit_message_text(loading_text)
            
            # Отправить видео (если есть)
            video_sent = False
            if lesson.get('video_path'):
                video_sent = await self._send_video_content(query, user_id, lesson)
            
            # Отправить текстовый контент (если есть)
            if lesson.get('text_content'):
                await self._send_text_content(query, user_id, lesson, not video_sent)
            
            # Если ни видео, ни текста нет
            if not lesson.get('video_path') and not lesson.get('text_content'):
                no_content_text = await get_user_text(user_id, "errors.no_content")
                keyboard = KeyboardBuilder.back_to_main(user_lang)
                
                await query.edit_message_text(
                    no_content_text,
                    reply_markup=keyboard
                )
            
        except Exception as e:
            logger.error(f"Error delivering lesson content: {e}")
            error_text = await get_user_text(user_id, "errors.general")
            await query.edit_message_text(error_text)
    
    async def _send_video_content(self, query, user_id: int, lesson: Dict[str, Any]) -> bool:
        """
        Отправить видео контент урока.
        
        Args:
            query: Callback query
            user_id: ID пользователя
            lesson: Данные урока
            
        Returns:
            bool: True если видео отправлено успешно
        """
        try:
            video_path = lesson.get('video_path')
            if not video_path:
                return False
            
            # Полный путь к видео файлу
            full_video_path = os.path.join(settings.get_storage_path('videos'), video_path)
            
            if not os.path.exists(full_video_path):
                logger.warning(f"Video file not found: {full_video_path}")
                return False
            
            # Проверить размер файла
            file_size = os.path.getsize(full_video_path)
            max_size = 50 * 1024 * 1024  # 50MB лимит Telegram
            
            if file_size > max_size:
                logger.warning(f"Video file too large: {file_size} bytes")
                # TODO: Можно реализовать загрузку по частям или внешние ссылки
                return False
            
            # Создать caption с информацией об уроке
            caption = f"📖 {lesson.get('title', '')}\n\n"
            if lesson.get('description'):
                # Ограничить длину описания
                desc = lesson.get('description')
                if len(desc) > 200:
                    desc = desc[:197] + "..."
                caption += desc
            
            # Отправить видео
            with open(full_video_path, 'rb') as video_file:
                await query.message.reply_video(
                    video=InputFile(video_file, filename=f"lesson_{lesson.get('id')}.mp4"),
                    caption=caption,
                    parse_mode=ParseMode.HTML
                )
            
            logger.info(f"Video sent for lesson {lesson.get('id')} to user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending video content: {e}")
            return False
    
    async def _send_text_content(self, query, user_id: int, lesson: Dict[str, Any], edit_original: bool = True):
        """
        Отправить текстовый контент урока.
        
        Args:
            query: Callback query
            user_id: ID пользователя
            lesson: Данные урока
            edit_original: Редактировать оригинальное сообщение или отправить новое
        """
        try:
            text_content = lesson.get('text_content', '')
            if not text_content:
                return
            
            # Создать заголовок урока
            lesson_header = f"📖 <b>{lesson.get('title', '')}</b>\n\n"
            
            # Ограничить длину текста (Telegram лимит 4096 символов)
            max_text_length = 4096 - len(lesson_header) - 100  # Оставить место для клавиатуры
            
            if len(text_content) > max_text_length:
                text_content = text_content[:max_text_length] + "\n\n... (содержание обрезано)"
            
            full_text = lesson_header + text_content
            
            # Создать клавиатуру для навигации
            user_lang = await get_user_language(user_id)
            keyboard = KeyboardBuilder.back_to_main(user_lang)
            
            if edit_original:
                await query.edit_message_text(
                    full_text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
            else:
                await query.message.reply_text(
                    full_text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
            
            logger.info(f"Text content sent for lesson {lesson.get('id')} to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error sending text content: {e}")
    
    async def _format_lesson_details(self, lesson: Dict[str, Any], user_id: int, user_purchased: bool) -> str:
        """
        Форматировать детали урока для отображения.
        
        Args:
            lesson: Данные урока
            user_id: ID пользователя
            user_purchased: Купил ли пользователь урок
            
        Returns:
            str: Отформатированный текст
        """
        title = lesson.get('title', 'No title')
        description = lesson.get('description', '')
        price = lesson.get('price', 0)
        is_free = lesson.get('is_free', False)
        
        # Заголовок
        text = f"📖 <b>{title}</b>\n\n"
        
        # Описание
        if description:
            # Ограничить длину описания для предварительного просмотра
            if len(description) > 300:
                description = description[:297] + "..."
            text += f"{description}\n\n"
        
        # Цена
        if is_free:
            price_text = await get_user_text(user_id, "lessons.free_lesson")
        else:
            price_text = await get_user_text(user_id, "lessons.price", price=f"{price} ⭐")
        
        text += f"{price_text}\n\n"
        
        # Статус доступа
        if user_purchased:
            status_text = await get_user_text(user_id, "lessons.already_purchased")
            text += f"✅ {status_text}"
        elif is_free:
            status_text = await get_user_text(user_id, "common.free")
            text += f"🆓 {status_text}"
        
        return text
    
    async def search_lessons_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработчик поиска уроков.
        TODO: Реализовать, когда в API будет поддержка поиска.
        """
        query = update.callback_query
        user_id = update.effective_user.id
        
        if query:
            await query.answer("🔍 Search feature coming soon!")
    
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


# Фабрика для создания обработчиков
def create_lesson_handlers(state_manager: StateManager) -> LessonHandlers:
    """Создать обработчики уроков."""
    return LessonHandlers(state_manager)