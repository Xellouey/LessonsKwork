#!/usr/bin/env python3
"""
Скрипт для создания первого администратора бота.
Запустите этот скрипт для назначения пользователя администратором.
"""

import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.shared.database import init_database, get_db
from bot.shared.helper_functions import create_telegram_admin


def main():
    """Главная функция создания администратора."""
    print("🤖 Создание администратора бота")
    print("=" * 40)
    
    # Инициализируем базу данных
    try:
        init_database()
        print("✅ База данных инициализирована")
    except Exception as e:
        print(f"❌ Ошибка инициализации базы данных: {e}")
        return
    
    # Запрашиваем данные администратора
    try:
        telegram_id = input("Введите Telegram ID администратора: ").strip()
        
        if not telegram_id.isdigit():
            print("❌ Telegram ID должен быть числом")
            return
        
        telegram_id = int(telegram_id)
        
        username = input("Введите username (необязательно): ").strip() or None
        first_name = input("Введите имя (по умолчанию 'Admin'): ").strip() or "Admin"
        
        print(f"\n📋 Данные администратора:")
        print(f"   Telegram ID: {telegram_id}")
        print(f"   Username: {username or 'не указан'}")
        print(f"   Имя: {first_name}")
        
        confirm = input("\nПодтвердить создание? (y/N): ").strip().lower()
        
        if confirm != 'y':
            print("❌ Создание отменено")
            return
        
        # Создаем администратора
        db = next(get_db())
        try:
            admin_user = create_telegram_admin(
                db=db,
                telegram_id=telegram_id,
                username=username,
                first_name=first_name
            )
            
            if admin_user:
                print(f"\n✅ Администратор успешно создан!")
                print(f"   ID в базе: {admin_user.id}")
                print(f"   Telegram ID: {admin_user.telegram_id}")
                print(f"   Имя: {admin_user.first_name}")
                print(f"   Username: @{admin_user.username}" if admin_user.username else "   Username: не указан")
                print(f"\n🎉 Теперь пользователь может использовать команду /admin в боте!")
            else:
                print("❌ Ошибка создания администратора")
                
        finally:
            db.close()
            
    except KeyboardInterrupt:
        print("\n❌ Создание прервано пользователем")
    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    main()