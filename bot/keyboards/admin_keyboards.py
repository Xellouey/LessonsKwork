"""
Клавиатуры для админ-панели бота.
Включает меню для управления уроками, статистики, рассылок и настроек.
"""

from typing import List
from telegram import InlineKeyboardButton


class AdminKeyboards:
    """Клавиатуры для админ-панели."""
    
    def get_admin_main_menu(self) -> List[List[InlineKeyboardButton]]:
        """Главное меню админ-панели."""
        return [
            [
                InlineKeyboardButton("📚 Управление уроками", callback_data="admin:lessons"),
                InlineKeyboardButton("👥 Статистика", callback_data="admin:users")
            ],
            [
                InlineKeyboardButton("📢 Рассылка", callback_data="admin:broadcast"),
                InlineKeyboardButton("⚙️ Настройки", callback_data="admin:settings")
            ],
            [
                InlineKeyboardButton("🔄 Обновить", callback_data="admin:refresh")
            ]
        ]
    
    def get_lesson_management_menu(self) -> List[List[InlineKeyboardButton]]:
        """Меню управления уроками."""
        return [
            [
                InlineKeyboardButton("➕ Добавить урок", callback_data="lesson:add"),
                InlineKeyboardButton("📝 Редактировать", callback_data="lesson:edit")
            ],
            [
                InlineKeyboardButton("📋 Список уроков", callback_data="lesson:list"),
                InlineKeyboardButton("🗑️ Удалить урок", callback_data="lesson:delete")
            ],
            [
                InlineKeyboardButton("🔄 Курсы", callback_data="course:manage"),
                InlineKeyboardButton("🎁 Промокоды", callback_data="promo:manage")
            ],
            [
                InlineKeyboardButton("🔙 Назад", callback_data="admin:back")
            ]
        ]
    
    def get_lesson_edit_menu(self, lesson_id: int) -> List[List[InlineKeyboardButton]]:
        """Меню редактирования урока."""
        return [
            [
                InlineKeyboardButton("📝 Название", callback_data=f"lesson:edit_title:{lesson_id}"),
                InlineKeyboardButton("📄 Описание", callback_data=f"lesson:edit_desc:{lesson_id}")
            ],
            [
                InlineKeyboardButton("💰 Цена", callback_data=f"lesson:edit_price:{lesson_id}"),
                InlineKeyboardButton("📹 Контент", callback_data=f"lesson:edit_content:{lesson_id}")
            ],
            [
                InlineKeyboardButton("✅ Активный", callback_data=f"lesson:toggle_active:{lesson_id}"),
                InlineKeyboardButton("🆓 Бесплатный", callback_data=f"lesson:toggle_free:{lesson_id}")
            ],
            [
                InlineKeyboardButton("🔙 К урокам", callback_data="admin:lessons"),
                InlineKeyboardButton("🗑️ Удалить", callback_data=f"lesson:confirm_delete:{lesson_id}")
            ]
        ]
    
    def get_lesson_list_menu(self, page: int = 0) -> List[List[InlineKeyboardButton]]:
        """Меню списка уроков с пагинацией."""
        keyboard = []
        
        # Кнопки навигации по страницам
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"lesson:page:{page-1}"))
        nav_row.append(InlineKeyboardButton("➡️ Далее", callback_data=f"lesson:page:{page+1}"))
        
        if nav_row:
            keyboard.append(nav_row)
        
        keyboard.append([
            InlineKeyboardButton("🔙 К управлению", callback_data="admin:lessons")
        ])
        
        return keyboard
    
    def get_settings_menu(self) -> List[List[InlineKeyboardButton]]:
        """Меню настроек."""
        return [
            [
                InlineKeyboardButton("📝 Тексты сообщений", callback_data="settings:messages"),
                InlineKeyboardButton("🔘 Названия кнопок", callback_data="settings:buttons")
            ],
            [
                InlineKeyboardButton("🎨 Общие настройки", callback_data="settings:general"),
                InlineKeyboardButton("🔔 Уведомления", callback_data="settings:notifications")
            ],
            [
                InlineKeyboardButton("➕ Добавить настройку", callback_data="settings:add"),
                InlineKeyboardButton("📋 Все настройки", callback_data="settings:list")
            ],
            [
                InlineKeyboardButton("🔙 Назад", callback_data="admin:back")
            ]
        ]
    
    def get_settings_category_menu(self, category: str) -> List[List[InlineKeyboardButton]]:
        """Меню настроек по категории."""
        return [
            [
                InlineKeyboardButton("➕ Добавить", callback_data=f"settings:add:{category}"),
                InlineKeyboardButton("📝 Редактировать", callback_data=f"settings:edit:{category}")
            ],
            [
                InlineKeyboardButton("🔙 К настройкам", callback_data="admin:settings"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="admin:back")
            ]
        ]
    
    def get_broadcast_menu(self) -> List[List[InlineKeyboardButton]]:
        """Меню рассылки."""
        return [
            [
                InlineKeyboardButton("📢 Всем пользователям", callback_data="broadcast:all"),
                InlineKeyboardButton("👑 Только админам", callback_data="broadcast:admins")
            ],
            [
                InlineKeyboardButton("🛒 Покупателям", callback_data="broadcast:buyers"),
                InlineKeyboardButton("🆕 Новым пользователям", callback_data="broadcast:new")
            ],
            [
                InlineKeyboardButton("🔙 Назад", callback_data="admin:back")
            ]
        ]
    
    def get_confirm_broadcast_menu(self, target: str) -> List[List[InlineKeyboardButton]]:
        """Меню подтверждения рассылки."""
        return [
            [
                InlineKeyboardButton("✅ Отправить", callback_data=f"broadcast:confirm:{target}"),
                InlineKeyboardButton("❌ Отмена", callback_data="admin:broadcast")
            ]
        ]
    
    def get_user_management_menu(self) -> List[List[InlineKeyboardButton]]:
        """Меню управления пользователями."""
        return [
            [
                InlineKeyboardButton("👑 Назначить админа", callback_data="user:make_admin"),
                InlineKeyboardButton("👤 Снять админа", callback_data="user:remove_admin")
            ],
            [
                InlineKeyboardButton("🚫 Заблокировать", callback_data="user:block"),
                InlineKeyboardButton("✅ Разблокировать", callback_data="user:unblock")
            ],
            [
                InlineKeyboardButton("📋 Все пользователи", callback_data="user:list"),
                InlineKeyboardButton("🔍 Поиск пользователя", callback_data="user:search")
            ],
            [
                InlineKeyboardButton("🔙 Назад", callback_data="admin:back")
            ]
        ]
    
    def get_promo_management_menu(self) -> List[List[InlineKeyboardButton]]:
        """Меню управления промокодами."""
        return [
            [
                InlineKeyboardButton("➕ Создать промокод", callback_data="promo:create"),
                InlineKeyboardButton("📋 Список промокодов", callback_data="promo:list")
            ],
            [
                InlineKeyboardButton("📊 Статистика использования", callback_data="promo:stats"),
                InlineKeyboardButton("🗑️ Удалить промокод", callback_data="promo:delete")
            ],
            [
                InlineKeyboardButton("🔙 К урокам", callback_data="admin:lessons")
            ]
        ]
    
    def get_course_management_menu(self) -> List[List[InlineKeyboardButton]]:
        """Меню управления курсами."""
        return [
            [
                InlineKeyboardButton("➕ Создать курс", callback_data="course:create"),
                InlineKeyboardButton("📋 Список курсов", callback_data="course:list")
            ],
            [
                InlineKeyboardButton("📝 Редактировать курс", callback_data="course:edit"),
                InlineKeyboardButton("🗑️ Удалить курс", callback_data="course:delete")
            ],
            [
                InlineKeyboardButton("🔙 К урокам", callback_data="admin:lessons")
            ]
        ]
    
    def get_back_to_admin_menu(self) -> List[List[InlineKeyboardButton]]:
        """Кнопка возврата в главное меню админ-панели."""
        return [
            [
                InlineKeyboardButton("🔙 В главное меню", callback_data="admin:back")
            ]
        ]
    
    def get_confirmation_menu(self, action: str, item_id: str = None) -> List[List[InlineKeyboardButton]]:
        """Меню подтверждения действия."""
        confirm_data = f"confirm:{action}"
        cancel_data = f"cancel:{action}"
        
        if item_id:
            confirm_data += f":{item_id}"
            cancel_data += f":{item_id}"
        
        return [
            [
                InlineKeyboardButton("✅ Подтвердить", callback_data=confirm_data),
                InlineKeyboardButton("❌ Отмена", callback_data=cancel_data)
            ]
        ]
    
    def get_yes_no_menu(self, action: str, item_id: str = None) -> List[List[InlineKeyboardButton]]:
        """Меню да/нет."""
        yes_data = f"yes:{action}"
        no_data = f"no:{action}"
        
        if item_id:
            yes_data += f":{item_id}"
            no_data += f":{item_id}"
        
        return [
            [
                InlineKeyboardButton("✅ Да", callback_data=yes_data),
                InlineKeyboardButton("❌ Нет", callback_data=no_data)
            ]
        ]