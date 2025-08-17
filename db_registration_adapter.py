"""
Адаптер для интеграции системы регистрации с PostgreSQL
"""
import logging
from typing import Dict, Optional, Any
from datetime import datetime
from user_registration import RegistrationStep, UserData
from database import (
    get_user_by_telegram_id, create_or_update_user, 
    log_user_activity, User
)

logger = logging.getLogger(__name__)

class DatabaseRegistrationManager:
    """Менеджер регистрации с поддержкой PostgreSQL"""
    
    def __init__(self):
        # Кэш для активных состояний регистрации (in-memory для быстрого доступа)
        self.registration_states: Dict[int, RegistrationStep] = {}
        # Временный кэш пользователей для сессии
        self.user_cache: Dict[int, UserData] = {}
    
    async def get_user(self, telegram_user_id: int) -> Optional[UserData]:
        """Получить данные пользователя из базы данных"""
        try:
            # Сначала проверяем кэш
            if telegram_user_id in self.user_cache:
                return self.user_cache[telegram_user_id]
            
            # Загружаем из базы данных
            db_user = await get_user_by_telegram_id(telegram_user_id)
            if db_user:
                # Конвертируем в UserData для совместимости
                user_data = UserData(telegram_user_id)
                user_dict = db_user.to_dict()
                
                user_data.personal = user_dict['personal']
                user_data.current = user_dict['current']
                user_data.preferences = user_dict['preferences']
                user_data.metadata = user_dict['metadata']
                
                # Кэшируем
                self.user_cache[telegram_user_id] = user_data
                return user_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user {telegram_user_id}: {e}")
            return None
    
    async def get_or_create_user(self, telegram_user_id: int) -> UserData:
        """Получить или создать пользователя"""
        user = await self.get_user(telegram_user_id)
        if not user:
            user = UserData(telegram_user_id)
            self.user_cache[telegram_user_id] = user
            self.registration_states[telegram_user_id] = RegistrationStep.NOT_STARTED
        return user
    
    def get_registration_step(self, telegram_user_id: int) -> RegistrationStep:
        """Получить текущий этап регистрации"""
        # Сначала проверяем in-memory кэш
        if telegram_user_id in self.registration_states:
            return self.registration_states[telegram_user_id]
        
        # Проверяем кэш пользователей
        if telegram_user_id in self.user_cache:
            user = self.user_cache[telegram_user_id]
            step_str = user.metadata.get('registration_step', 'not_started')
            try:
                step = RegistrationStep(step_str)
                self.registration_states[telegram_user_id] = step
                return step
            except ValueError:
                pass
        
        return RegistrationStep.NOT_STARTED
    
    def set_registration_step(self, telegram_user_id: int, step: RegistrationStep):
        """Установить этап регистрации"""
        self.registration_states[telegram_user_id] = step
        
        # Обновляем кэш пользователя
        if telegram_user_id in self.user_cache:
            self.user_cache[telegram_user_id].metadata['registration_step'] = step.value
    
    def is_registration_complete(self, telegram_user_id: int) -> bool:
        """Проверить завершена ли регистрация"""
        return self.get_registration_step(telegram_user_id) == RegistrationStep.COMPLETED
    
    async def start_registration(self, telegram_user_id: int, user_telegram_data: Dict[str, Any]) -> str:
        """Начать процесс регистрации"""
        try:
            user = await self.get_or_create_user(telegram_user_id)
            
            # Сохраняем базовые данные из Telegram
            user.metadata.update({
                'telegram_username': user_telegram_data.get('username'),
                'telegram_first_name': user_telegram_data.get('first_name'),
                'telegram_last_name': user_telegram_data.get('last_name')
            })
            
            self.set_registration_step(telegram_user_id, RegistrationStep.NAME)
            
            # Логируем начало регистрации
            await log_user_activity(
                telegram_user_id, 
                'registration_start',
                {'telegram_data': user_telegram_data}
            )
            
            return """🌟 Добро пожаловать в DailyBot!

Для создания персональных астрологических прогнозов мне нужно узнать о вас немного информации.

📝 Процесс займет 2-3 минуты и включает:
• Ваше имя
• Дата и время рождения
• Место рождения
• Текущее местоположение
• Время для получения прогнозов

Все данные используются только для астрологических расчетов и надежно защищены.

Как вас зовут? (Можете написать любое удобное имя)"""
            
        except Exception as e:
            logger.error(f"Error starting registration for {telegram_user_id}: {e}")
            return "❌ Произошла ошибка при начале регистрации. Попробуйте позже."
    
    async def process_registration_step(self, telegram_user_id: int, message_text: str, location_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Обработать этап регистрации"""
        try:
            current_step = self.get_registration_step(telegram_user_id)
            user = await self.get_user(telegram_user_id)
            
            if not user:
                return {'error': 'User not found', 'restart': True}
            
            # Импортируем методы из оригинального менеджера
            from user_registration import registration_manager
            
            # Используем оригинальную логику обработки
            result = registration_manager.process_registration_step(telegram_user_id, message_text, location_data)
            
            # Если шаг успешно обработан, сохраняем в базу данных
            if result.get('success'):
                await self._save_user_to_database(telegram_user_id, user)
                
                # Логируем шаг регистрации
                await log_user_activity(
                    telegram_user_id,
                    'registration_step',
                    {
                        'step': current_step.value,
                        'message': message_text[:100] if message_text else None,
                        'has_location': location_data is not None
                    }
                )
                
                # Если регистрация завершена, финализируем
                if result.get('completed'):
                    await self._finalize_registration(telegram_user_id, user)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing registration step for {telegram_user_id}: {e}")
            return {'error': f'Произошла ошибка: {str(e)}', 'retry': True}
    
    async def _save_user_to_database(self, telegram_user_id: int, user: UserData):
        """Сохранить данные пользователя в базу данных"""
        try:
            user_dict = user.to_dict()
            user_dict['telegram_username'] = user.metadata.get('telegram_username')
            user_dict['telegram_first_name'] = user.metadata.get('telegram_first_name')
            user_dict['telegram_last_name'] = user.metadata.get('telegram_last_name')
            
            await create_or_update_user(user_dict)
            logger.info(f"User {telegram_user_id} saved to database")
            
        except Exception as e:
            logger.error(f"Error saving user {telegram_user_id} to database: {e}")
            raise
    
    async def _finalize_registration(self, telegram_user_id: int, user: UserData):
        """Финализировать регистрацию пользователя"""
        try:
            # Обновляем статус завершения
            user.metadata['registration_complete'] = True
            user.metadata['completed_at'] = datetime.now().isoformat()
            
            # Сохраняем финальное состояние
            await self._save_user_to_database(telegram_user_id, user)
            
            # Логируем завершение регистрации
            await log_user_activity(
                telegram_user_id,
                'registration_complete',
                {'completed_at': user.metadata['completed_at']}
            )
            
            # Очищаем кэш состояния регистрации
            self.registration_states[telegram_user_id] = RegistrationStep.COMPLETED
            
            logger.info(f"Registration completed for user {telegram_user_id}")
            
        except Exception as e:
            logger.error(f"Error finalizing registration for {telegram_user_id}: {e}")
            raise
    
    def _generate_registration_summary(self, user: UserData) -> str:
        """Сгенерировать сводку регистрации"""
        # Используем оригинальную логику
        from user_registration import registration_manager
        return registration_manager._generate_registration_summary(user)
    
    async def get_users_for_forecast(self, forecast_time: str) -> list:
        """Получить пользователей для отправки прогнозов в указанное время"""
        try:
            # Это будет использоваться для планировщика уведомлений
            # Пока возвращаем пустой список, реализуем позже
            return []
        except Exception as e:
            logger.error(f"Error getting users for forecast at {forecast_time}: {e}")
            return []
    
    async def update_user_last_activity(self, telegram_user_id: int):
        """Обновить время последней активности пользователя"""
        try:
            user = await get_user_by_telegram_id(telegram_user_id)
            if user:
                from database import db_manager
                async with db_manager.get_session() as session:
                    user.last_active = datetime.utcnow()
                    await session.commit()
        except Exception as e:
            logger.error(f"Error updating last activity for {telegram_user_id}: {e}")

# Глобальный экземпляр менеджера с поддержкой базы данных
db_registration_manager = DatabaseRegistrationManager()
