@echo off
echo DailyBot Local Development
echo ========================

if "%1"=="" (
    echo Использование:
    echo   run.bat install   - Установить зависимости
    echo   run.bat webhook   - Запуск webhook сервера
    echo   run.bat polling   - Запуск polling бота
    echo   run.bat test      - Тест эндпоинтов
    goto :eof
)

if "%1"=="install" (
    echo Установка зависимостей...
    pip install -r requirements.txt
    echo ✅ Зависимости установлены!
    goto :eof
)

if "%1"=="webhook" (
    echo 🔗 Запуск webhook сервера...
    python run_local.py webhook
    goto :eof
)

if "%1"=="polling" (
    echo 🔄 Запуск polling бота...
    python run_local.py polling
    goto :eof
)

if "%1"=="test" (
    echo 🧪 Тестирование эндпоинтов...
    echo Запуск сервера на порту 8000...
    start python run_local.py webhook
    timeout /t 3 /nobreak >nul
    echo Тестирование главной страницы...
    curl http://localhost:8000/ || echo "Curl не найден, откройте http://localhost:8000/ в браузере"
    goto :eof
)

echo ❌ Неизвестная команда: %1
