# Быстрый гайд по деплою на Railway 🚀

## Шаги для деплоя:

### 1. Загрузите код на GitHub
```bash
git push origin main
```

### 2. В Railway подключите GitHub репозиторий
1. Откройте ваш проект в Railway
2. Connect → GitHub → выберите ваш репозиторий

### 3. Настройте переменные окружения в Railway
В разделе **Variables** добавьте:

```
TELEGRAM_TOKEN=ваш_токен_от_BotFather
OPENAI_API_KEY=ваш_ключ_от_OpenAI
WEBHOOK_URL=https://ваш-домен.railway.app
PORT=8000
```

### 4. Получите ваш домен
1. **Settings** → **Domains** 
2. Скопируйте домен (например: `my-bot-abc123.railway.app`)
3. Обновите `WEBHOOK_URL=https://my-bot-abc123.railway.app`

### 5. Деплой автоматически запустится! 🎉

## Проверка работы:
- Health check: `https://ваш-домен.railway.app/health`
- Отправьте голосовое сообщение боту

## Если что-то не работает:
1. Проверьте логи в Railway
2. Убедитесь, что все переменные окружения установлены
3. Проверьте webhook: заменитe `YOUR_BOT_TOKEN` и выполните:
   ```bash
   curl "https://api.telegram.org/botYOUR_BOT_TOKEN/getWebhookInfo"
   ```

## Готово! 🎯
Ваш бот теперь работает в облаке Railway! 