# 🎥 YouTube Integration Setup Guide

## 📋 Обзор архитектуры

Реализована надежная система обработки YouTube видео с двухконтурным подходом:

### 🔄 **Двухконтурный фетчер (Router)**

#### **Контур A: Облачный воркер (по умолчанию)**
- **YouTube Transcript API** - быстрый доступ к субтитрам
- **yt-dlp** - загрузка видео для обработки через Whisper
- **Railway/Cloudflare** - текущая инфраструктура

#### **Контур B: Резиденциальный выход (fallback)**
- **Прокси-сервисы** - обход блокировок IP
- **VPS у "полурозничного" провайдера** - не hyperscaler
- **Домашний/офисный мини-воркер** - Raspberry Pi + Tailscale

### 🎯 **Логика роутинга**
```
YouTube URL → Проверка кэша → Контур A → 403/429/blocked → Контур B → Результат
```

## 🛠️ Настройка компонентов

### 1. **YouTube Data API v3 (Метаданные)**

#### Получение API ключа:
1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Включите YouTube Data API v3
4. Создайте учетные данные (API ключ)
5. Добавьте ключ в переменные окружения:

```bash
YOUTUBE_API_KEY=your_api_key_here
```

#### Квоты и лимиты:
- **10,000 единиц в день** (бесплатно)
- **1 запрос в секунду** (rate limiting)
- **Кэширование 1 час** (автоматическое)

### 2. **Контур A: Облачный воркер**

#### Установка зависимостей:
```bash
pip install youtube-transcript-api yt-dlp requests
```

#### Настройка в Railway:
```env
YOUTUBE_API_KEY=your_api_key
TLDRBUDDY_ENABLED=true
```

### 3. **Контур B: Резиденциальный выход**

#### Вариант 1: Прокси-сервис
```env
RESIDENTIAL_PROXY=http://username:password@proxy.example.com:8080
```

#### Вариант 2: VPS у полурозничного провайдера
- **Hetzner** (Германия)
- **OVH** (Франция)
- **Linode** (различные локации)

#### Вариант 3: Домашний мини-воркер
```bash
# На Raspberry Pi или мини-ПК
pip install youtube-transcript-api yt-dlp
# Настройка Tailscale/ZeroTier для доступа
```

## 🔧 Конфигурация

### Переменные окружения:

```env
# YouTube Data API v3
YOUTUBE_API_KEY=your_api_key_here

# Прокси для обхода блокировок
RESIDENTIAL_PROXY=http://username:password@proxy.example.com:8080
CLOUD_PROXY=http://cloud-proxy.example.com:8080

# Настройки фетчера
YOUTUBE_MAX_RETRIES=3
YOUTUBE_BACKOFF_BASE=2.0
YOUTUBE_CACHE_TTL=3600

# Включение функций
TLDRBUDDY_ENABLED=true
```

### Настройки троттлинга:

```python
# В youtube_dual_fetcher.py
max_retries = 3          # Максимум попыток
backoff_base = 2.0       # Экспоненциальный backoff
cache_ttl = 3600         # Кэш на 1 час
```

## 📊 Мониторинг и статистика

### Метрики системы:
- **Circuit A usage** - использование облачного контура
- **Circuit B usage** - использование резиденциального контура
- **Cache hits** - попадания в кэш
- **Failure rates** - частота ошибок по контурам
- **Processing times** - время обработки

### Команды для мониторинга:
```python
# Получить статистику
stats = processor.get_processing_stats()
print(stats)

# Проверить доступность контуров
print(f"Circuit A: {processor.dual_fetcher.circuit_a_available}")
print(f"Circuit B: {processor.dual_fetcher.circuit_b_available}")
```

## 🚀 Развертывание

### 1. **Локальная разработка:**
```bash
# Установка зависимостей
pip install -r requirements-railway.txt

# Настройка переменных окружения
export YOUTUBE_API_KEY=your_key
export RESIDENTIAL_PROXY=your_proxy

# Тестирование
python test_youtube_integrated.py
```

### 2. **Railway развертывание:**
```bash
# Добавить переменные в Railway Dashboard
YOUTUBE_API_KEY=your_key
RESIDENTIAL_PROXY=your_proxy
TLDRBUDDY_ENABLED=true

# Деплой
git push origin main
```

### 3. **Настройка резервного контура:**
```bash
# На VPS или домашнем сервере
git clone your_repo
pip install -r requirements-railway.txt
# Настройка Tailscale/ZeroTier
# Запуск как сервис
```

## 🔍 Диагностика проблем

### Проблема: YouTube блокирует запросы
```
Ошибка: YouTube is blocking requests from your IP
```

**Решение:**
1. Проверить настройки прокси
2. Включить Circuit B (резиденциальный выход)
3. Использовать VPS у полурозничного провайдера

### Проблема: Превышена квота API
```
Ошибка: YouTube API quota exceeded
```

**Решение:**
1. Проверить использование квоты в Google Cloud Console
2. Увеличить лимиты (платно)
3. Оптимизировать кэширование

### Проблема: Медленная обработка
```
Время обработки: >30 секунд
```

**Решение:**
1. Проверить настройки кэша
2. Оптимизировать размер загружаемых видео
3. Использовать более быстрые прокси

## 📈 Оптимизация производительности

### Кэширование:
- **Метаданные**: 1 час (YouTube Data API)
- **Контент**: 1 час (транскрипты/видео)
- **Результаты**: 24 часа (TLDR)

### Троттлинг:
- **Rate limiting**: 1 запрос/секунду
- **Exponential backoff**: 2^n секунд
- **Jitter**: ±10% для избежания thundering herd

### Параллельная обработка:
- **Метаданные** и **контент** загружаются параллельно
- **Кэш-проверка** выполняется первой
- **Fallback** на Circuit B при ошибках

## 🎯 Результат

После настройки система обеспечивает:

✅ **Надежность**: Двухконтурный подход с автоматическим failover  
✅ **Скорость**: Кэширование и оптимизированная обработка  
✅ **Качество**: Официальные субтитры + Whisper для точности  
✅ **Масштабируемость**: Поддержка высоких нагрузок  
✅ **Мониторинг**: Детальная статистика и диагностика  

**Готово к продакшену!** 🚀 