# SYSTEM PATTERNS: TELEGRAM VOICE-TO-INSIGHT PIPELINE

## ARCHITECTURAL PATTERNS

### 🏗️ PIPELINE PATTERN
```python
# Multi-stage async pipeline with parallel processing
class VoiceInsightPipeline:
    async def process(self, voice_message):
        # Stage 1: Speech Recognition (2s max)
        text = await self.whisper_stage(voice_message)
        
        # Stage 2: Parallel LLM Processing (3s max)
        default_result, tone_result = await asyncio.gather(
            self.default_processor(text),
            self.tone_processor(text)
        )
        
        # Stage 3: Response Formatting (<0.5s)
        return self.format_response(default_result, tone_result)
```

### 🔌 PLUGIN ARCHITECTURE PATTERN
```python
# Mode Registry with Hot-reload capability
class ModeRegistry:
    def __init__(self):
        self.modes = {
            "DEFAULT": {"model": "o3", "prompt": "..."},
            "TONE": {"model": "gpt-4o", "prompt": "..."}
        }
    
    def register_mode(self, name: str, config: dict):
        if self.validate_mode(config):
            self.modes[name] = config
            self.hot_reload()
    
    def validate_mode(self, config: dict) -> bool:
        # Validate model exists, prompt format, etc.
        return True
```

### ⚡ CIRCUIT BREAKER PATTERN
```python
# Resilient API calls with circuit breaker
class OpenAICircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call_api(self, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenError()
        
        try:
            result = await self.openai_client.chat.completions.create(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                self.last_failure_time = time.time()
            raise e
```

## DATA FLOW PATTERNS

### 📊 CACHING STRATEGY
```python
# Multi-tier caching with TTL
class CacheManager:
    def __init__(self):
        self.l1_cache = {}  # In-memory
        self.l2_cache = redis.Redis()  # Redis
        self.ttl = 24 * 3600  # 24 hours
    
    async def get(self, key: str):
        # L1 cache check
        if key in self.l1_cache:
            return self.l1_cache[key]
        
        # L2 cache check  
        result = await self.l2_cache.get(key)
        if result:
            self.l1_cache[key] = result
            return result
        
        return None
    
    async def set(self, key: str, value: any):
        self.l1_cache[key] = value
        await self.l2_cache.setex(key, self.ttl, value)
```

### 🔄 RETRY PATTERN
```python
# Exponential backoff with jitter
async def retry_with_backoff(func, max_retries=3, base_delay=1):
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            
            # Exponential backoff with jitter
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            await asyncio.sleep(delay)
```

## SECURITY PATTERNS

### 🔐 PRIVACY-FIRST DESIGN
```python
# Automatic data cleanup with TTL
class PrivacyManager:
    def __init__(self):
        self.cleanup_scheduler = BackgroundScheduler()
        self.cleanup_scheduler.add_job(
            self.cleanup_expired_data,
            'interval',
            hours=1
        )
    
    async def store_temporary(self, data: str, ttl: int = 86400):
        key = self.generate_key()
        expiry = time.time() + ttl
        
        await self.redis.setex(key, ttl, data)
        await self.redis.setex(f"{key}:expiry", ttl, expiry)
        
        return key
    
    async def cleanup_expired_data(self):
        # Remove all expired entries
        current_time = time.time()
        for key in await self.redis.scan_iter(match="*:expiry"):
            expiry_time = await self.redis.get(key)
            if current_time > float(expiry_time):
                data_key = key.replace(":expiry", "")
                await self.redis.delete(key, data_key)
```

### 🛡️ RATE LIMITING PATTERN
```python
# Token bucket algorithm for fair usage
class RateLimiter:
    def __init__(self, max_tokens=10, refill_rate=1):
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.tokens = max_tokens
        self.last_refill = time.time()
    
    def is_allowed(self, user_id: str) -> bool:
        current_time = time.time()
        
        # Refill tokens based on time elapsed
        elapsed = current_time - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
        self.last_refill = current_time
        
        # Check if request is allowed
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        
        return False
```

## ERROR HANDLING PATTERNS

### 🚨 GRACEFUL DEGRADATION
```python
# Fallback mechanisms for service failures
class ServiceHandler:
    async def process_with_fallback(self, text: str):
        try:
            # Primary: Try o3 model
            return await self.openai_api.process(text, model="o3")
        except OpenAIAPIError:
            try:
                # Fallback 1: Try gpt-4o
                return await self.openai_api.process(text, model="gpt-4o")
            except OpenAIAPIError:
                try:
                    # Fallback 2: Try gpt-3.5-turbo
                    return await self.openai_api.process(text, model="gpt-3.5-turbo")
                except OpenAIAPIError:
                    # Final fallback: Simple template response
                    return self.generate_template_response(text)
```

### 📝 ERROR CLASSIFICATION
```python
# Structured error handling
class ErrorHandler:
    ERROR_TYPES = {
        "WHISPER_TRANSCRIPTION_FAILED": {
            "message": "🎙️ Не удалось распознать речь. Попробуйте другой файл.",
            "retry": False,
            "log_level": "WARNING"
        },
        "OPENAI_RATE_LIMIT": {
            "message": "⏳ Сервис временно перегружен. Попробуйте через минуту.",
            "retry": True,
            "log_level": "INFO"
        },
        "OPENAI_API_ERROR": {
            "message": "🤖 Ошибка обработки текста. Повторяю попытку...",
            "retry": True,
            "log_level": "ERROR"
        },
        "FILE_TOO_LARGE": {
            "message": "📁 Файл слишком большой. Максимум 50MB.",
            "retry": False,
            "log_level": "INFO"
        }
    }
    
    def handle_error(self, error_type: str, context: dict = None):
        config = self.ERROR_TYPES.get(error_type)
        if config:
            self.log(config["log_level"], error_type, context)
            return config["message"], config["retry"]
        
        return "❌ Произошла неизвестная ошибка.", False
```

