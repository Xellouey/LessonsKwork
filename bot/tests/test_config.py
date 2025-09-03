"""
Тесты конфигурации бота.
"""

import pytest
import os
import tempfile
from unittest.mock import patch

from bot.config import BotSettings, validate_bot_configuration


class TestBotSettings:
    """Тесты настроек бота."""
    
    def test_bot_settings_validation_success(self):
        """Тест успешной валидации настроек."""
        with patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': '1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk',
            'BACKEND_API_URL': 'http://localhost:8000',
            'ADMIN_CHAT_ID': '123456789'
        }):
            settings = BotSettings()
            
            assert settings.telegram_bot_token is not None
            assert settings.backend_api_url == 'http://localhost:8000'
            assert settings.admin_chat_id == 123456789
    
    def test_bot_settings_validation_failure(self):
        """Тест неудачной валидации настроек."""
        with patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': 'invalid',  # Слишком короткий токен
        }, clear=True):
            with pytest.raises(ValueError):
                BotSettings()
    
    def test_supported_languages_parsing(self):
        """Тест парсинга поддерживаемых языков."""
        with patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': '1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk',
            'SUPPORTED_LANGUAGES': 'en,ru,es,fr'
        }):
            settings = BotSettings()
            
            assert settings.supported_languages == ['en', 'ru', 'es', 'fr']
    
    def test_storage_path_methods(self):
        """Тест методов работы с путями хранилища."""
        with patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': '1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk',
            'MEDIA_STORAGE_PATH': '/tmp/storage'
        }):
            settings = BotSettings()
            
            assert settings.get_storage_path() == '/tmp/storage'
            assert settings.get_storage_path('videos') == '/tmp/storage/videos'
    
    def test_is_admin_method(self):
        """Тест проверки прав администратора."""
        with patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': '1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk',
            'ADMIN_CHAT_ID': '123456789'
        }):
            settings = BotSettings()
            
            assert settings.is_admin(123456789) is True
            assert settings.is_admin(987654321) is False


class TestBotConfigurationValidation:
    """Тесты валидации конфигурации бота."""
    
    @patch('bot.config.settings')
    def test_validate_bot_configuration_success(self, mock_settings):
        """Тест успешной валидации конфигурации."""
        # Настроить mock
        mock_settings.telegram_bot_token = '1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk'
        mock_settings.backend_api_url = 'http://localhost:8000'
        mock_settings.get_storage_path = lambda x=None: f'/tmp/storage/{x}' if x else '/tmp/storage'
        
        # Создать временные директории
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('os.makedirs') as mock_makedirs:
                result = validate_bot_configuration()
                
                assert result is True
                # Проверить, что директории создаются
                assert mock_makedirs.call_count >= 3
    
    @patch('bot.config.settings')
    def test_validate_bot_configuration_no_token(self, mock_settings):
        """Тест валидации без токена бота."""
        mock_settings.telegram_bot_token = None
        
        result = validate_bot_configuration()
        assert result is False
    
    @patch('bot.config.settings')
    def test_validate_bot_configuration_no_api_url(self, mock_settings):
        """Тест валидации без URL API."""
        mock_settings.telegram_bot_token = '1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk'
        mock_settings.backend_api_url = None
        
        result = validate_bot_configuration()
        assert result is False


class TestLogConfiguration:
    """Тесты конфигурации логирования."""
    
    def test_get_log_config(self):
        """Тест получения конфигурации логирования."""
        from bot.config import get_log_config
        
        config = get_log_config()
        
        # Проверить структуру конфигурации
        assert 'version' in config
        assert 'formatters' in config
        assert 'handlers' in config
        assert 'loggers' in config
        
        # Проверить наличие стандартного форматера
        assert 'standard' in config['formatters']
        
        # Проверить наличие обработчика по умолчанию
        assert 'default' in config['handlers']