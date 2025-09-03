"""
Основные клавиатуры для Telegram бота.
InlineKeyboard для навигации, меню, покупок и управления.
"""

import logging
from typing import List, Optional, Dict, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.utils.i18n import get_text


logger = logging.getLogger(__name__)


class KeyboardBuilder:
    """Строитель клавиатур с поддержкой локализации."""
    
    @staticmethod
    def main_menu(lang: str = "en") -> InlineKeyboardMarkup:
        """
        Главное меню бота.
        
        Args:
            lang: Код языка
            
        Returns:
            InlineKeyboardMarkup: Клавиатура главного меню
        """
        keyboard = [
            [
                InlineKeyboardButton(
                    get_text("main_menu.browse_lessons", lang),
                    callback_data="menu:browse_lessons"
                )
            ],
            [
                InlineKeyboardButton(
                    get_text("main_menu.my_lessons", lang),
                    callback_data="menu:my_lessons"
                )
            ],
            [
                InlineKeyboardButton(
                    get_text("main_menu.support", lang),
                    callback_data="menu:support"
                ),
                InlineKeyboardButton(
                    get_text("main_menu.language", lang),
                    callback_data="menu:language"
                )
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def lessons_catalog(
        lessons: List[Dict[str, Any]], 
        page: int = 1, 
        total_pages: int = 1,
        lang: str = "en"
    ) -> InlineKeyboardMarkup:
        """
        Клавиатура каталога уроков с пагинацией.
        
        Args:
            lessons: Список уроков
            page: Текущая страница
            total_pages: Общее количество страниц
            lang: Код языка
            
        Returns:
            InlineKeyboardMarkup: Клавиатура каталога
        """
        keyboard = []
        
        # Кнопки уроков (по 2 в ряд)
        for i in range(0, len(lessons), 2):
            row = []
            
            # Первый урок в ряду
            lesson = lessons[i]
            price_text = get_text("common.free", lang) if lesson.get('is_free') else f"{lesson.get('price', 0)} ⭐"
            button_text = f"📖 {lesson.get('title', '')[:20]}{'...' if len(lesson.get('title', '')) > 20 else ''}\n💰 {price_text}"
            
            row.append(InlineKeyboardButton(
                button_text,
                callback_data=f"lesson:view:{lesson.get('id')}"
            ))
            
            # Второй урок в ряду (если есть)
            if i + 1 < len(lessons):
                lesson2 = lessons[i + 1]
                price_text2 = get_text("common.free", lang) if lesson2.get('is_free') else f"{lesson2.get('price', 0)} ⭐"
                button_text2 = f"📖 {lesson2.get('title', '')[:20]}{'...' if len(lesson2.get('title', '')) > 20 else ''}\n💰 {price_text2}"
                
                row.append(InlineKeyboardButton(
                    button_text2,
                    callback_data=f"lesson:view:{lesson2.get('id')}"
                ))
            
            keyboard.append(row)
        
        # Пагинация
        if total_pages > 1:
            pagination_row = []
            
            if page > 1:
                pagination_row.append(InlineKeyboardButton(
                    get_text("lessons.prev_page", lang),
                    callback_data=f"catalog:page:{page - 1}"
                ))
            
            # Информация о странице
            pagination_row.append(InlineKeyboardButton(
                get_text("lessons.page_info", lang, current=page, total=total_pages),
                callback_data="page_info"
            ))
            
            if page < total_pages:
                pagination_row.append(InlineKeyboardButton(
                    get_text("lessons.next_page", lang),
                    callback_data=f"catalog:page:{page + 1}"
                ))
            
            keyboard.append(pagination_row)
        
        # Кнопка "Назад в главное меню"
        keyboard.append([
            InlineKeyboardButton(
                get_text("navigation.main_menu", lang),
                callback_data="menu:main"
            )
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def lesson_detail(
        lesson: Dict[str, Any], 
        user_purchased: bool = False, 
        lang: str = "en"
    ) -> InlineKeyboardMarkup:
        """
        Клавиатура для детального просмотра урока.
        
        Args:
            lesson: Данные урока
            user_purchased: Купил ли пользователь урок
            lang: Код языка
            
        Returns:
            InlineKeyboardMarkup: Клавиатура детали урока
        """
        keyboard = []
        
        if user_purchased:
            # Пользователь уже купил урок
            keyboard.append([
                InlineKeyboardButton(
                    get_text("lessons.view_lesson", lang),
                    callback_data=f"lesson:open:{lesson.get('id')}"
                )
            ])
        else:
            # Пользователь еще не купил урок
            if lesson.get('is_free'):
                # Бесплатный урок
                keyboard.append([
                    InlineKeyboardButton(
                        get_text("lessons.view_lesson", lang),
                        callback_data=f"lesson:open:{lesson.get('id')}"
                    )
                ])
            else:
                # Платный урок
                price_text = get_text("lessons.buy_button", lang, price=f"{lesson.get('price', 0)} ⭐")
                keyboard.append([
                    InlineKeyboardButton(
                        price_text,
                        callback_data=f"payment:start:{lesson.get('id')}"
                    )
                ])
        
        # Кнопки навигации
        keyboard.append([
            InlineKeyboardButton(
                get_text("navigation.back", lang),
                callback_data="menu:browse_lessons"
            ),
            InlineKeyboardButton(
                get_text("navigation.main_menu", lang),
                callback_data="menu:main"
            )
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def my_lessons(
        lessons: List[Dict[str, Any]], 
        page: int = 1, 
        total_pages: int = 1,
        lang: str = "en"
    ) -> InlineKeyboardMarkup:
        """
        Клавиатура "Мои уроки".
        
        Args:
            lessons: Купленные уроки пользователя
            page: Текущая страница
            total_pages: Общее количество страниц
            lang: Код языка
            
        Returns:
            InlineKeyboardMarkup: Клавиатура "Мои уроки"
        """
        keyboard = []
        
        # Кнопки уроков
        for lesson in lessons:
            keyboard.append([
                InlineKeyboardButton(
                    f"📖 {lesson.get('title', '')}",
                    callback_data=f"lesson:open:{lesson.get('id')}"
                )
            ])
        
        # Пагинация (если нужна)
        if total_pages > 1:
            pagination_row = []
            
            if page > 1:
                pagination_row.append(InlineKeyboardButton(
                    get_text("lessons.prev_page", lang),
                    callback_data=f"my_lessons:page:{page - 1}"
                ))
            
            pagination_row.append(InlineKeyboardButton(
                get_text("lessons.page_info", lang, current=page, total=total_pages),
                callback_data="page_info"
            ))
            
            if page < total_pages:
                pagination_row.append(InlineKeyboardButton(
                    get_text("lessons.next_page", lang),
                    callback_data=f"my_lessons:page:{page + 1}"
                ))
            
            keyboard.append(pagination_row)
        
        # Кнопки навигации
        keyboard.append([
            InlineKeyboardButton(
                get_text("main_menu.browse_lessons", lang),
                callback_data="menu:browse_lessons"
            )
        ])
        
        keyboard.append([
            InlineKeyboardButton(
                get_text("navigation.main_menu", lang),
                callback_data="menu:main"
            )
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def language_selection(supported_languages: List[Dict[str, str]], current_lang: str = "en") -> InlineKeyboardMarkup:
        """
        Клавиатура выбора языка.
        
        Args:
            supported_languages: Список поддерживаемых языков
            current_lang: Текущий язык пользователя
            
        Returns:
            InlineKeyboardMarkup: Клавиатура выбора языка
        """
        keyboard = []
        
        for lang_info in supported_languages:
            lang_code = lang_info.get('code')
            lang_name = lang_info.get('name')
            
            # Отмечаем текущий язык
            if lang_code == current_lang:
                lang_name = f"✅ {lang_name}"
            
            keyboard.append([
                InlineKeyboardButton(
                    lang_name,
                    callback_data=f"language:set:{lang_code}"
                )
            ])
        
        # Кнопка назад
        keyboard.append([
            InlineKeyboardButton(
                get_text("navigation.back", current_lang),
                callback_data="menu:main"
            )
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def payment_confirmation(
        lesson: Dict[str, Any], 
        final_price: int, 
        promo_info: Optional[Dict[str, Any]] = None,
        lang: str = "en"
    ) -> InlineKeyboardMarkup:
        """
        Клавиатура подтверждения платежа.
        
        Args:
            lesson: Данные урока
            final_price: Финальная цена
            promo_info: Информация о промокоде
            lang: Код языка
            
        Returns:
            InlineKeyboardMarkup: Клавиатура подтверждения
        """
        keyboard = [
            [
                InlineKeyboardButton(
                    get_text("payments.confirm_button", lang),
                    callback_data=f"payment:confirm:{lesson.get('id')}:{final_price}"
                )
            ],
            [
                InlineKeyboardButton(
                    get_text("payments.cancel_button", lang),
                    callback_data=f"lesson:view:{lesson.get('id')}"
                )
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def promo_code_input(lesson_id: int, lang: str = "en") -> InlineKeyboardMarkup:
        """
        Клавиатура для ввода промокода.
        
        Args:
            lesson_id: ID урока
            lang: Код языка
            
        Returns:
            InlineKeyboardMarkup: Клавиатура ввода промокода
        """
        keyboard = [
            [
                InlineKeyboardButton(
                    get_text("payments.skip_promo", lang),
                    callback_data=f"payment:skip_promo:{lesson_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    get_text("navigation.cancel", lang),
                    callback_data=f"lesson:view:{lesson_id}"
                )
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def support_menu(lang: str = "en") -> InlineKeyboardMarkup:
        """
        Меню поддержки.
        
        Args:
            lang: Код языка
            
        Returns:
            InlineKeyboardMarkup: Клавиатура поддержки
        """
        keyboard = [
            [
                InlineKeyboardButton(
                    get_text("support.send_message", lang),
                    callback_data="support:send_message"
                )
            ],
            [
                InlineKeyboardButton(
                    get_text("support.faq", lang),
                    callback_data="support:faq"
                )
            ],
            [
                InlineKeyboardButton(
                    get_text("navigation.main_menu", lang),
                    callback_data="menu:main"
                )
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back_to_main(lang: str = "en") -> InlineKeyboardMarkup:
        """
        Простая кнопка "Назад в главное меню".
        
        Args:
            lang: Код языка
            
        Returns:
            InlineKeyboardMarkup: Клавиатура с кнопкой назад
        """
        keyboard = [
            [
                InlineKeyboardButton(
                    get_text("navigation.main_menu", lang),
                    callback_data="menu:main"
                )
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def admin_panel(lang: str = "en") -> InlineKeyboardMarkup:
        """
        Панель администратора (если пользователь админ).
        
        Args:
            lang: Код языка
            
        Returns:
            InlineKeyboardMarkup: Клавиатура админ-панели
        """
        keyboard = [
            [
                InlineKeyboardButton(
                    get_text("admin.stats", lang),
                    callback_data="admin:stats"
                ),
                InlineKeyboardButton(
                    get_text("admin.users", lang),
                    callback_data="admin:users"
                )
            ],
            [
                InlineKeyboardButton(
                    get_text("admin.lessons", lang),
                    callback_data="admin:lessons"
                ),
                InlineKeyboardButton(
                    get_text("admin.broadcast", lang),
                    callback_data="admin:broadcast"
                )
            ],
            [
                InlineKeyboardButton(
                    get_text("navigation.main_menu", lang),
                    callback_data="menu:main"
                )
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def inline_query_result(lesson: Dict[str, Any], lang: str = "en") -> str:
        """
        Генерировать callback_data для inline запросов.
        
        Args:
            lesson: Данные урока
            lang: Код языка
            
        Returns:
            str: Callback data для урока
        """
        return f"lesson:view:{lesson.get('id')}"


# Удобные функции для быстрого создания клавиатур
def main_menu_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    """Быстрое создание главного меню."""
    return KeyboardBuilder.main_menu(lang)


def back_button(lang: str = "en") -> InlineKeyboardMarkup:
    """Быстрое создание кнопки назад."""
    return KeyboardBuilder.back_to_main(lang)