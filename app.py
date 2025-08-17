import os
import logging
from aiohttp import web, ClientSession
import aiohttp_cors
from astro_service import get_daily_astro_summary, test_weather_api_connection, clear_cache
from user_registration import RegistrationStep
from database import initialize_database, db_manager
from db_registration_adapter import db_registration_manager

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')

# Простое хранилище пользователей (в будущем заменим на БД)
users_storage = {}

async def send_message(chat_id, text):
    """Отправляет сообщение пользователю через Telegram Bot API"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {'chat_id': chat_id, 'text': text}
    
    async with ClientSession() as session:
        async with session.post(url, json=data) as response:
            return await response.json()

async def health_check(request):
    """Проверка работоспособности сервиса"""
    return web.json_response({
        'status': 'ok', 
        'message': 'DailyBot is running!',
        'version': '1.2.0',
        'features': ['telegram_bot', 'astrology', 'moon_phases', 'user_registration', 'postgresql_db'],
        'configuration': {
            'BOT_TOKEN': '✓' if BOT_TOKEN else '✗',
            'WEBHOOK_URL': '✓' if WEBHOOK_URL else '✗',
            'WEATHER_API_KEY': '✓' if WEATHER_API_KEY else '✗',
            'DATABASE_URL': '✓' if os.getenv('DATABASE_URL') else '✗'
        },
        'endpoints': {
            'GET /': 'Health check',
            'GET /webhook/status': 'Check webhook status',
            'POST /webhook/set': 'Configure webhook',
            'POST /webhook': 'Telegram webhook endpoint',
            'GET /astro/today': 'Get today\'s astrology summary',
            'GET /astro/test': 'Test WeatherAPI connection',
            'POST /astro/cache/clear': 'Clear astro cache (dev)'
        }
    })

async def webhook(request):
    """Обработчик webhook от Telegram"""
    try:
        update = await request.json()
        logger.info(f"Received update from user: {update.get('message', {}).get('from', {}).get('id', 'unknown')}")
        
        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            user_id = message.get('from', {}).get('id')
            
            # Обработка геолокации
            if 'location' in message:
                await handle_location(chat_id, user_id, message['location'])
            # Обработка команд
            elif 'text' in message:
                user_text = message['text'].lower().strip()
                if user_text.startswith('/'):
                    await handle_command(chat_id, user_id, user_text)
                else:
                    # Простая обработка текста
                    await handle_text_message(chat_id, user_id, user_text)
            else:
                # Неподдерживаемый тип сообщения
                await send_message(chat_id, "Извините, я пока поддерживаю только текстовые сообщения и геолокацию.")
            
        return web.json_response({'status': 'ok'})
    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def handle_location(chat_id, user_id, location_data):
    """Обработка геолокации от пользователя"""
    try:
        # Проверяем, ожидается ли геолокация в процессе регистрации
        current_step = db_registration_manager.get_registration_step(user_id)
        
        if current_step == RegistrationStep.CURRENT_LOCATION:
            # Обрабатываем геолокацию в процессе регистрации
            result = await db_registration_manager.process_registration_step(
                user_id, "", location_data  # пустой текст, передаем location_data
            )
            
            if result.get('success'):
                await send_message(chat_id, result['message'])
            else:
                await send_message(chat_id, f"❌ {result.get('error', 'Ошибка обработки геолокации')}")
        else:
            # Геолокация вне процесса регистрации
            lat, lon = location_data['latitude'], location_data['longitude']
            await send_message(chat_id, f"""📍 Получил вашу геолокацию!

Координаты: {lat:.4f}, {lon:.4f}

Если вы хотите обновить свое местоположение для более точных прогнозов, используйте /start для обновления профиля.""")
            
    except Exception as e:
        logger.error(f"Error handling location: {e}")
        await send_message(chat_id, "❌ Ошибка при обработке геолокации.")

async def handle_command(chat_id, user_id, command):
    """Обработка команд бота"""
    if command == '/start':
        # Проверяем, зарегистрирован ли пользователь
        if db_registration_manager.is_registration_complete(user_id):
            user = await db_registration_manager.get_user(user_id)
            name = user.personal.get('name', 'Пользователь') if user else 'Пользователь'
            response = f"""🌟 С возвращением, {name}!

Ваши команды:
/astro - Персональный астропрогноз на сегодня
/moon - Информация о Луне
/profile - Ваши данные
/help - Справка

