#!/usr/bin/env python3
"""
Скрипт для локального запуска бота в разных режимах
"""
import os
import sys
import asyncio
from dotenv import load_dotenv

# Загружаем локальные переменные
load_dotenv('.env.local')

def print_banner():
    print("🚀 DailyBot Local Development")
    print("=" * 40)
    print(f"BOT_TOKEN: {'✅ Set' if os.getenv('BOT_TOKEN') else '❌ Not set'}")
    print(f"WEBHOOK_URL: {os.getenv('WEBHOOK_URL', 'Not set')}")
    print(f"PORT: {os.getenv('PORT', '8000')}")
    print("=" * 40)

def run_webhook_mode():
    """Запуск в webhook режиме (нужен ngrok или Railway)"""
    print("🔗 Webhook Mode - нужен публичный URL")
    print("Варианты:")
    print("1. Используйте ngrok: ngrok http 8000")
    print("2. Деплойте на Railway и используйте его URL")
    print("3. Используйте локальный URL только для тестирования эндпоинтов")
    print("")
    
    from app import create_app
    from aiohttp import web
    
    app = create_app()
    port = int(os.getenv('PORT', 8000))
    
    print(f"🌐 Сервер запущен на http://localhost:{port}")
    print("📍 Доступные эндпоинты:")
    print(f"   GET  http://localhost:{port}/")
    print(f"   GET  http://localhost:{port}/set_webhook")
    print(f"   POST http://localhost:{port}/webhook")
    
    web.run_app(app, host='localhost', port=port)

def run_polling_mode():
    """Запуск в polling режиме (для локальной разработки)"""
    print("🔄 Polling Mode - для локальной разработки")
    
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        print("❌ BOT_TOKEN не установлен!")
        return
    
    # Простой polling бот для тестирования
    import asyncio
    import aiohttp
    
    async def polling_bot():
        session = aiohttp.ClientSession()
        offset = 0
        
        print("🤖 Бот запущен в polling режиме...")
        print("💬 Отправьте сообщение боту для тестирования")
        
        try:
            while True:
                # Получаем обновления
                url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
                params = {'offset': offset, 'timeout': 30}
                
                async with session.get(url, params=params) as response:
                    data = await response.json()
                    
                    if data.get('ok') and data.get('result'):
                        for update in data['result']:
                            offset = update['update_id'] + 1
                            
                            # Обрабатываем сообщение
                            if 'message' in update:
                                message = update['message']
                                chat_id = message['chat']['id']
                                user_name = message.get('from', {}).get('first_name', 'Unknown')
                                text = message.get('text', '')
                                
                                print(f"📩 Сообщение от {user_name}: {text}")
                                
                                # Отвечаем
                                reply_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                                reply_data = {
                                    'chat_id': chat_id,
                                    'text': f"Hello World! 🌟\n\nВы написали: {text}"
                                }
                                
                                async with session.post(reply_url, json=reply_data) as reply_response:
                                    reply_result = await reply_response.json()
                                    if reply_result.get('ok'):
                                        print(f"✅ Ответ отправлен")
                                    else:
                                        print(f"❌ Ошибка отправки: {reply_result}")
                
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Остановка бота...")
        finally:
            await session.close()
    
    asyncio.run(polling_bot())

def main():
    print_banner()
    
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python run_local.py webhook  - Запуск webhook сервера")
        print("  python run_local.py polling  - Запуск polling бота")
        return
    
    mode = sys.argv[1].lower()
    
    if mode == 'webhook':
        run_webhook_mode()
    elif mode == 'polling':
        run_polling_mode()
    else:
        print("❌ Неизвестный режим. Используйте 'webhook' или 'polling'")

if __name__ == '__main__':
    main()
