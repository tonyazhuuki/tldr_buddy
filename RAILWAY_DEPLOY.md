# Деплой Telegram Voice Bot на Railway

## Подготовка к деплою

### 1. Подключение к GitHub

1. Убедитесь, что ваш код загружен в GitHub репозиторий
2. В Railway зайдите в свой проект
3. Подключите GitHub репозиторий к Railway

### 2. Настройка переменных окружения

В Railway перейдите в раздел **Variables** и добавьте следующие переменные:

#### Обязательные переменные:
```
TELEGRAM_TOKEN=ваш_токен_телеграм_бота
OPENAI_API_KEY=ваш_ключ_openai
WEBHOOK_URL=https://ваш-домен.railway.app
PORT=8000
```

#### Дополнительные переменные (опционально):
```
REDIS_URL=redis://localhost:6379
PYTHONUNBUFFERED=1
PYTHONPATH=/app
```

### 3. Настройка домена

1. В Railway перейдите в **Settings** → **Domains**
2. Скопируйте ваш домен (например: `your-app-12345.railway.app`)
3. Установите переменную `WEBHOOK_URL=https://your-app-12345.railway.app`

## Деплой

### Автоматический деплой

1. Railway автоматически задеплоит проект при push в GitHub
2. Проверьте логи в Railway для отслеживания процесса

### Проверка работы

1. Откройте `https://ваш-домен.railway.app/health` для проверки статуса
2. Отправьте голосовое сообщение боту в Telegram

## Устранение проблем

### Если бот не отвечает:

1. Проверьте логи в Railway
2. Убедитесь, что все переменные окружения настроены
3. Проверьте, что webhook установлен корректно

### Проверка webhook:

```bash
curl -X GET "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

### Сброс webhook (если нужно):

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/deleteWebhook"
```

## Структура проекта для Railway

- `Dockerfile` - для контейнеризации
- `Procfile` - команда запуска
- `railway.json` - конфигурация Railway
- `requirements.txt` - зависимости Python
- `.gitignore` - исключения из Git

## Примечания

- Бот работает в режиме webhook на Railway
- Локально можно запускать в режиме polling (без WEBHOOK_URL)
- Health check доступен по `/health`
- Логи сохраняются в Railway для отладки 