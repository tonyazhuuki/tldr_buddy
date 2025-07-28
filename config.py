"""
Configuration management for Telegram Voice-to-Insight Pipeline
Environment-based configuration with validation
"""

import os
from typing import Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class Config:
    """Application configuration"""
    
    # Required fields (no defaults) must come first
    telegram_token: str
    openai_api_key: str
    
    # Optional fields with defaults
    # Bot Configuration
    bot_name: str = "VoiceInsightBot"
    
    # OpenAI Configuration
    default_model: str = "o3"
    tone_model: str = "gpt-4o"
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    redis_max_memory: str = "256mb"
    
    # File Processing
    max_file_size: int = 52428800  # 50MB in bytes
    temp_dir: str = "temp"
    logs_dir: str = "logs"
    modes_dir: str = "modes"
    
    # Whisper Configuration (Legacy - for backward compatibility)
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    
    # OpenAI Whisper API Configuration
    whisper_api_model: str = "whisper-1"  # whisper-1|gpt-4o-transcribe
    whisper_api_timeout: int = 30
    whisper_api_max_retries: int = 3
    whisper_api_rate_limit: int = 50  # requests per minute
    
    # Speech Processing Configuration (Phase 2) - Updated for API
    whisper_compute_type: str = "int8"  # Legacy setting - not used with API
    whisper_cpu_threads: int = 4        # Legacy setting - not used with API
    whisper_num_workers: int = 1        # Legacy setting - not used with API
    
    # Audio Processing Settings
    max_audio_duration: int = 600  # 10 minutes
    chunk_size_mb: int = 32
    audio_cache_ttl: int = 3600  # 1 hour
    
    # Language Learning Settings  
    language_cache_ttl: int = 2592000  # 30 days
    language_confidence_threshold: float = 0.7
    
    # Performance Settings
    performance_target_seconds: float = 2.0  # ≤2s target
    enable_model_warming: bool = True
    enable_audio_caching: bool = True
    enable_user_learning: bool = True
    
    # Processing Limits
    default_ttl: int = 86400  # 24 hours
    max_processing_time: int = 30  # seconds
    max_text_length: int = 10000  # characters
    
    # Rate Limiting
    rate_limit_requests: int = 10  # per hour
    rate_limit_burst: int = 3
    admin_unlimited: bool = False
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Text Processing
    chunk_size: int = 3000
    chunk_overlap: int = 500
    language_threshold: float = 0.3  # Cyrillic ratio for Russian detection
    
    # Retry Configuration
    retry_base_delay: int = 1  # seconds
    retry_max_attempts: int = 3
    retry_jitter_percent: float = 0.3
    
    # Priority languages for speech processing (field with default_factory goes last)
    priority_languages: list = field(default_factory=lambda: ["ru", "en"])
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        self.validate()
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Create configuration from environment variables"""
        
        # Required environment variables
        telegram_token = os.getenv("TELEGRAM_TOKEN")
        if not telegram_token:
            raise ValueError("TELEGRAM_TOKEN environment variable is required")
        
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        return cls(
            # Required
            telegram_token=telegram_token,
            openai_api_key=openai_api_key,
            
            # Optional with defaults
            bot_name=os.getenv("BOT_NAME", "VoiceInsightBot"),
            default_model=os.getenv("DEFAULT_MODEL", "o3"),
            tone_model=os.getenv("TONE_MODEL", "gpt-4o"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
            redis_max_memory=os.getenv("REDIS_MAX_MEMORY", "256mb"),
            max_file_size=int(os.getenv("MAX_FILE_SIZE", "52428800")),
            temp_dir=os.getenv("TEMP_DIR", "temp"),
            logs_dir=os.getenv("LOGS_DIR", "logs"),
            modes_dir=os.getenv("MODES_DIR", "modes"),
            whisper_model=os.getenv("WHISPER_MODEL", "base"),
            whisper_device=os.getenv("WHISPER_DEVICE", "cpu"),
            whisper_api_model=os.getenv("WHISPER_API_MODEL", "whisper-1"),
            whisper_api_timeout=int(os.getenv("WHISPER_API_TIMEOUT", "30")),
            whisper_api_max_retries=int(os.getenv("WHISPER_API_MAX_RETRIES", "3")),
            whisper_api_rate_limit=int(os.getenv("WHISPER_API_RATE_LIMIT", "50")),
            whisper_compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "int8"),
            whisper_cpu_threads=int(os.getenv("WHISPER_CPU_THREADS", "4")),
            whisper_num_workers=int(os.getenv("WHISPER_NUM_WORKERS", "1")),
            priority_languages=os.getenv("PRIORITY_LANGUAGES", "ru,en").split(","),
            max_audio_duration=int(os.getenv("MAX_AUDIO_DURATION", "600")),
            chunk_size_mb=int(os.getenv("CHUNK_SIZE_MB", "32")),
            audio_cache_ttl=int(os.getenv("AUDIO_CACHE_TTL", "3600")),
            language_cache_ttl=int(os.getenv("LANGUAGE_CACHE_TTL", "2592000")),
            language_confidence_threshold=float(os.getenv("LANGUAGE_CONFIDENCE_THRESHOLD", "0.7")),
            performance_target_seconds=float(os.getenv("PERFORMANCE_TARGET_SECONDS", "2.0")),
            enable_model_warming=os.getenv("ENABLE_MODEL_WARMING", "true").lower() == "true",
            enable_audio_caching=os.getenv("ENABLE_AUDIO_CACHING", "true").lower() == "true",
            enable_user_learning=os.getenv("ENABLE_USER_LEARNING", "true").lower() == "true",
            default_ttl=int(os.getenv("DEFAULT_TTL", "86400")),
            max_processing_time=int(os.getenv("MAX_PROCESSING_TIME", "30")),
            max_text_length=int(os.getenv("MAX_TEXT_LENGTH", "10000")),
            rate_limit_requests=int(os.getenv("RATE_LIMIT_REQUESTS", "10")),
            rate_limit_burst=int(os.getenv("RATE_LIMIT_BURST", "3")),
            admin_unlimited=os.getenv("ADMIN_UNLIMITED", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_format=os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            chunk_size=int(os.getenv("CHUNK_SIZE", "3000")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "500")),
            language_threshold=float(os.getenv("LANGUAGE_THRESHOLD", "0.3")),
            retry_base_delay=int(os.getenv("RETRY_BASE_DELAY", "1")),
            retry_max_attempts=int(os.getenv("RETRY_MAX_ATTEMPTS", "3")),
            retry_jitter_percent=float(os.getenv("RETRY_JITTER_PERCENT", "0.3")),
        )
    
    def validate(self):
        """Validate configuration values"""
        errors = []
        
        # Validate required fields
        if not self.telegram_token:
            errors.append("telegram_token is required")
        
        if not self.openai_api_key:
            errors.append("openai_api_key is required")
        
        # Validate ranges
        if self.max_file_size <= 0:
            errors.append("max_file_size must be positive")
        
        if self.max_file_size > 52428800:  # 50MB Telegram limit
            errors.append("max_file_size cannot exceed 50MB (52428800 bytes)")
        
        if self.default_ttl <= 0:
            errors.append("default_ttl must be positive")
        
        if self.chunk_size <= 0:
            errors.append("chunk_size must be positive")
        
        if self.chunk_overlap < 0:
            errors.append("chunk_overlap cannot be negative")
        
        if self.chunk_overlap >= self.chunk_size:
            errors.append("chunk_overlap must be less than chunk_size")
        
        if not 0 <= self.language_threshold <= 1:
            errors.append("language_threshold must be between 0 and 1")
        
        if self.rate_limit_requests <= 0:
            errors.append("rate_limit_requests must be positive")
        
        if self.rate_limit_burst <= 0:
            errors.append("rate_limit_burst must be positive")
        
        if self.retry_max_attempts <= 0:
            errors.append("retry_max_attempts must be positive")
        
        if not 0 <= self.retry_jitter_percent <= 1:
            errors.append("retry_jitter_percent must be between 0 and 1")
        
        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_log_levels:
            errors.append(f"log_level must be one of: {', '.join(valid_log_levels)}")
        
        # Validate Whisper model (legacy)
        valid_whisper_models = ["tiny", "base", "small", "medium", "large"]
        if self.whisper_model not in valid_whisper_models:
            errors.append(f"whisper_model must be one of: {', '.join(valid_whisper_models)}")
        
        # Validate OpenAI Whisper API model
        valid_api_models = ["whisper-1", "gpt-4o-transcribe", "gpt-4o-mini-transcribe"]
        if self.whisper_api_model not in valid_api_models:
            errors.append(f"whisper_api_model must be one of: {', '.join(valid_api_models)}")
        
        # Validate API timeout and retries
        if self.whisper_api_timeout <= 0:
            errors.append("whisper_api_timeout must be positive")
        
        if self.whisper_api_max_retries <= 0:
            errors.append("whisper_api_max_retries must be positive")
        
        if self.whisper_api_rate_limit <= 0:
            errors.append("whisper_api_rate_limit must be positive")
        
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
    
    def get_openai_config(self, model: str) -> dict:
        """Get OpenAI API configuration for a specific model"""
        base_config = {
            "api_key": self.openai_api_key,
            "timeout": self.max_processing_time,
        }
        
        if model == "o3":
            return {
                **base_config,
                "max_tokens": 1000,
                "temperature": 0.3,
            }
        elif model == "gpt-4o":
            return {
                **base_config,
                "max_tokens": 500,
                "temperature": 0.7,
            }
        else:
            # Default configuration for custom models
            return {
                **base_config,
                "max_tokens": 1000,
                "temperature": 0.5,
            }
    
    def get_whisper_api_config(self) -> dict:
        """Get OpenAI Whisper API configuration"""
        return {
            "api_key": self.openai_api_key,
            "model": self.whisper_api_model,
            "timeout": self.whisper_api_timeout,
            "max_retries": self.whisper_api_max_retries,
            "rate_limit": self.whisper_api_rate_limit
        }
    
    def is_admin_mode(self) -> bool:
        """Check if admin mode is enabled"""
        return self.admin_unlimited
    
    def get_file_size_limit_mb(self) -> float:
        """Get file size limit in MB"""
        return self.max_file_size / (1024 * 1024)


# Global configuration instance
config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance"""
    global config
    if config is None:
        config = Config.from_env()
    return config


def reload_config():
    """Reload configuration from environment"""
    global config
    config = Config.from_env()


# Helper functions for common configuration access
def get_telegram_token() -> str:
    """Get Telegram bot token"""
    return get_config().telegram_token


def get_openai_api_key() -> str:
    """Get OpenAI API key"""
    return get_config().openai_api_key


def get_redis_url() -> str:
    """Get Redis connection URL"""
    return get_config().redis_url


def is_admin_mode() -> bool:
    """Check if admin mode is enabled"""
    return get_config().is_admin_mode() 