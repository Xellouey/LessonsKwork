"""
Система интернационализации для Telegram бота.
Управление переводами, языками пользователей, форматирование текстов.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any, List

from bot.utils.api_client import BackendAPI


logger = logging.getLogger(__name__)


class TranslationManager:
    """Менеджер переводов и локализации."""
    
    def __init__(self, locales_path: str = "bot/locales"):
        self.locales_path = Path(locales_path)
        self.translations: Dict[str, Dict[str, Any]] = {}
        self.supported_languages: List[str] = []
        self.default_language = "en"
        self.user_languages: Dict[int, str] = {}  # Кеш языков пользователей
        
        self._load_translations()
    
    def _load_translations(self):
        """Загрузить все переводы из файлов."""
        try:
            if not self.locales_path.exists():
                logger.warning(f"Locales directory not found: {self.locales_path}")
                return
            
            for lang_dir in self.locales_path.iterdir():
                if lang_dir.is_dir() and lang_dir.name.isalpha():
                    lang_code = lang_dir.name
                    messages_file = lang_dir / "messages.json"
                    
                    if messages_file.exists():
                        try:
                            with open(messages_file, 'r', encoding='utf-8') as f:
                                translations = json.load(f)
                            
                            self.translations[lang_code] = translations
                            self.supported_languages.append(lang_code)
                            
                            logger.info(f"✅ Loaded translations for language: {lang_code}")
                        except Exception as e:
                            logger.error(f"❌ Error loading translations for {lang_code}: {e}")
            
            if self.supported_languages:
                logger.info(f"✅ Loaded translations for languages: {', '.join(self.supported_languages)}")
            else:
                logger.warning("⚠️ No translations loaded!")
                
        except Exception as e:
            logger.error(f"❌ Error loading translations: {e}")
    
    def get_text(self, key: str, lang: str = None, **kwargs) -> str:
        """
        Получить переведенный текст.
        
        Args:
            key: Ключ перевода (поддерживает точечную нотацию, например 'menu.browse_lessons')
            lang: Код языка
            **kwargs: Параметры для форматирования строки
            
        Returns:
            str: Переведенный текст
        """
        if not lang:
            lang = self.default_language
        
        # Fallback на английский, если язык не поддерживается
        if lang not in self.translations:
            lang = self.default_language
        
        # Fallback на первый доступный язык
        if lang not in self.translations and self.translations:
            lang = next(iter(self.translations.keys()))
        
        # Получение перевода
        translation = self._get_nested_value(self.translations.get(lang, {}), key)
        
        # Fallback на английский если перевод не найден
        if not translation and lang != self.default_language:
            translation = self._get_nested_value(self.translations.get(self.default_language, {}), key)
        
        # Если перевод не найден, возвращаем ключ
        if not translation:
            logger.warning(f"Translation not found: {key} for language {lang}")
            return key
        
        # Форматирование строки
        try:
            if kwargs:
                return translation.format(**kwargs)
            return translation
        except Exception as e:
            logger.error(f"Error formatting translation {key}: {e}")
            return translation
    
    def _get_nested_value(self, data: dict, key: str) -> Optional[str]:
        """
        Получить значение по вложенному ключу.
        
        Args:
            data: Словарь с данными
            key: Ключ (может быть вложенным с точками)
            
        Returns:
            Optional[str]: Значение или None
        """
        keys = key.split('.')
        current = data
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        
        return current if isinstance(current, str) else None
    
    async def get_user_language(self, user_id: int) -> str:
        """
        Получить язык пользователя.
        
        Args:
            user_id: ID пользователя Telegram
            
        Returns:
            str: Код языка пользователя
        """
        # Проверить кеш
        if user_id in self.user_languages:
            return self.user_languages[user_id]
        
        # Получить из API
        try:
            api_client = BackendAPI.get_client()
            user_data = await api_client.get_user(user_id)
            lang = user_data.get('language_code', self.default_language)
            
            # Проверить поддержку языка
            if lang not in self.supported_languages:
                lang = self.default_language
            
            # Кешировать
            self.user_languages[user_id] = lang
            return lang
            
        except Exception as e:
            logger.error(f"Error getting user language for {user_id}: {e}")
            return self.default_language
    
    async def set_user_language(self, user_id: int, language: str) -> bool:
        """
        Установить язык пользователя.
        
        Args:
            user_id: ID пользователя Telegram
            language: Код языка
            
        Returns:
            bool: True если успешно установлен
        """
        if language not in self.supported_languages:
            logger.warning(f"Unsupported language: {language}")
            return False
        
        try:
            # Обновить в API
            api_client = BackendAPI.get_client()
            await api_client.update_user(user_id, language_code=language)
            
            # Обновить кеш
            self.user_languages[user_id] = language
            
            logger.info(f"Set language for user {user_id}: {language}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting user language for {user_id}: {e}")
            return False
    
    async def get_user_text(self, user_id: int, key: str, **kwargs) -> str:
        """
        Получить переведенный текст для конкретного пользователя.
        
        Args:
            user_id: ID пользователя Telegram
            key: Ключ перевода
            **kwargs: Параметры для форматирования
            
        Returns:
            str: Переведенный текст
        """
        user_lang = await self.get_user_language(user_id)
        return self.get_text(key, user_lang, **kwargs)
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """
        Получить список поддерживаемых языков.
        
        Returns:
            List[Dict[str, str]]: Список языков с кодами и названиями
        """
        language_names = {
            'en': '🇺🇸 English',
            'ru': '🇷🇺 Русский',
            'uk': '🇺🇦 Українська',
            'es': '🇪🇸 Español',
            'fr': '🇫🇷 Français',
            'de': '🇩🇪 Deutsch',
            'it': '🇮🇹 Italiano',
            'pt': '🇧🇷 Português',
        }
        
        return [
            {
                'code': lang,
                'name': language_names.get(lang, lang.upper())
            }
            for lang in self.supported_languages
        ]
    
    def format_price(self, amount: int, lang: str = None) -> str:
        """
        Форматировать цену с символом Stars.
        
        Args:
            amount: Сумма в Stars
            lang: Код языка
            
        Returns:
            str: Отформатированная цена
        """
        if not lang:
            lang = self.default_language
        
        # Локализованное форматирование чисел
        if lang == 'ru':
            if amount == 1:
                return f"{amount} ⭐ звезда"
            elif 2 <= amount <= 4:
                return f"{amount} ⭐ звезды"
            else:
                return f"{amount} ⭐ звезд"
        else:
            # Английский и другие языки
            if amount == 1:
                return f"{amount} ⭐ star"
            else:
                return f"{amount} ⭐ stars"
    
    def format_duration(self, seconds: int, lang: str = None) -> str:
        """
        Форматировать продолжительность.
        
        Args:
            seconds: Продолжительность в секундах
            lang: Код языка
            
        Returns:
            str: Отформатированная продолжительность
        """
        if not lang:
            lang = self.default_language
        
        minutes = seconds // 60
        hours = minutes // 60
        
        if hours > 0:
            if lang == 'ru':
                return f"{hours} ч {minutes % 60} мин"
            else:
                return f"{hours}h {minutes % 60}m"
        else:
            if lang == 'ru':
                return f"{minutes} мин"
            else:
                return f"{minutes}m"
    
    def get_language_flag(self, lang_code: str) -> str:
        """Получить флаг для языка."""
        flags = {
            'en': '🇺🇸',
            'ru': '🇷🇺', 
            'uk': '🇺🇦',
            'es': '🇪🇸',
            'fr': '🇫🇷',
            'de': '🇩🇪',
            'it': '🇮🇹',
            'pt': '🇧🇷',
        }
        return flags.get(lang_code, '🌐')
    
    def clear_user_cache(self, user_id: Optional[int] = None):
        """
        Очистить кеш языков пользователей.
        
        Args:
            user_id: ID конкретного пользователя или None для очистки всего кеша
        """
        if user_id:
            self.user_languages.pop(user_id, None)
        else:
            self.user_languages.clear()
    
    def reload_translations(self):
        """Перезагрузить переводы из файлов."""
        self.translations.clear()
        self.supported_languages.clear()
        self._load_translations()


# Глобальный экземпляр менеджера переводов
i18n = TranslationManager()


# Удобные функции-сокращения
async def get_user_text(user_id: int, key: str, **kwargs) -> str:
    """Быстрый доступ к переводу для пользователя."""
    return await i18n.get_user_text(user_id, key, **kwargs)


def get_text(key: str, lang: str = 'en', **kwargs) -> str:
    """Быстрый доступ к переводу."""
    return i18n.get_text(key, lang, **kwargs)


async def set_user_language(user_id: int, language: str) -> bool:
    """Быстрая установка языка пользователя."""
    return await i18n.set_user_language(user_id, language)


async def get_user_language(user_id: int) -> str:
    """Быстрое получение языка пользователя."""
    return await i18n.get_user_language(user_id)