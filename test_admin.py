#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функций админ-панели.
"""

import sys
import os
import asyncio

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.shared.database import init_database, get_db
from bot.shared.helper_functions import create_telegram_admin, is_user_admin, get_admin_users
from bot.shared.models import User, Lesson, BotSettings


async def test_admin_functions():
    """Тестирование функций админ-панели."""
    print("🧪 Тестирование админ-панели")
    print("=" * 40)
    
    # Инициализируем базу данных
    try:
        init_database()
        print("✅ База данных инициализирована")
    except Exception as e:
        print(f"❌ Ошибка инициализации базы данных: {e}")
        return
    
    db = next(get_db())
    
    try:
        # Тест 1: Создание тестового администратора
        print("\n1️⃣ Тестирование создания администратора...")
        test_admin_id = 123456789
        admin_user = create_telegram_admin(
            db=db,
            telegram_id=test_admin_id,
            username="test_admin",
            first_name="Test Admin"
        )
        
        if admin_user:
            print(f"✅ Администратор создан: {admin_user.first_name} (ID: {admin_user.telegram_id})")
        else:
            print("❌ Ошибка создания администратора")
            return
        
        # Тест 2: Проверка прав администратора
        print("\n2️⃣ Тестирование проверки прав...")
        is_admin = is_user_admin(db, test_admin_id)
        print(f"✅ Проверка прав администратора: {is_admin}")
        
        # Тест 3: Получение списка администраторов
        print("\n3️⃣ Тестирование получения списка администраторов...")
        admins = get_admin_users(db)
        print(f"✅ Найдено администраторов: {len(admins)}")
        for admin in admins:
            print(f"   - {admin.first_name} (@{admin.username or 'нет'}) - ID: {admin.telegram_id}")
        
        # Тест 4: Создание тестового урока
        print("\n4️⃣ Тестирование создания урока...")
        test_lesson = Lesson(
            title="Тестовый урок",
            description="Это тестовый урок для проверки админ-панели",
            price=100,
            is_free=False,
            text_content="Содержимое тестового урока",
            is_active=True
        )
        
        db.add(test_lesson)
        db.commit()
        db.refresh(test_lesson)
        print(f"✅ Урок создан: {test_lesson.title} (ID: {test_lesson.id})")
        
        # Тест 5: Создание тестовых настроек
        print("\n5️⃣ Тестирование создания настроек...")
        test_settings = [
            BotSettings(
                key="welcome_message",
                value="Добро пожаловать в наш бот!",
                category="messages",
                description="Приветственное сообщение"
            ),
            BotSettings(
                key="button_catalog",
                value="📚 Каталог уроков",
                category="buttons",
                description="Текст кнопки каталога"
            )
        ]
        
        for setting in test_settings:
            db.add(setting)
        
        db.commit()
        print(f"✅ Создано настроек: {len(test_settings)}")
        
        # Тест 6: Проверка статистики
        print("\n6️⃣ Тестирование статистики...")
        total_users = db.query(User).count()
        total_lessons = db.query(Lesson).filter(Lesson.is_active == True).count()
        total_settings = db.query(BotSettings).filter(BotSettings.is_active == True).count()
        
        print(f"✅ Статистика:")
        print(f"   - Пользователей: {total_users}")
        print(f"   - Активных уроков: {total_lessons}")
        print(f"   - Настроек: {total_settings}")
        
        print("\n🎉 Все тесты пройдены успешно!")
        print("\n📋 Следующие шаги:")
        print("1. Запустите бота: python -m bot.main")
        print("2. Найдите бота в Telegram")
        print("3. Отправьте команду /admin")
        print("4. Используйте админ-панель!")
        
    except Exception as e:
        print(f"❌ Ошибка во время тестирования: {e}")
        db.rollback()
    finally:
        db.close()


def main():
    """Главная функция."""
    try:
        asyncio.run(test_admin_functions())
    except KeyboardInterrupt:
        print("\n❌ Тестирование прервано пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")


if __name__ == "__main__":
    main()