Получить прогноз прямо сейчас? Используйте /astro ✨"""
        else:
            # Начинаем регистрацию
            user_telegram_data = {
                'user_id': user_id,
                'first_name': 'User',  # В реальности получаем из update
                'username': None
            }
            response = await db_registration_manager.start_registration(user_id, user_telegram_data)
        
    elif command == '/astro':
        try:
            summary = await get_daily_astro_summary()
            if summary.get('status') == 'error':
                response = "❌ Извините, временно не могу получить астрологические данные. Попробуйте позже."
            else:
                moon = summary['moon']
                response = f"""🔮 Астрологическая сводка на {summary['date']}

{moon['description']}

✨ Общая энергетика:
{summary['general_energy']}

📋 Рекомендации на день:
""" + '\n'.join(summary['recommendations'])
        except Exception as e:
            logger.error(f"Error getting astro summary for user: {e}")
            response = "❌ Произошла ошибка при получении астрологических данных."
    
    elif command == '/moon':
        try:
            summary = await get_daily_astro_summary()
            if summary.get('status') == 'error':
                response = "❌ Не могу получить данные о Луне."
            else:
                moon = summary['moon']
                response = f"""🌙 Лунная информация

{moon['description']}

Освещенность: {moon['illumination']}%
Дата: {summary['date']}"""
        except Exception as e:
            response = "❌ Ошибка получения лунных данных."
    
    elif command == '/profile':
        if not db_registration_manager.is_registration_complete(user_id):
            response = """📋 Вы еще не зарегистрированы!

Используйте /start для создания персонального профиля и получения точных астрологических прогнозов."""
        else:
            user = await db_registration_manager.get_user(user_id)
            if user:
                response = f"""👤 Ваш профиль:

{db_registration_manager._generate_registration_summary(user)}

Для изменения данных используйте /start (перерегистрация)."""
            else:
                response = "❌ Ошибка получения данных профиля. Попробуйте /start"
    
    elif command == '/help':
        if db_registration_manager.is_registration_complete(user_id):
            response = """📖 Помощь по DailyBot

Доступные команды:
/start - Главное меню (или перерегистрация)
/astro - Персональный астропрогноз на сегодня
/moon - Информация о текущей фазе Луны
/profile - Ваши данные и настройки
/help - Эта справка

🔮 DailyBot создает персональные астрологические прогнозы на основе вашей натальной карты и текущих планетарных транзитов."""
        else:
            response = """📖 Помощь по DailyBot

Для начала работы используйте /start - это запустит процесс регистрации.

После регистрации вам будут доступны:
• Персональные астропрогнозы
• Информация о лунных фазах
• Ежедневные рекомендации
• Настройка времени получения прогнозов

🔮 Все прогнозы основаны на реальных астрономических данных и вашей натальной карте."""
    
    else:
        response = "❓ Неизвестная команда. Используйте /help для списка команд."
    
    await send_message(chat_id, response)

async def handle_text_message(chat_id, user_id, text):
    """Обработка текстовых сообщений"""
    if not text:
        return
    
    # Проверяем, находится ли пользователь в процессе регистрации
    current_step = db_registration_manager.get_registration_step(user_id)
    
    if current_step != RegistrationStep.NOT_STARTED and current_step != RegistrationStep.COMPLETED:
        # Пользователь в процессе регистрации
        result = await db_registration_manager.process_registration_step(user_id, text)
        
        if result.get('error'):
            if result.get('restart'):
                # Начинаем регистрацию заново
                user_telegram_data = {'user_id': user_id, 'first_name': 'User'}
                response = await db_registration_manager.start_registration(user_id, user_telegram_data)
            else:
                response = f"❌ {result['error']}"
        elif result.get('success'):
            response = result['message']
            
            # Если регистрация завершена, отправляем первый прогноз
            if result.get('completed'):
                await send_message(chat_id, response)
                # Отправляем первый астропрогноз
                try:
                    summary = await get_daily_astro_summary()
                    if summary.get('status') != 'error':
                        moon = summary['moon']
                        astro_response = f"""🔮 Ваш первый персональный прогноз!

{moon['description']}

✨ Общая энергетика:
{summary['general_energy']}

📋 Рекомендации на день:
""" + '\n'.join(summary['recommendations'])
                        await send_message(chat_id, astro_response)
                    return
                except Exception as e:
                    logger.error(f"Error sending first forecast: {e}")
                return
        else:
            response = "❌ Произошла ошибка при обработке данных."
    else:
        # Обычное сообщение от зарегистрированного пользователя
        if db_registration_manager.is_registration_complete(user_id):
            response = f"""💬 Получил ваше сообщение: "{text}"

