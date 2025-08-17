import os
import logging
import asyncio
from aiohttp import web, ClientSession
import aiohttp_cors

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем токен бота из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

async def send_message(chat_id, text):
    """Асинхронно отправляет сообщение пользователю"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text
    }
    
    async with ClientSession() as session:
        async with session.post(url, json=data) as response:
            return await response.json()

async def health_check(request):
    """Проверка работоспособности сервиса"""
    return web.json_response({
        'status': 'ok', 
        'message': 'Dailybot is running!',
        'endpoints': {
            'GET /': 'Health check',
            'GET /set_webhook': 'Set webhook (also accepts POST)',
            'POST /webhook': 'Telegram webhook endpoint'
        }
    })

async def webhook(request):
    """Асинхронный обработчик webhook от Telegram"""
    try:
        update = await request.json()
        logger.info(f"Received update: {update}")
        
        # Проверяем, что это сообщение
        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            
            # Асинхронно отвечаем "Hello World" на любое сообщение
            await send_message(chat_id, "Hello World! 🌟")
            
        return web.json_response({'status': 'ok'})
    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def set_webhook(request):
    """Асинхронно устанавливает webhook для бота"""
    if not BOT_TOKEN or not WEBHOOK_URL:
        return web.json_response({'error': 'BOT_TOKEN or WEBHOOK_URL not set'}, status=400)
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    data = {'url': f"{WEBHOOK_URL}/webhook"}
    
    async with ClientSession() as session:
        async with session.post(url, json=data) as response:
            result = await response.json()
    
    if result.get('ok'):
        return web.json_response({'status': 'success', 'message': 'Webhook set successfully'})
    else:
        return web.json_response({'status': 'error', 'message': result.get('description', 'Unknown error')})

def create_app():
    """Создает и настраивает aiohttp приложение"""
    app = web.Application()
    
    # Настройка CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*"
        )
    })
    
    # Добавляем routes
    app.router.add_get('/', health_check)
    app.router.add_post('/webhook', webhook)
    app.router.add_post('/set_webhook', set_webhook)
    app.router.add_get('/set_webhook', set_webhook)  # Добавляем GET для удобства
    
    # Добавляем CORS для всех routes
    for route in list(app.router.routes()):
        cors.add(route)
    
    return app

# Создаем приложение для gunicorn
app = create_app()

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    web.run_app(app, host='0.0.0.0', port=port)
