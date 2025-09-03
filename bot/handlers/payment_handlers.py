"""
Обработчики платежей с Telegram Stars.
Создание инвойсов, обработка платежей, применение промокодов.
"""

import logging
import uuid
from typing import Dict, Any, Optional
from telegram import Update, LabeledPrice
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.config import settings
from bot.utils.api_client import BackendAPI
from bot.utils.i18n import get_user_text, get_user_language, i18n
from bot.utils.state_manager import StateManager
from bot.states.user_states import BotState
from bot.keyboards.main_keyboards import KeyboardBuilder


logger = logging.getLogger(__name__)


class PaymentHandlers:
    """Обработчики платежей."""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.api_client = BackendAPI.get_client()
    
    async def start_payment_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Начать процесс покупки урока.
        """
        query = update.callback_query
        user_id = update.effective_user.id
        
        if not query or not query.data:
            return
        
        await query.answer()
        
        try:
            # Парсинг коллбэка: "payment:start:lesson_id"
            action_parts = query.data.split(':')
            if len(action_parts) != 3:
                return
            
            lesson_id = int(action_parts[2])
            
            # Получить данные урока
            lesson = await self.api_client.get_lesson_public(lesson_id)
            
            # Проверить, что урок не бесплатный
            if lesson.get('is_free'):
                error_text = await get_user_text(user_id, "errors.free_lesson_purchase")
                await query.edit_message_text(error_text)
                return
            
            # Проверить, что пользователь еще не купил урок
            user_purchased = await self.api_client.check_user_has_lesson(user_id, lesson_id)
            if user_purchased:
                already_text = await get_user_text(user_id, "lessons.already_purchased")
                await query.edit_message_text(already_text)
                return
            
            # Установить состояние платежа
            self.state_manager.set_user_state(
                user_id,
                BotState.PAYMENT_PROCESS,
                {
                    'lesson_id': lesson_id,
                    'original_price': lesson.get('price', 0),
                    'final_price': lesson.get('price', 0),
                    'promo_code': None
                }
            )
            
            # Предложить ввести промокод
            await self._show_promo_code_input(query, user_id, lesson)
            
        except Exception as e:
            logger.error(f"Error in start_payment_callback: {e}")
            await self._send_error_message(query, user_id)
    
    async def _show_promo_code_input(self, query, user_id: int, lesson: Dict[str, Any]):
        """Показать интерфейс для ввода промокода."""
        user_lang = await get_user_language(user_id)
        
        promo_text = await get_user_text(user_id, "payments.promo_code_prompt")
        lesson_info = await get_user_text(
            user_id,
            "payments.purchase_details",
            title=lesson.get('title', ''),
            price=i18n.format_price(lesson.get('price', 0), user_lang),
            promo="None"
        )
        
        full_text = f"{lesson_info}\n\n{promo_text}"
        
        keyboard = KeyboardBuilder.promo_code_input(lesson.get('id'), user_lang)
        
        await query.edit_message_text(
            full_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        
        # Установить состояние ожидания промокода
        self.state_manager.set_user_state(user_id, BotState.PROMO_CODE_INPUT)
    
    async def skip_promo_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Пропустить ввод промокода и перейти к оплате.
        """
        query = update.callback_query
        user_id = update.effective_user.id
        
        if not query or not query.data:
            return
        
        await query.answer()
        
        try:
            # Парсинг коллбэка: "payment:skip_promo:lesson_id"
            action_parts = query.data.split(':')
            if len(action_parts) != 3:
                return
            
            lesson_id = int(action_parts[2])
            
            # Получить данные урока
            lesson = await self.api_client.get_lesson_public(lesson_id)
            
            # Создать инвойс без промокода
            await self._create_invoice(query, user_id, lesson)
            
        except Exception as e:
            logger.error(f"Error in skip_promo_callback: {e}")
            await self._send_error_message(query, user_id)
    
    async def promo_code_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработать введенный промокод.
        """
        user_id = update.effective_user.id
        message = update.message
        
        if not message or not message.text:
            return
        
        try:
            # Проверить, что пользователь в правильном состоянии
            current_state, state_data = self.state_manager.get_user_state(user_id)
            
            if current_state != BotState.PROMO_CODE_INPUT:
                return
            
            promo_code = message.text.strip()
            lesson_id = state_data.get('lesson_id')
            
            if not lesson_id:
                error_text = await get_user_text(user_id, "errors.general")
                await message.reply_text(error_text)
                return
            
            # Получить данные урока
            lesson = await self.api_client.get_lesson_public(lesson_id)
            
            # Проверить промокод
            try:
                promo_info = await self.api_client.check_promo_code(
                    code=promo_code,
                    item_type='lesson',
                    item_id=lesson_id
                )
                
                # Промокод действителен
                discount_percent = promo_info.get('discount_percent', 0)
                original_price = lesson.get('price', 0)
                final_price = max(1, original_price - (original_price * discount_percent // 100))
                
                # Обновить состояние с промокодом
                self.state_manager.update_user_data(user_id, 'promo_code', promo_code)
                self.state_manager.update_user_data(user_id, 'final_price', final_price)
                self.state_manager.update_user_data(user_id, 'discount_percent', discount_percent)
                
                # Показать примененный промокод
                user_lang = await get_user_language(user_id)
                applied_text = await get_user_text(
                    user_id,
                    "payments.promo_code_applied",
                    discount=discount_percent,
                    price=i18n.format_price(final_price, user_lang)
                )
                
                await message.reply_text(applied_text)
                
                # Создать инвойс с учетом промокода
                await self._create_invoice_from_message(message, user_id, lesson, final_price, promo_code)
                
            except Exception as promo_error:
                # Промокод недействителен
                logger.info(f"Invalid promo code '{promo_code}' for user {user_id}: {promo_error}")
                
                invalid_text = await get_user_text(user_id, "payments.promo_code_invalid")
                await message.reply_text(invalid_text)
                
                # Создать инвойс без промокода
                await self._create_invoice_from_message(message, user_id, lesson)
            
        except Exception as e:
            logger.error(f"Error in promo_code_message_handler: {e}")
            error_text = await get_user_text(user_id, "errors.general")
            await message.reply_text(error_text)
    
    async def _create_invoice(self, query, user_id: int, lesson: Dict[str, Any], 
                            final_price: Optional[int] = None, promo_code: Optional[str] = None):
        """Создать инвойс для платежа."""
        try:
            price = final_price or lesson.get('price', 0)
            user_lang = await get_user_language(user_id)
            
            # Создать уникальный payload для платежа
            payment_payload = f"lesson_{lesson.get('id')}_{user_id}_{uuid.uuid4().hex[:8]}"
            
            # Сохранить информацию о платеже в состоянии
            self.state_manager.update_user_data(user_id, 'payment_payload', payment_payload)
            
            # Создать инвойс
            await query.message.reply_invoice(
                title=lesson.get('title', 'Lesson'),
                description=lesson.get('description', '')[:255],  # Ограничение Telegram
                payload=payment_payload,
                provider_token='',  # Для Telegram Stars используется пустой токен
                currency='XTR',  # Telegram Stars
                prices=[LabeledPrice(label='Price', amount=price)],
                start_parameter=f'lesson_{lesson.get("id")}',
                photo_url=None,  # TODO: Добавить превью урока
                need_name=False,
                need_phone_number=False,
                need_email=False,
                need_shipping_address=False,
                send_phone_number_to_provider=False,
                send_email_to_provider=False,
                is_flexible=False
            )
            
            # Установить состояние ожидания платежа
            self.state_manager.set_user_state(user_id, BotState.PAYMENT_CONFIRMATION)
            
            logger.info(f"Invoice created for user {user_id}, lesson {lesson.get('id')}, price {price}")
            
        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            error_text = await get_user_text(user_id, "payments.failed")
            await query.edit_message_text(error_text)
    
    async def _create_invoice_from_message(self, message, user_id: int, lesson: Dict[str, Any],
                                         final_price: Optional[int] = None, promo_code: Optional[str] = None):
        """Создать инвойс из обычного сообщения (не callback)."""
        try:
            price = final_price or lesson.get('price', 0)
            user_lang = await get_user_language(user_id)
            
            # Создать уникальный payload для платежа
            payment_payload = f"lesson_{lesson.get('id')}_{user_id}_{uuid.uuid4().hex[:8]}"
            
            # Сохранить информацию о платеже в состоянии
            self.state_manager.update_user_data(user_id, 'payment_payload', payment_payload)
            
            # Создать инвойс
            await message.reply_invoice(
                title=lesson.get('title', 'Lesson'),
                description=lesson.get('description', '')[:255],
                payload=payment_payload,
                provider_token='',
                currency='XTR',
                prices=[LabeledPrice(label='Price', amount=price)],
                start_parameter=f'lesson_{lesson.get("id")}',
                need_name=False,
                need_phone_number=False,
                need_email=False,
                need_shipping_address=False,
                send_phone_number_to_provider=False,
                send_email_to_provider=False,
                is_flexible=False
            )
            
            # Установить состояние ожидания платежа
            self.state_manager.set_user_state(user_id, BotState.PAYMENT_CONFIRMATION)
            
        except Exception as e:
            logger.error(f"Error creating invoice from message: {e}")
    
    async def pre_checkout_query_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработчик pre-checkout запроса.
        """
        pre_checkout_query = update.pre_checkout_query
        user_id = update.effective_user.id
        
        try:
            # Проверить payload
            payload = pre_checkout_query.invoice_payload
            current_state, state_data = self.state_manager.get_user_state(user_id)
            expected_payload = state_data.get('payment_payload')
            
            if payload != expected_payload:
                logger.warning(f"Invalid payment payload for user {user_id}: {payload}")
                await pre_checkout_query.answer(ok=False, error_message="Invalid payment")
                return
            
            # Проверить, что урок все еще доступен для покупки
            lesson_id = state_data.get('lesson_id')
            if lesson_id:
                lesson = await self.api_client.get_lesson_public(lesson_id)
                if not lesson or not lesson.get('is_active', True):
                    await pre_checkout_query.answer(ok=False, error_message="Lesson is no longer available")
                    return
            
            # Подтвердить платеж
            await pre_checkout_query.answer(ok=True)
            
            logger.info(f"Pre-checkout approved for user {user_id}, payload {payload}")
            
        except Exception as e:
            logger.error(f"Error in pre_checkout_query_handler: {e}")
            await pre_checkout_query.answer(ok=False, error_message="Payment processing error")
    
    async def successful_payment_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработчик успешного платежа.
        """
        message = update.message
        user_id = update.effective_user.id
        payment = message.successful_payment
        
        try:
            # Получить информацию о платеже
            telegram_payment_charge_id = payment.telegram_payment_charge_id
            payload = payment.invoice_payload
            total_amount = payment.total_amount
            
            # Получить данные из состояния
            current_state, state_data = self.state_manager.get_user_state(user_id)
            lesson_id = state_data.get('lesson_id')
            promo_code = state_data.get('promo_code')
            
            if not lesson_id:
                logger.error(f"No lesson_id in state for successful payment from user {user_id}")
                return
            
            # Создать запись о покупке в API
            purchase_data = await self.api_client.create_purchase(
                user_id=user_id,
                lesson_id=lesson_id,
                payment_id=telegram_payment_charge_id,
                amount=total_amount,
                promo_code=promo_code
            )
            
            # Обновить статус покупки на завершенную
            await self.api_client.update_purchase(
                purchase_data.get('id'),
                status='completed'
            )
            
            # Отправить подтверждение пользователю
            user_lang = await get_user_language(user_id)
            success_text = await get_user_text(user_id, "payments.success")
            keyboard = KeyboardBuilder.main_menu(user_lang)
            
            await message.reply_text(
                success_text,
                reply_markup=keyboard
            )
            
            # Сбросить состояние
            self.state_manager.set_user_state(user_id, BotState.MAIN_MENU)
            
            logger.info(f"Payment completed for user {user_id}, lesson {lesson_id}, charge_id {telegram_payment_charge_id}")
            
            # Уведомить администратора (если настроено)
            if settings.admin_chat_id:
                admin_notification = (
                    f"💰 New purchase!\n"
                    f"User: {user_id}\n"
                    f"Lesson ID: {lesson_id}\n"
                    f"Amount: {total_amount} ⭐\n"
                    f"Payment ID: {telegram_payment_charge_id}"
                )
                
                try:
                    await context.bot.send_message(
                        chat_id=settings.admin_chat_id,
                        text=admin_notification
                    )
                except Exception as admin_error:
                    logger.error(f"Error sending admin notification: {admin_error}")
            
        except Exception as e:
            logger.error(f"Error in successful_payment_handler: {e}")
            
            # Уведомить пользователя об ошибке
            error_text = await get_user_text(user_id, "payments.failed")
            await message.reply_text(error_text)
            
            # Уведомить администратора об ошибке платежа
            if settings.error_log_chat_id:
                error_notification = (
                    f"❌ Payment processing error!\n"
                    f"User: {user_id}\n"
                    f"Payment ID: {payment.telegram_payment_charge_id}\n"
                    f"Error: {str(e)}"
                )
                
                try:
                    await context.bot.send_message(
                        chat_id=settings.error_log_chat_id,
                        text=error_notification
                    )
                except Exception:
                    pass
    
    async def _send_error_message(self, query, user_id: int):
        """Отправить сообщение об ошибке."""
        try:
            error_text = await get_user_text(user_id, "errors.payment_error")
            keyboard = KeyboardBuilder.back_to_main(await get_user_language(user_id))
            
            await query.edit_message_text(
                error_text,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error sending error message: {e}")


# Фабрика для создания обработчиков платежей
def create_payment_handlers(state_manager: StateManager) -> PaymentHandlers:
    """Создать обработчики платежей."""
    return PaymentHandlers(state_manager)