💡 Доступные команды:
/astro - Персональный прогноз
/moon - Фаза Луны  
/profile - Ваши данные
/help - Справка"""
        else:
            response = f"""💬 Получил ваше сообщение: "{text}"

Для получения персональных астропрогнозов используйте /start для регистрации.

💡 Или попробуйте:
/moon - Фаза Луны
/help - Справка"""
    
    await send_message(chat_id, response)

async def set_webhook(request):
    """Настройка webhook для бота (только POST)"""
    if not BOT_TOKEN or not WEBHOOK_URL:
        return web.json_response({
            'error': 'Configuration missing',
            'details': {
                'BOT_TOKEN': 'Set' if BOT_TOKEN else 'Missing',
                'WEBHOOK_URL': 'Set' if WEBHOOK_URL else 'Missing'
            }
        }, status=400)
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    data = {'url': f"{WEBHOOK_URL}/webhook"}
    
    async with ClientSession() as session:
        async with session.post(url, json=data) as response:
            result = await response.json()
    
    if result.get('ok'):
        return web.json_response({
            'status': 'success', 
            'message': 'Webhook configured successfully',
            'webhook_url': f"{WEBHOOK_URL}/webhook"
        })
    else:
        return web.json_response({
            'status': 'error', 
            'message': result.get('description', 'Unknown error'),
            'telegram_response': result
        }, status=400)

async def webhook_status(request):
    """Проверка статуса webhook (безопасный GET)"""
    if not BOT_TOKEN:
        return web.json_response({'error': 'BOT_TOKEN not configured'}, status=400)
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
    
    async with ClientSession() as session:
        async with session.get(url) as response:
            result = await response.json()
    
    if result.get('ok'):
        webhook_info = result['result']
        return web.json_response({
            'status': 'success',
            'webhook_configured': bool(webhook_info.get('url')),
            'webhook_url': webhook_info.get('url', ''),
            'has_custom_certificate': webhook_info.get('has_custom_certificate', False),
            'pending_update_count': webhook_info.get('pending_update_count', 0),
            'last_error_date': webhook_info.get('last_error_date'),
            'last_error_message': webhook_info.get('last_error_message')
        })
    else:
        return web.json_response({
            'error': 'Failed to get webhook info',
            'telegram_response': result
        }, status=400)

async def get_astro_today(request):
    """Получить астрологическую сводку на сегодня"""
    try:
        summary = await get_daily_astro_summary()
        return web.json_response(summary)
    except Exception as e:
        logger.error(f"Error getting astro summary: {e}")
        return web.json_response({
            'error': 'Unable to fetch astrology data',
            'details': str(e)
        }, status=500)

async def test_astro_api(request):
    """Тестировать подключение к WeatherAPI"""
    result = await test_weather_api_connection()
    status_code = 200 if result['status'] == 'success' else 500
    return web.json_response(result, status=status_code)

async def clear_astro_cache(request):
    """Очистить кэш астрологических данных (для разработки)"""
    try:
        clear_cache()
        return web.json_response({
            'status': 'success',
            'message': 'Astro cache cleared'
        })
    except Exception as e:
        return web.json_response({
            'status': 'error',
            'message': str(e)
        }, status=500)

def create_app():
    """Создает и настраивает aiohttp приложение"""
    logger.info("Initializing DailyBot application...")
    logger.info(f"Configuration: BOT_TOKEN={'✓' if BOT_TOKEN else '✗'}, WEBHOOK_URL={'✓' if WEBHOOK_URL else '✗'}")
    
    app = web.Application()
    
    # CORS настройки
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*"
        )
    })
    
    # Маршруты
    app.router.add_get('/', health_check)
    app.router.add_post('/webhook', webhook)
    app.router.add_get('/webhook/status', webhook_status)
    app.router.add_post('/webhook/set', set_webhook)
    
    # Астрологические эндпоинты
    app.router.add_get('/astro/today', get_astro_today)
    app.router.add_get('/astro/test', test_astro_api)
    app.router.add_post('/astro/cache/clear', clear_astro_cache)
    
    # Добавляем CORS для всех маршрутов
    for route in list(app.router.routes()):
        cors.add(route)
    
    logger.info("Application initialized successfully!")
    return app

# Экспорт для внешних серверов
application = create_app()

if __name__ == '__main__':
    # Прямой запуск
    port = int(os.environ.get('PORT', 8080))
    host = os.environ.get('HOST', '0.0.0.0')
    logger.info(f"Starting DailyBot server on {host}:{port}")
    web.run_app(application, host=host, port=port)