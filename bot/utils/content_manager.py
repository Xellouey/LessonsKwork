"""
Менеджер контента для Telegram бота.
Управление файлами, доставка видео и текстового контента.
"""

import os
import logging
import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, Any, Optional, BinaryIO, List
from urllib.parse import urlparse

from telegram import Bot, InputFile, InputMediaVideo
from telegram.constants import ParseMode
from telegram.error import TelegramError

from bot.config import settings


logger = logging.getLogger(__name__)


class ContentManager:
    """Менеджер контента уроков."""
    
    def __init__(self, storage_path: str = None):
        self.storage_path = Path(storage_path or settings.get_storage_path())
        self.videos_path = self.storage_path / "videos"
        self.texts_path = self.storage_path / "texts" 
        self.temp_path = self.storage_path / "temp"
        self.thumbnails_path = self.storage_path / "thumbnails"
        
        # Создать директории если их нет
        self._ensure_directories()
        
        # Поддерживаемые форматы
        self.video_formats = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.webm'}
        self.text_formats = {'.txt', '.md', '.html'}
        
        # Лимиты файлов
        self.max_video_size = 50 * 1024 * 1024  # 50MB для Telegram
        self.max_text_length = 4000  # Лимит сообщения Telegram
    
    def _ensure_directories(self):
        """Создать необходимые директории."""
        try:
            self.storage_path.mkdir(exist_ok=True)
            self.videos_path.mkdir(exist_ok=True) 
            self.texts_path.mkdir(exist_ok=True)
            self.temp_path.mkdir(exist_ok=True)
            self.thumbnails_path.mkdir(exist_ok=True)
            
            logger.info(f"✅ Content directories ensured: {self.storage_path}")
        except Exception as e:
            logger.error(f"❌ Error creating directories: {e}")
            raise
    
    async def store_lesson_video(self, lesson_id: int, video_data: bytes, filename: str = None) -> str:
        """
        Сохранить видео урока.
        
        Args:
            lesson_id: ID урока
            video_data: Данные видео файла
            filename: Имя файла (опционально)
            
        Returns:
            str: Путь к сохраненному файлу относительно storage
        """
        try:
            # Создать директорию для урока
            lesson_dir = self.videos_path / str(lesson_id)
            lesson_dir.mkdir(exist_ok=True)
            
            # Определить имя файла
            if not filename:
                filename = f"lesson_{lesson_id}.mp4"
            
            # Проверить расширение
            file_ext = Path(filename).suffix.lower()
            if file_ext not in self.video_formats:
                raise ValueError(f"Unsupported video format: {file_ext}")
            
            # Полный путь к файлу
            video_path = lesson_dir / filename
            
            # Сохранить файл
            async with aiofiles.open(video_path, 'wb') as f:
                await f.write(video_data)
            
            # Относительный путь
            relative_path = f"videos/{lesson_id}/{filename}"
            
            logger.info(f"✅ Video stored for lesson {lesson_id}: {relative_path}")
            return relative_path
            
        except Exception as e:
            logger.error(f"❌ Error storing video for lesson {lesson_id}: {e}")
            raise
    
    async def store_lesson_text(self, lesson_id: int, text_content: str, filename: str = None) -> str:
        """
        Сохранить текстовый контент урока.
        
        Args:
            lesson_id: ID урока
            text_content: Текстовое содержимое
            filename: Имя файла (опционально)
            
        Returns:
            str: Путь к сохраненному файлу
        """
        try:
            # Создать директорию для урока
            lesson_dir = self.texts_path / str(lesson_id)
            lesson_dir.mkdir(exist_ok=True)
            
            # Определить имя файла
            if not filename:
                filename = f"lesson_{lesson_id}.txt"
            
            # Полный путь к файлу
            text_path = lesson_dir / filename
            
            # Сохранить файл
            async with aiofiles.open(text_path, 'w', encoding='utf-8') as f:
                await f.write(text_content)
            
            # Относительный путь
            relative_path = f"texts/{lesson_id}/{filename}"
            
            logger.info(f"✅ Text stored for lesson {lesson_id}: {relative_path}")
            return relative_path
            
        except Exception as e:
            logger.error(f"❌ Error storing text for lesson {lesson_id}: {e}")
            raise
    
    async def get_lesson_content(self, lesson_id: int) -> Dict[str, Any]:
        """
        Получить весь контент урока.
        
        Args:
            lesson_id: ID урока
            
        Returns:
            Dict[str, Any]: Информация о контенте урока
        """
        content_info = {
            'lesson_id': lesson_id,
            'video': None,
            'text': None,
            'thumbnails': [],
            'files': []
        }
        
        try:
            # Проверить видео файлы
            video_dir = self.videos_path / str(lesson_id)
            if video_dir.exists():
                for video_file in video_dir.iterdir():
                    if video_file.is_file() and video_file.suffix.lower() in self.video_formats:
                        content_info['video'] = {
                            'path': str(video_file),
                            'relative_path': f"videos/{lesson_id}/{video_file.name}",
                            'size': video_file.stat().st_size,
                            'format': video_file.suffix.lower()
                        }
                        break
            
            # Проверить текстовые файлы
            text_dir = self.texts_path / str(lesson_id)
            if text_dir.exists():
                for text_file in text_dir.iterdir():
                    if text_file.is_file() and text_file.suffix.lower() in self.text_formats:
                        async with aiofiles.open(text_file, 'r', encoding='utf-8') as f:
                            text_content = await f.read()
                        
                        content_info['text'] = {
                            'path': str(text_file),
                            'relative_path': f"texts/{lesson_id}/{text_file.name}",
                            'content': text_content,
                            'length': len(text_content)
                        }
                        break
            
            # Проверить превью
            thumbnail_dir = self.thumbnails_path / str(lesson_id)
            if thumbnail_dir.exists():
                for thumb_file in thumbnail_dir.iterdir():
                    if thumb_file.is_file():
                        content_info['thumbnails'].append({
                            'path': str(thumb_file),
                            'relative_path': f"thumbnails/{lesson_id}/{thumb_file.name}",
                            'size': thumb_file.stat().st_size
                        })
            
            return content_info
            
        except Exception as e:
            logger.error(f"❌ Error getting lesson content for {lesson_id}: {e}")
            return content_info
    
    async def send_video_to_user(
        self, 
        bot: Bot, 
        user_id: int, 
        video_path: str, 
        caption: str = None,
        thumbnail_path: str = None
    ) -> bool:
        """
        Отправить видео пользователю.
        
        Args:
            bot: Экземпляр бота
            user_id: ID пользователя
            video_path: Путь к видео файлу
            caption: Подпись к видео
            thumbnail_path: Путь к превью (опционально)
            
        Returns:
            bool: True если отправлено успешно
        """
        try:
            # Полный путь к видео
            full_path = self.storage_path / video_path
            
            if not full_path.exists():
                logger.error(f"Video file not found: {full_path}")
                return False
            
            # Проверить размер файла
            file_size = full_path.stat().st_size
            if file_size > self.max_video_size:
                logger.error(f"Video file too large: {file_size} bytes")
                # TODO: Можно реализовать разбивку на части или внешние ссылки
                return False
            
            # Подготовить превью
            thumbnail_file = None
            if thumbnail_path:
                thumbnail_full_path = self.storage_path / thumbnail_path
                if thumbnail_full_path.exists():
                    thumbnail_file = open(thumbnail_full_path, 'rb')
            
            # Отправить видео
            with open(full_path, 'rb') as video_file:
                await bot.send_video(
                    chat_id=user_id,
                    video=InputFile(video_file, filename=full_path.name),
                    caption=caption,
                    thumbnail=thumbnail_file,
                    parse_mode=ParseMode.HTML,
                    supports_streaming=True
                )
            
            # Закрыть файл превью
            if thumbnail_file:
                thumbnail_file.close()
            
            logger.info(f"✅ Video sent to user {user_id}: {video_path}")
            return True
            
        except TelegramError as e:
            logger.error(f"❌ Telegram error sending video to {user_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error sending video to {user_id}: {e}")
            return False
    
    async def send_text_to_user(
        self, 
        bot: Bot, 
        user_id: int, 
        text_content: str,
        title: str = None
    ) -> bool:
        """
        Отправить текстовый контент пользователю.
        
        Args:
            bot: Экземпляр бота
            user_id: ID пользователя 
            text_content: Текстовое содержимое
            title: Заголовок (опционально)
            
        Returns:
            bool: True если отправлено успешно
        """
        try:
            # Подготовить текст
            full_text = ""
            
            if title:
                full_text += f"📖 <b>{title}</b>\n\n"
            
            # Проверить длину текста
            remaining_length = self.max_text_length - len(full_text)
            
            if len(text_content) > remaining_length:
                # Разбить на части
                text_parts = self._split_text(text_content, remaining_length)
                
                # Отправить первую часть с заголовком
                await bot.send_message(
                    chat_id=user_id,
                    text=full_text + text_parts[0],
                    parse_mode=ParseMode.HTML
                )
                
                # Отправить остальные части
                for part in text_parts[1:]:
                    await bot.send_message(
                        chat_id=user_id,
                        text=part,
                        parse_mode=ParseMode.HTML
                    )
            else:
                # Отправить одним сообщением
                await bot.send_message(
                    chat_id=user_id,
                    text=full_text + text_content,
                    parse_mode=ParseMode.HTML
                )
            
            logger.info(f"✅ Text content sent to user {user_id}")
            return True
            
        except TelegramError as e:
            logger.error(f"❌ Telegram error sending text to {user_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error sending text to {user_id}: {e}")
            return False
    
    def _split_text(self, text: str, max_length: int) -> List[str]:
        """
        Разбить длинный текст на части.
        
        Args:
            text: Исходный текст
            max_length: Максимальная длина части
            
        Returns:
            List[str]: Список частей текста
        """
        if len(text) <= max_length:
            return [text]
        
        parts = []
        current_pos = 0
        
        while current_pos < len(text):
            # Найти хорошее место для разбивки (предложение, абзац)
            end_pos = min(current_pos + max_length, len(text))
            
            if end_pos < len(text):
                # Попытаться найти конец предложения
                for i in range(end_pos, current_pos, -1):
                    if text[i] in '.!?\n':
                        end_pos = i + 1
                        break
                else:
                    # Если не нашли, найти пробел
                    for i in range(end_pos, current_pos, -1):
                        if text[i] == ' ':
                            end_pos = i
                            break
            
            part = text[current_pos:end_pos].strip()
            if part:
                parts.append(part)
            
            current_pos = end_pos
        
        return parts
    
    async def delete_lesson_content(self, lesson_id: int) -> bool:
        """
        Удалить весь контент урока.
        
        Args:
            lesson_id: ID урока
            
        Returns:
            bool: True если удалено успешно
        """
        try:
            deleted_something = False
            
            # Удалить видео
            video_dir = self.videos_path / str(lesson_id)
            if video_dir.exists():
                for file in video_dir.iterdir():
                    file.unlink()
                video_dir.rmdir()
                deleted_something = True
            
            # Удалить текстовые файлы
            text_dir = self.texts_path / str(lesson_id)
            if text_dir.exists():
                for file in text_dir.iterdir():
                    file.unlink()
                text_dir.rmdir()
                deleted_something = True
            
            # Удалить превью
            thumbnail_dir = self.thumbnails_path / str(lesson_id)
            if thumbnail_dir.exists():
                for file in thumbnail_dir.iterdir():
                    file.unlink()
                thumbnail_dir.rmdir()
                deleted_something = True
            
            if deleted_something:
                logger.info(f"✅ Content deleted for lesson {lesson_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting content for lesson {lesson_id}: {e}")
            return False
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Получить статистику использования хранилища.
        
        Returns:
            Dict[str, Any]: Статистика хранилища
        """
        stats = {
            'total_size': 0,
            'videos': {'count': 0, 'size': 0},
            'texts': {'count': 0, 'size': 0},
            'thumbnails': {'count': 0, 'size': 0}
        }
        
        try:
            # Подсчитать видео
            if self.videos_path.exists():
                for video_dir in self.videos_path.iterdir():
                    if video_dir.is_dir():
                        for video_file in video_dir.iterdir():
                            if video_file.is_file():
                                size = video_file.stat().st_size
                                stats['videos']['count'] += 1
                                stats['videos']['size'] += size
                                stats['total_size'] += size
            
            # Подсчитать тексты
            if self.texts_path.exists():
                for text_dir in self.texts_path.iterdir():
                    if text_dir.is_dir():
                        for text_file in text_dir.iterdir():
                            if text_file.is_file():
                                size = text_file.stat().st_size
                                stats['texts']['count'] += 1
                                stats['texts']['size'] += size
                                stats['total_size'] += size
            
            # Подсчитать превью
            if self.thumbnails_path.exists():
                for thumb_dir in self.thumbnails_path.iterdir():
                    if thumb_dir.is_dir():
                        for thumb_file in thumb_dir.iterdir():
                            if thumb_file.is_file():
                                size = thumb_file.stat().st_size
                                stats['thumbnails']['count'] += 1
                                stats['thumbnails']['size'] += size
                                stats['total_size'] += size
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
        
        return stats


# Создание глобального экземпляра менеджера контента
content_manager = ContentManager()


# Удобные функции
async def deliver_lesson_to_user(bot: Bot, user_id: int, lesson: Dict[str, Any]) -> bool:
    """
    Доставить урок пользователю.
    
    Args:
        bot: Экземпляр бота
        user_id: ID пользователя
        lesson: Данные урока
        
    Returns:
        bool: True если доставлено успешно
    """
    try:
        success = False
        
        # Отправить видео если есть
        if lesson.get('video_path'):
            video_success = await content_manager.send_video_to_user(
                bot=bot,
                user_id=user_id,
                video_path=lesson.get('video_path'),
                caption=f"📖 {lesson.get('title', '')}"
            )
            if video_success:
                success = True
        
        # Отправить текст если есть
        if lesson.get('text_content'):
            text_success = await content_manager.send_text_to_user(
                bot=bot,
                user_id=user_id,
                text_content=lesson.get('text_content'),
                title=lesson.get('title', '') if not lesson.get('video_path') else None
            )
            if text_success:
                success = True
        
        return success
        
    except Exception as e:
        logger.error(f"Error delivering lesson to user: {e}")
        return False