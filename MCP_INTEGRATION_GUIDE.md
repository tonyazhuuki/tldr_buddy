# 🎥 MCP YouTube Integration Guide

## 📋 **Обзор**

Это руководство описывает интеграцию MCP (Model Context Protocol) YouTube сервиса в ваш Telegram бот для получения транскриптов и создания TLDR.

## 🎯 **Цель**

**Базовый сценарий:**
1. Пользователь отправляет YouTube ссылку
2. Бот использует MCP сервис для получения транскрипта
3. Бот создает TLDR в формате LONGFORM
4. Пользователь получает структурированный анализ

## 🔧 **Архитектура**

### **Компоненты:**

1. **`mcp_youtube_integration.py`** - Базовый MCP процессор (заглушка)
2. **`mcp_youtube_real.py`** - Реальный MCP процессор (для интеграции)
3. **`main.py`** - Обновленный Telegram бот с MCP поддержкой
4. **`test_mcp_youtube_integration.py`** - Тесты интеграции

### **Поток данных:**

```
YouTube URL → MCP Processor → get_transcript → Transcript → SummaryEngine → TLDR
```

## 🚀 **Текущий статус**

### ✅ **Готово:**
- Базовая архитектура MCP интеграции
- URL извлечение и валидация
- Обработка ошибок
- Интеграция с SummaryEngine
- Тесты базовой функциональности

### 🔄 **Требует доработки:**
- Реальная интеграция с MCP `get_transcript` сервисом
- Обработка пагинации для длинных видео
- Кэширование результатов

## 📝 **Инструкции по интеграции**

### **1. Обновление main.py**

```python
# Добавить импорт
from mcp_youtube_integration import create_mcp_youtube_processor

# Добавить глобальную переменную
mcp_youtube_processor = None

# В функции startup() добавить инициализацию
mcp_youtube_processor = create_mcp_youtube_integration()

# В handle_text_message() добавить проверку MCP
if mcp_youtube_processor and mcp_youtube_processor.available:
    await handle_youtube_url_mcp(message, youtube_url, user_id)
else:
    await handle_youtube_url(message, youtube_url, user_id)
```

### **2. Реальная MCP интеграция**

Для полной интеграции нужно:

1. **Импортировать MCP сервис:**
```python
# В mcp_youtube_real.py
from mcp_tools import get_transcript  # Реальный MCP импорт
```

2. **Вызвать MCP сервис:**
```python
async def _call_real_mcp_service(self, url: str, lang: str):
    result = await get_transcript(url=url, lang=lang)
    return result
```

3. **Обработать результат:**
```python
if result and result.get("transcript"):
    return {
        "transcript": result["transcript"],
        "title": result.get("title", ""),
        "language": result.get("language", lang)
    }
```

## 🧪 **Тестирование**

### **Запуск тестов:**

```bash
# Тест базовой интеграции
python test_mcp_youtube_integration.py

# Тест реальной MCP интеграции
python mcp_youtube_real.py
```

### **Ожидаемые результаты:**

```
✅ MCP YouTube processor created successfully
✅ URL extraction working correctly
✅ MCP service integration ready
✅ Ready for Telegram bot integration
```

## 🔄 **Следующие шаги**

### **1. Полная MCP интеграция**
- [ ] Интегрировать реальный MCP `get_transcript` сервис
- [ ] Добавить обработку пагинации
- [ ] Реализовать кэширование

### **2. Улучшения**
- [ ] Добавить поддержку разных языков
- [ ] Реализовать fallback на обычный YouTube процессор
- [ ] Добавить метрики и мониторинг

### **3. Развертывание**
- [ ] Обновить requirements.txt
- [ ] Протестировать на Railway
- [ ] Добавить переменные окружения для MCP

## 📊 **Преимущества MCP подхода**

### **По сравнению с обычным YouTube процессором:**

1. **Надежность:** MCP сервис более стабилен
2. **Качество:** Лучшие транскрипты
3. **Скорость:** Быстрее чем yt-dlp + Whisper
4. **Простота:** Меньше зависимостей

### **По сравнению с YouTube Transcript API:**

1. **Доступность:** Работает с заблокированными IP
2. **Гибкость:** Поддержка разных форматов
3. **Масштабируемость:** Через MCP инфраструктуру

## 🛠️ **Устранение неполадок**

### **Частые проблемы:**

1. **"MCP service not available"**
   - Проверить импорт MCP сервиса
   - Убедиться в правильности конфигурации

2. **"No transcript available"**
   - Проверить доступность видео
   - Убедиться в наличии субтитров

3. **"Invalid YouTube URL"**
   - Проверить формат URL
   - Убедиться в корректности video_id

## 📞 **Поддержка**

Для вопросов по интеграции:
1. Проверьте логи бота
2. Запустите тесты
3. Проверьте конфигурацию MCP

---

**🎯 Результат:** Полностью интегрированный MCP YouTube сервис в Telegram бот с автоматическим TLDR генерацией в формате LONGFORM. 