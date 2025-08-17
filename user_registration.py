"""
Система регистрации пользователей для астрологического бота
"""
import logging
from datetime import datetime
from typing import Dict, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)

class RegistrationStep(Enum):
    """Этапы регистрации пользователя"""
    NOT_STARTED = "not_started"
    NAME = "name"
    BIRTH_DATE = "birth_date"
    BIRTH_TIME = "birth_time"
    BIRTH_PLACE = "birth_place"
    CURRENT_LOCATION = "current_location"
    FORECAST_TIME = "forecast_time"
    COMPLETED = "completed"

class UserData:
    """Класс для хранения данных пользователя"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.personal = {}
        self.current = {}
        self.preferences = {}
        self.metadata = {
            'registered_at': datetime.now().isoformat(),
            'registration_step': RegistrationStep.NOT_STARTED.value,
            'registration_complete': False
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь для сохранения"""
        return {
            'user_id': self.user_id,
            'personal': self.personal,
            'current': self.current,
            'preferences': self.preferences,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserData':
        """Создать объект из словаря"""
        user = cls(data['user_id'])
        user.personal = data.get('personal', {})
        user.current = data.get('current', {})
        user.preferences = data.get('preferences', {})
        user.metadata = data.get('metadata', {})
        return user

class RegistrationManager:
    """Менеджер процесса регистрации"""
    
    def __init__(self):
        # Временное хранилище (в будущем заменим на БД)
        self.users: Dict[int, UserData] = {}
        self.registration_states: Dict[int, RegistrationStep] = {}
    
    def get_user(self, user_id: int) -> Optional[UserData]:
        """Получить данные пользователя"""
        return self.users.get(user_id)
    
    def get_or_create_user(self, user_id: int) -> UserData:
        """Получить или создать пользователя"""
        if user_id not in self.users:
            self.users[user_id] = UserData(user_id)
            self.registration_states[user_id] = RegistrationStep.NOT_STARTED
        return self.users[user_id]
    
    def get_registration_step(self, user_id: int) -> RegistrationStep:
        """Получить текущий этап регистрации"""
        return self.registration_states.get(user_id, RegistrationStep.NOT_STARTED)
    
    def set_registration_step(self, user_id: int, step: RegistrationStep):
        """Установить этап регистрации"""
        self.registration_states[user_id] = step
        if user_id in self.users:
            self.users[user_id].metadata['registration_step'] = step.value
    
    def is_registration_complete(self, user_id: int) -> bool:
        """Проверить завершена ли регистрация"""
        return self.get_registration_step(user_id) == RegistrationStep.COMPLETED
    
    def start_registration(self, user_id: int, user_telegram_data: Dict[str, Any]) -> str:
        """Начать процесс регистрации"""
        user = self.get_or_create_user(user_id)
        
        # Сохраняем базовые данные из Telegram
        user.metadata.update({
            'telegram_username': user_telegram_data.get('username'),
            'telegram_first_name': user_telegram_data.get('first_name'),
            'telegram_last_name': user_telegram_data.get('last_name')
        })
        
        self.set_registration_step(user_id, RegistrationStep.NAME)
        
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
    
    def process_registration_step(self, user_id: int, message_text: str, location_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Обработать этап регистрации"""
        current_step = self.get_registration_step(user_id)
        user = self.get_user(user_id)
        
        if not user:
            return {'error': 'User not found', 'restart': True}
        
        try:
            if current_step == RegistrationStep.NAME:
                return self._process_name(user_id, user, message_text)
            elif current_step == RegistrationStep.BIRTH_DATE:
                return self._process_birth_date(user_id, user, message_text)
            elif current_step == RegistrationStep.BIRTH_TIME:
                return self._process_birth_time(user_id, user, message_text)
            elif current_step == RegistrationStep.BIRTH_PLACE:
                return self._process_birth_place(user_id, user, message_text)
            elif current_step == RegistrationStep.CURRENT_LOCATION:
                return self._process_current_location(user_id, user, message_text, location_data)
            elif current_step == RegistrationStep.FORECAST_TIME:
                return self._process_forecast_time(user_id, user, message_text)
            else:
                return {'error': 'Unknown registration step'}
                
        except Exception as e:
            logger.error(f"Error processing registration step {current_step} for user {user_id}: {e}")
            return {'error': f'Произошла ошибка: {str(e)}', 'retry': True}
    
    def _process_name(self, user_id: int, user: UserData, name: str) -> Dict[str, Any]:
        """Обработать ввод имени"""
        if not name or len(name.strip()) < 1:
            return {'error': 'Пожалуйста, введите ваше имя', 'retry': True}
        
        user.personal['name'] = name.strip()
        self.set_registration_step(user_id, RegistrationStep.BIRTH_DATE)
        
        return {
            'success': True,
            'message': f"""Приятно познакомиться, {name}! 😊

📅 Теперь укажите дату вашего рождения в формате ДД.ММ.ГГГГ

Например: 15.03.1990"""
        }
    
    def _process_birth_date(self, user_id: int, user: UserData, date_text: str) -> Dict[str, Any]:
        """Обработать ввод даты рождения"""
        try:
            # Попробуем разные форматы
            date_formats = ['%d.%m.%Y', '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']
            birth_date = None
            
            for date_format in date_formats:
                try:
                    birth_date = datetime.strptime(date_text.strip(), date_format)
                    break
                except ValueError:
                    continue
            
            if not birth_date:
                return {
                    'error': 'Неверный формат даты. Используйте ДД.ММ.ГГГГ (например: 15.03.1990)',
                    'retry': True
                }
            
            # Проверяем разумность даты
            if birth_date.year < 1900 or birth_date > datetime.now():
                return {
                    'error': 'Пожалуйста, укажите корректную дату рождения',
                    'retry': True
                }
            
            user.personal['birth_date'] = birth_date.strftime('%Y-%m-%d')
            self.set_registration_step(user_id, RegistrationStep.BIRTH_TIME)
            
            return {
                'success': True,
                'message': f"""Отлично! Дата рождения: {birth_date.strftime('%d.%m.%Y')}

⏰ Теперь укажите время рождения в формате ЧЧ:ММ

Например: 14:30

Если не знаете точное время, напишите "не знаю" - мы используем полдень для расчетов."""
            }
            
        except Exception as e:
            return {
                'error': 'Ошибка при обработке даты. Попробуйте формат ДД.ММ.ГГГГ',
                'retry': True
            }
    
    def _process_birth_time(self, user_id: int, user: UserData, time_text: str) -> Dict[str, Any]:
        """Обработать ввод времени рождения"""
        time_text = time_text.strip().lower()
        
        if time_text in ['не знаю', 'незнаю', 'нет', 'неизвестно']:
            user.personal['birth_time'] = '12:00'
            user.personal['birth_time_unknown'] = True
            time_display = '12:00 (приблизительно)'
        else:
            try:
                # Попробуем разные форматы времени
                time_formats = ['%H:%M', '%H.%M', '%H-%M']
                birth_time = None
                
                for time_format in time_formats:
                    try:
                        birth_time = datetime.strptime(time_text, time_format)
                        break
                    except ValueError:
                        continue
                
                if not birth_time:
                    return {
                        'error': 'Неверный формат времени. Используйте ЧЧ:ММ (например: 14:30) или напишите "не знаю"',
                        'retry': True
                    }
                
                user.personal['birth_time'] = birth_time.strftime('%H:%M')
                user.personal['birth_time_unknown'] = False
                time_display = birth_time.strftime('%H:%M')
                
            except Exception:
                return {
                    'error': 'Ошибка при обработке времени. Используйте формат ЧЧ:ММ или напишите "не знаю"',
                    'retry': True
                }
        
        self.set_registration_step(user_id, RegistrationStep.BIRTH_PLACE)
        
        return {
            'success': True,
            'message': f"""Время рождения: {time_display}

🏙️ Теперь укажите город или место рождения

Например: Москва, Санкт-Петербург, Екатеринбург

Это нужно для точных астрологических расчетов натальной карты."""
        }
    
    def _process_birth_place(self, user_id: int, user: UserData, place_text: str) -> Dict[str, Any]:
        """Обработать ввод места рождения"""
        if not place_text or len(place_text.strip()) < 2:
            return {'error': 'Пожалуйста, укажите место рождения', 'retry': True}
        
        user.personal['birth_place'] = place_text.strip()
        self.set_registration_step(user_id, RegistrationStep.CURRENT_LOCATION)
        
        return {
            'success': True,
            'message': f"""Место рождения: {place_text}

📍 Теперь укажите где вы живете сейчас:

🌍 Поделиться геолокацией (рекомендуется)
🏙️ Или написать название города

Это нужно для актуальных прогнозов с учетом времени восхода и заката в вашем регионе.""",
            'request_location': True
        }
    
    def _process_current_location(self, user_id: int, user: UserData, message_text: str, location_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Обработать текущее местоположение"""
        if location_data:
            # Получена геолокация
            user.current['coordinates'] = [location_data['latitude'], location_data['longitude']]
            user.current['location_type'] = 'coordinates'
            location_display = f"📍 Координаты: {location_data['latitude']:.4f}, {location_data['longitude']:.4f}"
        else:
            # Получен текст с названием города
            if not message_text or len(message_text.strip()) < 2:
                return {'error': 'Пожалуйста, укажите город или поделитесь геолокацией', 'retry': True}
            
            user.current['location'] = message_text.strip()
            user.current['location_type'] = 'city'
            location_display = f"🏙️ Город: {message_text}"
        
        self.set_registration_step(user_id, RegistrationStep.FORECAST_TIME)
        
        return {
            'success': True,
            'message': f"""Текущее местоположение: {location_display}

⏰ Последний вопрос! В какое время присылать вам ежедневные астропрогнозы?

Укажите время в формате ЧЧ:ММ
Например: 09:00, 19:30

Рекомендуем утреннее время (8:00-10:00) для планирования дня."""
        }
    
    def _process_forecast_time(self, user_id: int, user: UserData, time_text: str) -> Dict[str, Any]:
        """Обработать время для прогнозов"""
        try:
            time_formats = ['%H:%M', '%H.%M', '%H-%M']
            forecast_time = None
            
            for time_format in time_formats:
                try:
                    forecast_time = datetime.strptime(time_text.strip(), time_format)
                    break
                except ValueError:
                    continue
            
            if not forecast_time:
                return {
                    'error': 'Неверный формат времени. Используйте ЧЧ:ММ (например: 09:00)',
                    'retry': True
                }
            
            user.preferences['forecast_time'] = forecast_time.strftime('%H:%M')
            user.preferences['frequency'] = 'daily'
            user.preferences['language'] = 'ru'
            user.preferences['astro_level'] = 'beginner'
            
            user.metadata['registration_complete'] = True
            user.metadata['completed_at'] = datetime.now().isoformat()
            
            self.set_registration_step(user_id, RegistrationStep.COMPLETED)
            
            # Формируем сводку регистрации
            summary = self._generate_registration_summary(user)
            
            return {
                'success': True,
                'completed': True,
                'message': f"""🎉 Регистрация завершена!

{summary}

✨ Сейчас я подготовлю ваш первый персональный астрологический прогноз!

Используйте команды:
/astro - Получить прогноз на сегодня
/profile - Посмотреть свои данные
/help - Справка"""
            }
            
        except Exception as e:
            return {
                'error': 'Ошибка при обработке времени. Используйте формат ЧЧ:ММ',
                'retry': True
            }
    
    def _generate_registration_summary(self, user: UserData) -> str:
        """Сгенерировать сводку регистрации"""
        name = user.personal.get('name', 'Пользователь')
        birth_date = user.personal.get('birth_date', '')
        birth_time = user.personal.get('birth_time', '')
        birth_place = user.personal.get('birth_place', '')
        forecast_time = user.preferences.get('forecast_time', '')
        
        # Форматируем дату
        if birth_date:
            try:
                date_obj = datetime.strptime(birth_date, '%Y-%m-%d')
                birth_date_formatted = date_obj.strftime('%d.%m.%Y')
            except:
                birth_date_formatted = birth_date
        else:
            birth_date_formatted = 'не указана'
        
        time_note = ""
        if user.personal.get('birth_time_unknown'):
            time_note = " (приблизительно)"
        
        location_info = ""
        if user.current.get('location_type') == 'coordinates':
            location_info = "📍 По геолокации"
        elif user.current.get('location'):
            location_info = f"🏙️ {user.current['location']}"
        
        return f"""📋 Ваши данные:
👤 Имя: {name}
📅 Дата рождения: {birth_date_formatted}
⏰ Время рождения: {birth_time}{time_note}
🏙️ Место рождения: {birth_place}
📍 Текущее местоположение: {location_info}
🔔 Время прогнозов: {forecast_time}"""

# Глобальный менеджер регистрации
registration_manager = RegistrationManager()
