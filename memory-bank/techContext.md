# TECHNICAL CONTEXT: TELEGRAM VOICE-TO-INSIGHT PIPELINE

## АРХИТЕКТУРНЫЙ OVERVIEW

### System Architecture Diagram
```
[Telegram Bot] → [Voice Processor] → [Multi-LLM Pipeline] → [Formatted Response]
     ↓                   ↓                    ↓                     ↓
[aiogram 3]      [faster-whisper]    [OpenAI API Router]    [Structured Output]
```

## CORE COMPONENTS

### 1. BOT LAYER (aiogram 3)
```python
# Primary responsibilities:
- Message handling and routing
- File download and preprocessing  
- Response formatting and sending
- Command processing (/set_model, /list_modes)
- Rate limiting and error handling
```

### 2. SPEECH PROCESSING LAYER (faster-whisper)
```python
# Technical specifications:
- Model: faster-whisper (optimized for speed)
- Languages: ru, en (primary), auto-detect for others
- Output: Plain text with timestamps
- Performance target: <2s for 60s audio
- Fallback: If whisper fails, return error message
```

### 3. LLM PIPELINE LAYER
```python
# Multi-model routing system:
class LLMRouter:
    def __init__(self):
        self.mode_registry = {
            "DEFAULT": {"model": "o3", "prompt": "..."},
            "TONE": {"model": "gpt-4o", "prompt": "..."}
        }
    
    async def process_parallel(self, text: str):
        # Run DEFAULT and TONE processing simultaneously
        default_task = self.process_mode(text, "DEFAULT")
        tone_task = self.process_mode(text, "TONE")
        return await asyncio.gather(default_task, tone_task)
```

### 4. DATA MANAGEMENT LAYER
```python
# Temporary storage with TTL:
- Redis/In-memory cache for 24h retention
- Automatic cleanup with background tasks
- No persistent storage for privacy
- Token usage tracking per mode
```

## API INTEGRATION SPECS

### OpenAI API Configuration
```python
OPENAI_CONFIG = {
    "o3": {
        "max_tokens": 1000,
        "temperature": 0.3,
        "timeout": 10
    },
    "gpt-4o": {
        "max_tokens": 500,  
        "temperature": 0.7,
        "timeout": 8
    }
}
```

### Model Prompt Templates
```python
PROMPTS = {
    "DEFAULT": """
    Проанализируй следующий текст и верни результат в формате:
    
    РЕЗЮМЕ: [1-2 предложения]
    ОСНОВНЫЕ ПУНКТЫ:
    • [пункт 1]
    • [пункт 2] 
    • [пункт 3-5]
    ДЕЙСТВИЯ: [если есть конкретные действия]
    
    Текст: {text}
    """,
    
    "TONE": """
    Определи психологические характеристики следующего текста:
    
    СКРЫТЫЕ НАМЕРЕНИЯ: [что на самом деле хочет автор]
    ДОМИНИРУЮЩАЯ ЭМОЦИЯ: [основная эмоция]
    СТИЛЬ ВЗАИМОДЕЙСТВИЯ: [как лучше отвечать этому человеку]
    
    Текст: {text}
    """
}
```

## PERFORMANCE OPTIMIZATION

### Async Pipeline Design
```python
async def process_voice_message(file_path: str) -> str:
    # Step 1: Speech-to-text (2s max)
    text = await whisper_transcribe(file_path)
    
    # Step 2: Parallel LLM processing (3s max)
    default_result, tone_result = await asyncio.gather(
        llm_process(text, "DEFAULT"),
        llm_process(text, "TONE")
    )
    
    # Step 3: Format response (<0.5s)
    return format_response(default_result, tone_result)
```

### Caching Strategy
```python
# Cache frequently used models and results
- Model response caching (1h TTL)
- Whisper model preloading
- Connection pooling for OpenAI API
```

## DOCKER ARCHITECTURE

### Multi-container Setup
```yaml
version: '3.8'
services:
  telegram-bot:
    build: .
    environment:
      - TELEGRAM_TOKEN=${TELEGRAM_TOKEN}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./temp:/app/temp
    depends_on:
      - redis
      
  redis:
    image: redis:alpine
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    
  cleanup-worker:
    build: .
    command: python cleanup_worker.py
    environment:
      - CLEANUP_INTERVAL=3600  # 1 hour
```

## SECURITY & PRIVACY

### Data Protection
```python
# Privacy-first design:
- No permanent text storage
- API keys in encrypted .env
- Temporary files auto-cleanup
- No user data logging
- Anonymous usage analytics only
```

### Error Handling
```python
# Robust error management:
- Graceful OpenAI API failures
- Whisper processing fallbacks  
- Rate limiting with exponential backoff
- User-friendly error messages
```

## MONITORING & METRICS

### Performance Tracking
```python
METRICS = {
    "processing_time": "histogram",
    "tokens_used_per_mode": "counter", 
    "error_rate": "gauge",
    "active_users": "gauge"
}
```

### Health Checks
```python
# System health endpoints:
- /health - overall system status
- /metrics - prometheus metrics
- /modes - current mode configuration
```

## EXTENSIBILITY FRAMEWORK

### Custom Mode Plugin System
```python
class CustomModePlugin:
    def __init__(self, name: str, model: str, prompt: str):
        self.name = name
        self.model = model  
        self.prompt = prompt
        
    def validate(self) -> bool:
        # Validate model exists in OpenAI
        # Validate prompt format
        return True
        
    def register(self):
        # Add to mode registry
        # Update configuration
        pass
```

### Mode Registry Management
```python
# Dynamic mode management:
- Hot-reload configuration changes
- Validate new models before activation
- Rollback mechanism for failed modes
- Usage statistics per custom mode
``` 