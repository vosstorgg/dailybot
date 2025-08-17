import os
import logging
from aiohttp import web, ClientSession
import aiohttp_cors

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

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
        'version': '1.0.0',
        'endpoints': {
            'GET /': 'Health check',
            'GET|POST /set_webhook': 'Configure webhook',
            'POST /webhook': 'Telegram webhook endpoint'
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
            user_text = message.get('text', '')
            
            # Пока что простой ответ
            response_text = f"Hello World! 🌟\n\nВы написали: {user_text}"
            await send_message(chat_id, response_text)
            
        return web.json_response({'status': 'ok'})
    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def set_webhook(request):
    """Настройка webhook для бота"""
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
    app.router.add_get('/set_webhook', set_webhook)
    app.router.add_post('/set_webhook', set_webhook)
    
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