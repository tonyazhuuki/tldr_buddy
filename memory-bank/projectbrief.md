# TELEGRAM VOICE-TO-INSIGHT PIPELINE

## ПРОЕКТ: TELEGRAM КОНВЕЙЕР "ВОЙС → СМЫСЛ"

**Архитектор**: Продукт-архитектор  
**Цель**: По forwarded аудио/видео возвращать концентрат смысла с многоступенчатой LLM-обработкой  
**Создан**: ${new Date().toISOString()}

## CORE MISSION
Создать telegram-бота, который принимает forwarded голосовые/видео сообщения и возвращает структурированный анализ через pipeline из разных LLM моделей.

## TECHNICAL REQUIREMENTS

### Performance Targets
- **Latency**: ≤ 5 секунд на 60-секундное голосовое сообщение
- **Languages**: Русский + английский (приоритет), остальные языки pass-through
- **Data Retention**: Текст хранится ≤ 24 часа, затем автоматическая очистка

### Technology Stack
- **Runtime**: Python 3.11
- **Bot Framework**: aiogram 3
- **Speech Recognition**: faster-whisper
- **LLM Integration**: OpenAI Chat API
- **Deployment**: Docker Compose
- **Configuration**: .env для API ключей

## PIPELINE ARCHITECTURE

### Hard-wired Flow
1. **INPUT**: Voice/Video message forwarded в чат
2. **WHISPER-ASR**: Конвертация в текст
3. **PROCESSOR(mode=DEFAULT)**: 
   - Summary (1-2 строки)
   - 3-5 BULLETS "о чём говорит"
   - ACTION POINTS (если необходимы)
4. **TONE_SCAN(mode=TONE)**: 
   - Hidden intent анализ
   - Dominant emotion определение
   - Preferred interaction style
5. **OUTPUT**: Структурированный ответ бота

### Model Split (Default Configuration)
- **DEFAULT-процессор**: o3 model
- **TONE-процессор**: gpt-4o model

## MODE REGISTRY SYSTEM

### Base Configuration
```json
{
  "DEFAULT": {
    "prompt": "Проанализируй текст и верни краткое резюме, основные пункты и действия",
    "model": "o3"
  },
  "TONE": {
    "prompt": "Определи скрытые намерения, доминирующие эмоции и стиль взаимодействия",
    "model": "gpt-4o"
  }
}
```

### Custom Mode Management
- **Добавление**: `/set_model <name> <gpt-id>`
- **Просмотр**: `/list_modes` - показывает таблицу name | model | tokens_used

## OUTPUT FORMAT
```
📝 [Summary в 1-2 строки]
• [Bullet point 1]
• [Bullet point 2] 
• [Bullet point 3-5]
👉 [Action points если есть]
🎭 [Tone analysis: intent/emotion/style]
```

## SYSTEM CONSTRAINTS
- Максимальная производительность при минимальной латентности
- Модульная архитектура для легкого добавления новых режимов
- Безопасное хранение API ключей
- Автоматическая очистка данных для privacy compliance 