import os
import logging
from aiohttp import web, ClientSession
import aiohttp_cors
from astro_service import get_daily_astro_summary, test_weather_api_connection, clear_cache

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
        'version': '1.1.0',
        'features': ['telegram_bot', 'astrology', 'moon_phases'],
        'configuration': {
            'BOT_TOKEN': '✓' if BOT_TOKEN else '✗',
            'WEBHOOK_URL': '✓' if WEBHOOK_URL else '✗',
            'WEATHER_API_KEY': '✓' if WEATHER_API_KEY else '✗'
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
            user_text = message.get('text', '').lower().strip()
            user_id = message.get('from', {}).get('id')
            
            # Обработка команд
            if user_text.startswith('/'):
                await handle_command(chat_id, user_id, user_text)
            else:
                # Простая обработка текста
                await handle_text_message(chat_id, user_id, user_text)
            
        return web.json_response({'status': 'ok'})
    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def handle_command(chat_id, user_id, command):
    """Обработка команд бота"""
    if command == '/start':
        response = """🌟 Добро пожаловать в DailyBot!
        
Я помогу вам получать ежедневные астрологические прогнозы.

Команды:
/astro - Астрологическая сводка на сегодня
/moon - Информация о Луне
/help - Помощь

Скоро будет доступна регистрация с указанием местоположения для персональных прогнозов! ✨"""
        
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
    
    elif command == '/help':
        response = """📖 Помощь по DailyBot

Доступные команды:
/start - Начало работы
/astro - Получить астрологическую сводку
/moon - Информация о текущей фазе Луны
/help - Эта справка

🔮 DailyBot использует данные о положении планет и Луны для создания персонализированных астрологических прогнозов.

Скоро будут доступны:
• Регистрация с указанием города
• Персональные прогнозы по времени рождения  
• Настройка времени получения прогнозов"""
    
    else:
        response = "❓ Неизвестная команда. Используйте /help для списка команд."
    
    await send_message(chat_id, response)

async def handle_text_message(chat_id, user_id, text):
    """Обработка текстовых сообщений"""
    if not text:
        return
    
    # Простое эхо с подсказкой
    response = f"""Вы написали: "{text}"

💡 Попробуйте команды:
/astro - Астрологический прогноз
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