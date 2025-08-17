import os
import logging
from flask import Flask, request, jsonify
import requests

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Получаем токен бота из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

def send_message(chat_id, text):
    """Отправляет сообщение пользователю"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text
    }
    response = requests.post(url, json=data)
    return response.json()

@app.route('/', methods=['GET'])
def health_check():
    """Проверка работоспособности сервиса"""
    return jsonify({'status': 'ok', 'message': 'Dailybot is running!'})

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработчик webhook от Telegram"""
    try:
        update = request.get_json()
        logger.info(f"Received update: {update}")
        
        # Проверяем, что это сообщение
        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            
            # Отвечаем "Hello World" на любое сообщение
            send_message(chat_id, "Hello World! 🌟")
            
        return jsonify({'status': 'ok'})
    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/set_webhook', methods=['POST'])
def set_webhook():
    """Устанавливает webhook для бота"""
    if not BOT_TOKEN or not WEBHOOK_URL:
        return jsonify({'error': 'BOT_TOKEN or WEBHOOK_URL not set'}), 400
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    data = {'url': f"{WEBHOOK_URL}/webhook"}
    
    response = requests.post(url, json=data)
    result = response.json()
    
    if result.get('ok'):
        return jsonify({'status': 'success', 'message': 'Webhook set successfully'})
    else:
        return jsonify({'status': 'error', 'message': result.get('description', 'Unknown error')})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
