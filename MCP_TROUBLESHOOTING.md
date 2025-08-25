# 🔧 MCP Integration Troubleshooting Guide

## 🚨 **Проблема:** Бот возвращает старый placeholder вместо MCP TLDR

### 📋 **Симптомы:**
- Отправляете YouTube ссылку боту
- Получаете старый ответ: "🎥 YouTube TLDR" с placeholder текстом
- Вместо ожидаемого: "🎥 **YouTube TLDR (MCP)**" с реальным TLDR

### 🔍 **Диагностика:**

#### **1. Проверка Railway Dashboard:**
1. Откройте [Railway Dashboard](https://railway.app/dashboard)
2. Найдите проект `tldr_buddy`
3. Проверьте статус деплоя (должен быть ✅ "Deployed")
4. Посмотрите логи на предмет ошибок

#### **2. Проверка версии через Debug Endpoint:**
После деплоя (5-10 минут) проверьте:
```
https://your-railway-app.railway.app/debug
```

**Ожидаемый результат:**
```
🔍 MCP Integration Debug Report

Files:
- mcp_youtube_real.py: ✅ Exists
- get_transcript.py: ✅ Exists

Import:
- MCP Import: ✅ Success

Git:
- Commit: ✅ e18d7b4

Expected: All files should exist and MCP should import successfully
```

#### **3. Проверка Health Endpoint:**
```
https://your-railway-app.railway.app/health
```

### 🎯 **Возможные причины:**

#### **A. Railway не развернул последние изменения:**
- **Причина:** Railway еще развертывает (5-10 минут)
- **Решение:** Подождите и проверьте снова

#### **B. Ошибка в логах Railway:**
- **Причина:** Импорт MCP модулей не удался
- **Решение:** Проверьте логи Railway на предмет ошибок

#### **C. Переменные окружения:**
- **Причина:** `TLDRBUDDY_ENABLED` не установлен
- **Решение:** Убедитесь, что `TLDRBUDDY_ENABLED=true` в Railway

#### **D. Кэширование Telegram:**
- **Причина:** Telegram кэширует старые ответы
- **Решение:** Отправьте новое сообщение боту

### 🛠️ **Шаги по устранению:**

#### **Шаг 1: Проверьте Railway Dashboard**
1. Убедитесь, что последний коммит развернут
2. Проверьте логи на ошибки
3. Убедитесь, что приложение запущено

#### **Шаг 2: Проверьте Debug Endpoint**
1. Откройте `/debug` endpoint
2. Убедитесь, что все файлы существуют
3. Убедитесь, что MCP импорт успешен

#### **Шаг 3: Проверьте переменные окружения**
1. В Railway Dashboard перейдите в Variables
2. Убедитесь, что `TLDRBUDDY_ENABLED=true`
3. Перезапустите приложение если нужно

#### **Шаг 4: Тестирование**
1. Отправьте YouTube ссылку боту
2. Ожидайте ответ: "🎥 Обрабатываем YouTube видео через MCP..."
3. Затем должен появиться TLDR в формате LONGFORM

### 📊 **Локальное тестирование:**

#### **Запустите локальный тест:**
```bash
python debug_mcp_bot.py
```

**Ожидаемый результат:**
```
✅ MCP processor created: True
✅ MCP processor is available - should use MCP
✅ MCP processing successful!
✅ Ready for SummaryEngine processing
✅ Expected bot response:
🎥 **YouTube TLDR (MCP)**
```

### 🎯 **Ожидаемое поведение после исправления:**

1. **Отправляете:** `https://www.youtube.com/watch?v=1vQ0RpfCqH0`
2. **Получаете:** "🎥 Обрабатываем YouTube видео через MCP..."
3. **Затем:** Полный TLDR в формате LONGFORM с реальным контентом

### 📞 **Если проблема не решается:**

1. **Проверьте логи Railway** на критические ошибки
2. **Убедитесь, что все файлы** отправлены в git
3. **Проверьте переменные окружения** в Railway
4. **Перезапустите приложение** в Railway Dashboard

### 🎉 **Успешное исправление:**

После исправления бот должен:
- ✅ Автоматически определять YouTube URL
- ✅ Использовать MCP процессор
- ✅ Получать транскрипты через get_transcript сервис
- ✅ Генерировать TLDR в формате LONGFORM
- ✅ Отправлять качественные результаты

---

**🔧 Если проблема остается, проверьте Railway логи для детальной диагностики.** 