## PERFORMANCE PATTERNS

### ⚡ ASYNC OPTIMIZATION
```python
# Concurrent processing with resource limits
class AsyncProcessor:
    def __init__(self, max_concurrent=5):
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_batch(self, tasks: List[Callable]):
        async def limited_task(task):
            async with self.semaphore:
                return await task()
        
        # Process all tasks concurrently with limit
        results = await asyncio.gather(
            *[limited_task(task) for task in tasks],
            return_exceptions=True
        )
        
        return results
```

### 🗂️ MEMORY MANAGEMENT
```python
# Efficient memory usage for large files
class MemoryOptimizer:
    def __init__(self, max_memory_mb=512):
        self.max_memory = max_memory_mb * 1024 * 1024
    
    async def process_large_audio(self, file_path: str):
        file_size = os.path.getsize(file_path)
        
        if file_size > self.max_memory:
            # Stream processing for large files
            return await self.stream_process(file_path)
        else:
            # In-memory processing for small files
            return await self.memory_process(file_path)
    
    async def stream_process(self, file_path: str):
        # Process audio in chunks to minimize memory usage
        chunk_size = self.max_memory // 4
        results = []
        
        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                result = await self.process_chunk(chunk)
                results.append(result)
        
        return self.merge_results(results)
```

## MONITORING PATTERNS

### 📊 METRICS COLLECTION
```python
# Prometheus-style metrics
class MetricsCollector:
    def __init__(self):
        self.counters = defaultdict(int)
        self.histograms = defaultdict(list)
        self.gauges = defaultdict(float)
    
    def increment(self, metric: str, labels: dict = None):
        key = self.build_key(metric, labels)
        self.counters[key] += 1
    
    def observe(self, metric: str, value: float, labels: dict = None):
        key = self.build_key(metric, labels)
        self.histograms[key].append(value)
    
    def set_gauge(self, metric: str, value: float, labels: dict = None):
        key = self.build_key(metric, labels)
        self.gauges[key] = value
    
    def get_metrics(self) -> dict:
        return {
            "counters": dict(self.counters),
            "histograms": {k: {
                "count": len(v),
                "sum": sum(v),
                "avg": sum(v) / len(v) if v else 0,
                "p95": self.percentile(v, 0.95) if v else 0
            } for k, v in self.histograms.items()},
            "gauges": dict(self.gauges)
        }
```

### 🏥 HEALTH CHECKS
```python
# Comprehensive health monitoring
class HealthChecker:
    async def check_system_health(self) -> dict:
        checks = {
            "redis": await self.check_redis(),
            "openai_api": await self.check_openai(),
            "whisper": await self.check_whisper(),
            "disk_space": await self.check_disk_space(),
            "memory": await self.check_memory()
        }
        
        overall_status = "healthy" if all(
            check["status"] == "ok" for check in checks.values()
        ) else "unhealthy"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks
        }
    
    async def check_redis(self) -> dict:
        try:
            await self.redis.ping()
            return {"status": "ok", "message": "Redis connection healthy"}
        except Exception as e:
            return {"status": "error", "message": f"Redis error: {str(e)}"}
```

## CONFIGURATION PATTERNS

### ⚙️ ENVIRONMENT-BASED CONFIG
```python
# Flexible configuration management
class Config:
    def __init__(self):
        self.telegram_token = os.getenv("TELEGRAM_TOKEN")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.max_file_size = int(os.getenv("MAX_FILE_SIZE", "52428800"))  # 50MB
        self.whisper_model = os.getenv("WHISPER_MODEL", "base")
        self.default_ttl = int(os.getenv("DEFAULT_TTL", "86400"))  # 24h
        
    def validate(self):
        required = ["telegram_token", "openai_api_key"]
        missing = [key for key in required if not getattr(self, key)]
        
        if missing:
            raise ValueError(f"Missing required config: {missing}")
```

## TESTING PATTERNS

### 🧪 MOCK SERVICES
```python
# Mock external services for testing
class MockOpenAI:
    async def chat_completions_create(self, **kwargs):
        # Return predictable test responses
        model = kwargs.get("model", "gpt-3.5-turbo")
        messages = kwargs.get("messages", [])
        
        if model == "o3":
            return MockResponse("РЕЗЮМЕ: Test summary\n• Test bullet")
        elif model == "gpt-4o":
            return MockResponse("ЭМОЦИЯ: neutral\nСТИЛЬ: formal")

class MockWhisper:
    async def transcribe(self, audio_file):
        return MockTranscription("This is a test transcription.")
```

Эти паттерны обеспечивают:
- **Масштабируемость**: Async processing, circuit breakers
- **Надёжность**: Retry logic, graceful degradation  
- **Безопасность**: Privacy-first design, rate limiting
- **Производительность**: Multi-tier caching, memory optimization
- **Мониторинг**: Comprehensive metrics and health checks 