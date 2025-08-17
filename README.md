# DailyBot - Telegram Астро-бот

Telegram бот для ежедневных астрологических прогнозов и эзотерических сводок.

## Возможности

- Webhook интеграция с Telegram
- Астрологические прогнозы (планируется)
- Карты Таро (планируется)
- Персонализированные рекомендации (планируется)

## Развертывание на Railway

### 1. Подготовка

1. Создайте бота в Telegram через [@BotFather](https://t.me/botfather)
2. Получите токен бота
3. Форкните этот репозиторий

### 2. Развертывание на Railway

1. Зайдите на [railway.app](https://railway.app)
2. Подключите ваш GitHub аккаунт
3. Создайте новый проект из вашего репозитория
4. В настройках проекта добавьте переменные окружения:
   - `BOT_TOKEN` - токен вашего Telegram бота
   - `WEBHOOK_URL` - URL вашего приложения на Railway (например: `https://your-app-name.up.railway.app`)

### 3. Настройка webhook

После развертывания:

1. Откройте ваше приложение в браузере
2. Перейдите на `/set_webhook` (POST запрос) или используйте curl:

```bash
curl -X POST https://your-app-name.up.railway.app/set_webhook
```

### 4. Тестирование

Отправьте любое сообщение вашему боту - он должен ответить "Hello World! 🌟"

## Локальная разработка

1. Клонируйте репозиторий:
```bash
git clone <ваш-репозиторий>
cd dailybot
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `.env` на основе `env.example`:
```bash
cp env.example .env
```

5. Заполните переменные в `.env`

6. Запустите приложение:
```bash
python app.py
```

## Структура проекта

```
dailybot/
├── app.py              # Основное приложение Flask
├── requirements.txt    # Python зависимости
├── Procfile           # Конфигурация для Railway
├── .gitignore         # Игнорируемые файлы
├── env.example        # Пример переменных окружения
└── README.md          # Документация
```

## Переменные окружения

- `BOT_TOKEN` - Токен Telegram бота (обязательно)
- `WEBHOOK_URL` - URL webhook для Railway (обязательно)
- `PORT` - Порт приложения (автоматически устанавливается Railway)

## API Endpoints

- `GET /` - Проверка здоровья сервиса
- `POST /webhook` - Webhook для получения обновлений от Telegram
- `POST /set_webhook` - Установка webhook в Telegram

## Планы развития

- [ ] Регистрация пользователей
- [ ] Астрологические API интеграции
- [ ] OpenAI интеграция для генерации прогнозов
- [ ] Персональные настройки
- [ ] Планировщик уведомлений
- [ ] Дневник эмоций
