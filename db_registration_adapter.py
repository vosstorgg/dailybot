"""
Адаптер для работы с базой данных - система регистрации и аналитики
"""
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Optional, Any, List
from sqlalchemy import select, update, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from database import (
    User, UserAction, UserAnalytics, ActionType, RegistrationStep,
    get_db_session, init_database
)

logger = logging.getLogger(__name__)

class DatabaseRegistrationManager:
    """Менеджер регистрации пользователей с использованием БД"""
    
    def __init__(self):
        self._db_initialized = False
    
    async def initialize(self):
        """Инициализация БД"""
        if not self._db_initialized:
            success = await init_database()
            if success:
                self._db_initialized = True
                logger.info("Database registration manager initialized")
            return success
        return True
    
    async def get_user(self, telegram_user_id: int) -> Optional[User]:
        """Получить пользователя по Telegram ID"""
        async with await get_db_session() as session:
            stmt = select(User).where(User.telegram_user_id == telegram_user_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    async def get_or_create_user(self, telegram_user_id: int, telegram_data: Dict[str, Any] = None) -> User:
        """Получить или создать пользователя"""
        user = await self.get_user(telegram_user_id)
        
        if not user:
            # Создаем нового пользователя
            user = User(
                telegram_user_id=telegram_user_id,
                telegram_username=telegram_data.get('username') if telegram_data else None,
                telegram_first_name=telegram_data.get('first_name') if telegram_data else None,
                telegram_last_name=telegram_data.get('last_name') if telegram_data else None,
                first_seen=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                registration_step=RegistrationStep.NOT_STARTED.value
            )
            
            async with await get_db_session() as session:
                session.add(user)
                await session.commit()
                await session.refresh(user)
            
            # Записываем действие первого контакта
            await self.log_user_action(
                telegram_user_id, 
                ActionType.REGISTRATION_STARTED.value,
                context={'telegram_data': telegram_data}
            )
            
            logger.info(f"Created new user: {telegram_user_id}")
        
        return user
    
    async def update_user_activity(self, telegram_user_id: int):
        """Обновить время последней активности пользователя"""
        async with await get_db_session() as session:
            stmt = (
                update(User)
                .where(User.telegram_user_id == telegram_user_id)
                .values(last_activity=datetime.utcnow())
            )
            await session.execute(stmt)
            await session.commit()
    
    async def get_registration_step(self, telegram_user_id: int) -> RegistrationStep:
        """Получить текущий этап регистрации"""
        user = await self.get_user(telegram_user_id)
        if not user:
            return RegistrationStep.NOT_STARTED
        
        try:
            return RegistrationStep(user.registration_step)
        except ValueError:
            return RegistrationStep.NOT_STARTED
    
    async def set_registration_step(self, telegram_user_id: int, step: RegistrationStep):
        """Установить этап регистрации"""
        async with await get_db_session() as session:
            stmt = (
                update(User)
                .where(User.telegram_user_id == telegram_user_id)
                .values(
                    registration_step=step.value,
                    last_activity=datetime.utcnow()
                )
            )
            await session.execute(stmt)
            await session.commit()
    
    async def is_registration_complete(self, telegram_user_id: int) -> bool:
        """Проверить завершена ли регистрация"""
        user = await self.get_user(telegram_user_id)
        return user and user.registration_complete
    
    async def start_registration(self, telegram_user_id: int, telegram_data: Dict[str, Any]) -> str:
        """Начать процесс регистрации"""
        user = await self.get_or_create_user(telegram_user_id, telegram_data)
        
        # Сбрасываем регистрацию если пользователь перерегистрируется
        async with await get_db_session() as session:
            stmt = (
                update(User)
                .where(User.telegram_user_id == telegram_user_id)
                .values(
                    registration_step=RegistrationStep.NAME.value,
                    registration_complete=False,
                    last_activity=datetime.utcnow()
                )
            )
            await session.execute(stmt)
            await session.commit()
        
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
    
    async def process_registration_step(self, telegram_user_id: int, message_text: str, location_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Обработать этап регистрации"""
        current_step = await self.get_registration_step(telegram_user_id)
        user = await self.get_user(telegram_user_id)
        
        if not user:
            return {'error': 'User not found', 'restart': True}
        
        # Обновляем активность
        await self.update_user_activity(telegram_user_id)
        
        try:
            if current_step == RegistrationStep.NAME:
                return await self._process_name(telegram_user_id, message_text)
            elif current_step == RegistrationStep.BIRTH_DATE:
                return await self._process_birth_date(telegram_user_id, message_text)
            elif current_step == RegistrationStep.BIRTH_TIME:
                return await self._process_birth_time(telegram_user_id, message_text)
            elif current_step == RegistrationStep.BIRTH_PLACE:
                return await self._process_birth_place(telegram_user_id, message_text)
            elif current_step == RegistrationStep.CURRENT_LOCATION:
                return await self._process_current_location(telegram_user_id, message_text, location_data)
            elif current_step == RegistrationStep.FORECAST_TIME:
                return await self._process_forecast_time(telegram_user_id, message_text)
            else:
                return {'error': 'Unknown registration step'}
                
        except Exception as e:
            logger.error(f"Error processing registration step {current_step} for user {telegram_user_id}: {e}")
            return {'error': f'Произошла ошибка: {str(e)}', 'retry': True}
    
    async def _process_name(self, telegram_user_id: int, name: str) -> Dict[str, Any]:
        """Обработать ввод имени"""
        if not name or len(name.strip()) < 1:
            return {'error': 'Пожалуйста, введите ваше имя', 'retry': True}
        
        async with await get_db_session() as session:
            stmt = (
                update(User)
                .where(User.telegram_user_id == telegram_user_id)
                .values(
                    name=name.strip(),
                    registration_step=RegistrationStep.BIRTH_DATE.value
                )
            )
            await session.execute(stmt)
            await session.commit()
        
        return {
            'success': True,
            'message': f"""Приятно познакомиться, {name}! 😊

📅 Теперь укажите дату вашего рождения в формате ДД.ММ.ГГГГ

Например: 15.03.1990"""
        }
    
    async def _process_birth_date(self, telegram_user_id: int, date_text: str) -> Dict[str, Any]:
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
            
            async with await get_db_session() as session:
                stmt = (
                    update(User)
                    .where(User.telegram_user_id == telegram_user_id)
                    .values(
                        birth_date=birth_date,
                        registration_step=RegistrationStep.BIRTH_TIME.value
                    )
                )
                await session.execute(stmt)
                await session.commit()
            
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
    
    async def _process_birth_time(self, telegram_user_id: int, time_text: str) -> Dict[str, Any]:
        """Обработать ввод времени рождения"""
        time_text = time_text.strip().lower()
        
        if time_text in ['не знаю', 'незнаю', 'нет', 'неизвестно']:
            birth_time = '12:00'
            birth_time_unknown = True
            time_display = '12:00 (приблизительно)'
        else:
            try:
                # Попробуем разные форматы времени
                time_formats = ['%H:%M', '%H.%M', '%H-%M']
                parsed_time = None
                
                for time_format in time_formats:
                    try:
                        parsed_time = datetime.strptime(time_text, time_format)
                        break
                    except ValueError:
                        continue
                
                if not parsed_time:
                    return {
                        'error': 'Неверный формат времени. Используйте ЧЧ:ММ (например: 14:30) или напишите "не знаю"',
                        'retry': True
                    }
                
                birth_time = parsed_time.strftime('%H:%M')
                birth_time_unknown = False
                time_display = birth_time
                
            except Exception:
                return {
                    'error': 'Ошибка при обработке времени. Используйте формат ЧЧ:ММ или напишите "не знаю"',
                    'retry': True
                }
        
        async with await get_db_session() as session:
            stmt = (
                update(User)
                .where(User.telegram_user_id == telegram_user_id)
                .values(
                    birth_time=birth_time,
                    birth_time_unknown=birth_time_unknown,
                    registration_step=RegistrationStep.BIRTH_PLACE.value
                )
            )
            await session.execute(stmt)
            await session.commit()
        
        return {
            'success': True,
            'message': f"""Время рождения: {time_display}

🏙️ Теперь укажите город или место рождения

Например: Москва, Санкт-Петербург, Екатеринбург

Это нужно для точных астрологических расчетов натальной карты."""
        }
    
    async def _process_birth_place(self, telegram_user_id: int, place_text: str) -> Dict[str, Any]:
        """Обработать ввод места рождения"""
        if not place_text or len(place_text.strip()) < 2:
            return {'error': 'Пожалуйста, укажите место рождения', 'retry': True}
        
        async with await get_db_session() as session:
            stmt = (
                update(User)
                .where(User.telegram_user_id == telegram_user_id)
                .values(
                    birth_place=place_text.strip(),
                    registration_step=RegistrationStep.CURRENT_LOCATION.value
                )
            )
            await session.execute(stmt)
            await session.commit()
        
        return {
            'success': True,
            'message': f"""Место рождения: {place_text}

📍 Теперь укажите где вы живете сейчас:

🌍 Поделиться геолокацией (рекомендуется)
🏙️ Или написать название города

Это нужно для актуальных прогнозов с учетом времени восхода и заката в вашем регионе.""",
            'request_location': True
        }
    
    async def _process_current_location(self, telegram_user_id: int, message_text: str, location_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Обработать текущее местоположение"""
        if location_data:
            # Получена геолокация
            coordinates = {"lat": location_data['latitude'], "lon": location_data['longitude']}
            
            async with await get_db_session() as session:
                stmt = (
                    update(User)
                    .where(User.telegram_user_id == telegram_user_id)
                    .values(
                        current_coordinates=coordinates,
                        location_type='coordinates',
                        registration_step=RegistrationStep.FORECAST_TIME.value
                    )
                )
                await session.execute(stmt)
                await session.commit()
            
            # Логируем получение геолокации
            await self.log_user_action(
                telegram_user_id,
                ActionType.LOCATION_SHARED.value,
                context={'coordinates': coordinates}
            )
            
            location_display = f"📍 Координаты: {location_data['latitude']:.4f}, {location_data['longitude']:.4f}"
        else:
            # Получен текст с названием города
            if not message_text or len(message_text.strip()) < 2:
                return {'error': 'Пожалуйста, укажите город или поделитесь геолокацией', 'retry': True}
            
            async with await get_db_session() as session:
                stmt = (
                    update(User)
                    .where(User.telegram_user_id == telegram_user_id)
                    .values(
                        current_location=message_text.strip(),
                        location_type='city',
                        registration_step=RegistrationStep.FORECAST_TIME.value
                    )
                )
                await session.execute(stmt)
                await session.commit()
            
            location_display = f"🏙️ Город: {message_text}"
        
        return {
            'success': True,
            'message': f"""Текущее местоположение: {location_display}

⏰ Последний вопрос! В какое время присылать вам ежедневные астропрогнозы?

Укажите время в формате ЧЧ:ММ
Например: 09:00, 19:30

Рекомендуем утреннее время (8:00-10:00) для планирования дня."""
        }
    
    async def _process_forecast_time(self, telegram_user_id: int, time_text: str) -> Dict[str, Any]:
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
            
            # Завершаем регистрацию
            async with await get_db_session() as session:
                stmt = (
                    update(User)
                    .where(User.telegram_user_id == telegram_user_id)
                    .values(
                        forecast_time=forecast_time.strftime('%H:%M'),
                        frequency='daily',
                        language='ru',
                        astro_level='beginner',
                        registration_complete=True,
                        registered_at=datetime.utcnow(),
                        registration_step=RegistrationStep.COMPLETED.value
                    )
                )
                await session.execute(stmt)
                await session.commit()
            
            # Логируем завершение регистрации
            await self.log_user_action(
                telegram_user_id,
                ActionType.REGISTRATION_COMPLETED.value,
                context={'forecast_time': forecast_time.strftime('%H:%M')}
            )
            
            # Получаем обновленные данные пользователя для сводки
            user = await self.get_user(telegram_user_id)
            summary = await self._generate_registration_summary(user)
            
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
    
    async def _generate_registration_summary(self, user: User) -> str:
        """Сгенерировать сводку регистрации"""
        name = user.name or 'Пользователь'
        
        # Форматируем дату
        if user.birth_date:
            birth_date_formatted = user.birth_date.strftime('%d.%m.%Y')
        else:
            birth_date_formatted = 'не указана'
        
        time_note = ""
        if user.birth_time_unknown:
            time_note = " (приблизительно)"
        
        location_info = ""
        if user.location_type == 'coordinates' and user.current_coordinates:
            location_info = "📍 По геолокации"
        elif user.current_location:
            location_info = f"🏙️ {user.current_location}"
        
        return f"""📋 Ваши данные:
👤 Имя: {name}
📅 Дата рождения: {birth_date_formatted}
⏰ Время рождения: {user.birth_time or 'не указано'}{time_note}
🏙️ Место рождения: {user.birth_place or 'не указано'}
📍 Текущее местоположение: {location_info}
🔔 Время прогнозов: {user.forecast_time or 'не указано'}"""
    
    async def log_user_action(self, telegram_user_id: int, action_type: str, command: str = None, message_text: str = None, context: Dict[str, Any] = None):
        """Логировать действие пользователя"""
        try:
            action = UserAction(
                user_id=(await self.get_user(telegram_user_id)).id,
                action_type=action_type,
                command=command,
                message_text=message_text,
                context=context or {},
                created_at=datetime.utcnow()
            )
            
            async with await get_db_session() as session:
                session.add(action)
                await session.commit()
            
            # Обновляем ежедневную аналитику
            await self._update_daily_analytics(telegram_user_id, action_type, command)
            
        except Exception as e:
            logger.error(f"Error logging user action for {telegram_user_id}: {e}")
    
    async def _update_daily_analytics(self, telegram_user_id: int, action_type: str, command: str = None):
        """Обновить ежедневную аналитику пользователя"""
        try:
            user = await self.get_user(telegram_user_id)
            if not user:
                return
            
            today = date.today()
            
            async with await get_db_session() as session:
                # Ищем существующую запись аналитики на сегодня
                stmt = select(UserAnalytics).where(
                    and_(
                        UserAnalytics.user_id == user.id,
                        func.date(UserAnalytics.date) == today
                    )
                )
                result = await session.execute(stmt)
                analytics = result.scalar_one_or_none()
                
                if not analytics:
                    # Создаем новую запись
                    analytics = UserAnalytics(
                        user_id=user.id,
                        date=datetime.combine(today, datetime.min.time()),
                        first_activity_time=datetime.utcnow(),
                        commands_used=[]
                    )
                    session.add(analytics)
                
                # Обновляем счетчики
                analytics.last_activity_time = datetime.utcnow()
                
                if action_type == ActionType.MESSAGE_SENT.value:
                    analytics.total_messages += 1
                elif action_type == ActionType.COMMAND_USED.value:
                    analytics.total_commands += 1
                    if command and command not in analytics.commands_used:
                        analytics.commands_used.append(command)
                elif action_type == ActionType.ASTRO_REQUEST.value:
                    analytics.astro_requests += 1
                elif action_type == ActionType.MOON_REQUEST.value:
                    analytics.moon_requests += 1
                
                # Рассчитываем продолжительность сессии
                if analytics.first_activity_time and analytics.last_activity_time:
                    duration = analytics.last_activity_time - analytics.first_activity_time
                    analytics.session_duration_minutes = int(duration.total_seconds() / 60)
                
                # Простая оценка вовлеченности
                analytics.engagement_score = (
                    analytics.total_messages * 1.0 +
                    analytics.total_commands * 2.0 +
                    analytics.astro_requests * 3.0 +
                    analytics.moon_requests * 2.5
                )
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error updating daily analytics for {telegram_user_id}: {e}")
    
    async def get_user_analytics(self, telegram_user_id: int, days: int = 30) -> Dict[str, Any]:
        """Получить аналитику пользователя за последние дни"""
        try:
            user = await self.get_user(telegram_user_id)
            if not user:
                return {}
            
            # Получаем аналитику за последние дни
            start_date = datetime.now() - timedelta(days=days)
            
            async with await get_db_session() as session:
                stmt = (
                    select(UserAnalytics)
                    .where(
                        and_(
                            UserAnalytics.user_id == user.id,
                            UserAnalytics.date >= start_date
                        )
                    )
                    .order_by(desc(UserAnalytics.date))
                )
                result = await session.execute(stmt)
                analytics_records = result.scalars().all()
                
                # Считаем общую статистику
                total_messages = sum(a.total_messages for a in analytics_records)
                total_commands = sum(a.total_commands for a in analytics_records)
                total_astro_requests = sum(a.astro_requests for a in analytics_records)
                total_moon_requests = sum(a.moon_requests for a in analytics_records)
                avg_engagement = sum(a.engagement_score for a in analytics_records) / len(analytics_records) if analytics_records else 0
                
                # Активные дни
                active_days = len(analytics_records)
                
                # Самые используемые команды
                all_commands = []
                for a in analytics_records:
                    all_commands.extend(a.commands_used or [])
                
                command_counts = {}
                for cmd in all_commands:
                    command_counts[cmd] = command_counts.get(cmd, 0) + 1
                
                most_used_commands = sorted(command_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                
                return {
                    'user_info': {
                        'name': user.name,
                        'telegram_user_id': user.telegram_user_id,
                        'registered_at': user.registered_at.isoformat() if user.registered_at else None,
                        'first_seen': user.first_seen.isoformat() if user.first_seen else None,
                        'last_activity': user.last_activity.isoformat() if user.last_activity else None,
                        'registration_complete': user.registration_complete
                    },
                    'analytics_period': {
                        'days': days,
                        'active_days': active_days
                    },
                    'totals': {
                        'messages': total_messages,
                        'commands': total_commands,
                        'astro_requests': total_astro_requests,
                        'moon_requests': total_moon_requests,
                        'avg_engagement_score': round(avg_engagement, 2)
                    },
                    'most_used_commands': most_used_commands,
                    'daily_records': [
                        {
                            'date': a.date.date().isoformat(),
                            'messages': a.total_messages,
                            'commands': a.total_commands,
                            'astro_requests': a.astro_requests,
                            'moon_requests': a.moon_requests,
                            'engagement_score': a.engagement_score,
                            'session_duration_minutes': a.session_duration_minutes
                        } for a in analytics_records
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error getting user analytics for {telegram_user_id}: {e}")
            return {}

# Глобальный менеджер регистрации с БД
db_registration_manager = DatabaseRegistrationManager()
