"""
Тесты для системы интернационализации.
"""

import pytest
import json
import tempfile
from pathlib import Path

from bot.utils.i18n import TranslationManager, get_text


class TestTranslationManager:
    """Тесты для менеджера переводов."""
    
    @pytest.fixture
    def temp_locales_dir(self):
        """Создать временную директорию с переводами для тестов."""
        with tempfile.TemporaryDirectory() as temp_dir:
            locales_path = Path(temp_dir)
            
            # Создать английские переводы
            en_dir = locales_path / "en"
            en_dir.mkdir()
            
            en_messages = {
                "welcome": "Welcome to Bot!",
                "menu": {
                    "browse": "Browse Items",
                    "settings": "Settings"
                },
                "price": "Price: {amount} stars"
            }
            
            with open(en_dir / "messages.json", "w") as f:
                json.dump(en_messages, f)
            
            # Создать русские переводы
            ru_dir = locales_path / "ru"
            ru_dir.mkdir()
            
            ru_messages = {
                "welcome": "Добро пожаловать в Бот!",
                "menu": {
                    "browse": "Просмотр товаров", 
                    "settings": "Настройки"
                },
                "price": "Цена: {amount} звезд"
            }
            
            with open(ru_dir / "messages.json", "w") as f:
                json.dump(ru_messages, f)
            
            yield str(locales_path)
    
    def test_load_translations(self, temp_locales_dir):
        """Тест загрузки переводов."""
        manager = TranslationManager(temp_locales_dir)
        
        # Проверить, что языки загружены
        assert "en" in manager.supported_languages
        assert "ru" in manager.supported_languages
        
        # Проверить содержимое переводов
        assert "welcome" in manager.translations["en"]
        assert "welcome" in manager.translations["ru"]
    
    def test_get_text_simple(self, temp_locales_dir):
        """Тест получения простого перевода."""
        manager = TranslationManager(temp_locales_dir)
        
        # Английский
        en_text = manager.get_text("welcome", "en")
        assert en_text == "Welcome to Bot!"
        
        # Русский
        ru_text = manager.get_text("welcome", "ru")
        assert ru_text == "Добро пожаловать в Бот!"
    
    def test_get_text_nested(self, temp_locales_dir):
        """Тест получения вложенного перевода."""
        manager = TranslationManager(temp_locales_dir)
        
        # Английский
        en_text = manager.get_text("menu.browse", "en")
        assert en_text == "Browse Items"
        
        # Русский
        ru_text = manager.get_text("menu.settings", "ru")
        assert ru_text == "Настройки"
    
    def test_get_text_with_formatting(self, temp_locales_dir):
        """Тест получения перевода с форматированием."""
        manager = TranslationManager(temp_locales_dir)
        
        # Английский с параметрами
        en_text = manager.get_text("price", "en", amount=100)
        assert en_text == "Price: 100 stars"
        
        # Русский с параметрами
        ru_text = manager.get_text("price", "ru", amount=50)
        assert ru_text == "Цена: 50 звезд"
    
    def test_fallback_to_default_language(self, temp_locales_dir):
        """Тест fallback на язык по умолчанию."""
        manager = TranslationManager(temp_locales_dir)
        
        # Запросить перевод для несуществующего языка
        text = manager.get_text("welcome", "fr")
        
        # Должен вернуть английский (по умолчанию)
        assert text == "Welcome to Bot!"
    
    def test_missing_translation_key(self, temp_locales_dir):
        """Тест обработки отсутствующего ключа перевода."""
        manager = TranslationManager(temp_locales_dir)
        
        # Запросить несуществующий ключ
        text = manager.get_text("nonexistent.key", "en")
        
        # Должен вернуть ключ как есть
        assert text == "nonexistent.key"
    
    def test_format_price(self, temp_locales_dir):
        """Тест форматирования цены."""
        manager = TranslationManager(temp_locales_dir)
        
        # Английский
        en_price = manager.format_price(1, "en")
        assert "1 ⭐ star" in en_price
        
        en_price_plural = manager.format_price(5, "en")
        assert "5 ⭐ stars" in en_price_plural
        
        # Русский
        ru_price_1 = manager.format_price(1, "ru")
        assert "1 ⭐ звезда" in ru_price_1
        
        ru_price_2 = manager.format_price(2, "ru")
        assert "2 ⭐ звезды" in ru_price_2
        
        ru_price_5 = manager.format_price(5, "ru")
        assert "5 ⭐ звезд" in ru_price_5
    
    def test_get_supported_languages(self, temp_locales_dir):
        """Тест получения списка поддерживаемых языков."""
        manager = TranslationManager(temp_locales_dir)
        
        languages = manager.get_supported_languages()
        
        # Проверить структуру
        assert isinstance(languages, list)
        assert len(languages) >= 2
        
        # Проверить содержимое
        lang_codes = [lang['code'] for lang in languages]
        assert 'en' in lang_codes
        assert 'ru' in lang_codes
        
        # Проверить наличие флагов
        for lang in languages:
            assert 'name' in lang
            assert '🇺🇸' in lang['name'] or '🇷🇺' in lang['name']


def test_global_get_text_function():
    """Тест глобальной функции get_text."""
    # Тест с базовой функциональностью
    text = get_text("nonexistent.key", "en")
    assert text == "nonexistent.key"  # Fallback
    
    # Тест с форматированием
    text_with_params = get_text("test.key", "en", param="value")
    assert "test.key" in text_with_params  # Должен вернуть ключ при отсутствии перевода


class TestLanguageDetection:
    """Тесты определения и обработки языков."""
    
    def test_language_flag_mapping(self):
        """Тест маппинга флагов языков."""
        from bot.utils.i18n import TranslationManager
        
        manager = TranslationManager()
        
        # Проверить известные флаги
        assert manager.get_language_flag('en') == '🇺🇸'
        assert manager.get_language_flag('ru') == '🇷🇺'
        assert manager.get_language_flag('unknown') == '🌐'