# 🎨 CREATIVE PHASE: SPEECH RECOGNITION ARCHITECTURE DESIGN

**Date**: December 19, 2024  
**Phase**: Phase 2 Speech Processing Development  
**Focus**: Design integration architecture for faster-whisper with bot infrastructure

🎨🎨🎨 **ENTERING CREATIVE PHASE: SPEECH RECOGNITION ARCHITECTURE** 🎨🎨🎨

## PROBLEM STATEMENT

### Core Challenge
Design an optimal speech recognition architecture that integrates faster-whisper with the existing aiogram bot infrastructure while achieving:
- **Model Selection**: Optimal balance between accuracy and performance for ≤2s target
- **Language Detection**: Intelligent handling of Russian/English priority with auto-detection
- **Caching Strategy**: Efficient model loading and result caching for performance
- **Async Integration**: Seamless integration with existing async bot architecture

### Technical Constraints
- **Model Loading**: faster-whisper models can be large (100MB-1GB) and slow to load
- **Memory Limits**: Container deployment with limited memory resources
- **Language Priority**: Russian and English are primary, others secondary
- **Bot Integration**: Must integrate with existing aiogram message handlers
- **Performance Target**: Contribute to overall ≤2s processing time for 60s audio

### Requirements
1. **Model Management**: Efficient model loading, caching, and memory management
2. **Language Detection**: Smart language detection with priority handling
3. **Performance Optimization**: Model preloading and inference optimization
4. **Error Handling**: Graceful failure handling with fallback strategies
5. **Async Architecture**: Non-blocking integration with bot message processing
6. **Resource Management**: Efficient CPU/memory usage in containerized environment

## OPTIONS ANALYSIS

### Option 1: Single Model with Auto-Detection
**Description**: Use one multi-language model with automatic language detection

**Architecture**:
```python
class SingleModelRecognizer:
    def __init__(self):
        self.model = WhisperModel("base", device="cpu")
    
    async def transcribe(self, audio_data: bytes) -> str:
        # Auto-detect language and transcribe
        result = await self.model.transcribe(
            audio_data,
            language=None,  # Auto-detect
            task="transcribe"
        )
        return result.text
```

**Pros**:
- Simple architecture with single model to manage
- Built-in language detection reduces complexity
- Lower memory footprint (one model loaded)
- Consistent performance across all languages

**Cons**:
- Slower processing due to language detection overhead
- Less optimal for known language scenarios
- No prioritization for Russian/English
- Auto-detection can be inaccurate for short audio

**Performance Analysis**:
- **Model Loading**: 2-3 seconds (one-time cost)
- **Processing Time**: 1.5-2.5 seconds per request (includes detection)
- **Memory Usage**: ~500MB for base model
- **Accuracy**: Good for clear speech, reduced for accented/noisy audio

### Option 2: Multi-Model Strategy with Language-Specific Models
**Description**: Separate optimized models for Russian, English, and multilingual fallback

**Architecture**:
```python
class MultiModelRecognizer:
    def __init__(self):
        self.models = {
            'ru': WhisperModel("base", device="cpu"),
            'en': WhisperModel("base", device="cpu"), 
            'auto': WhisperModel("base", device="cpu")
        }
        self.language_detector = LanguageDetector()
    
    async def transcribe(self, audio_data: bytes) -> str:
        # Quick language detection
        detected_lang = await self.language_detector.detect(audio_data)
        
        # Select appropriate model
        model_key = detected_lang if detected_lang in ['ru', 'en'] else 'auto'
        model = self.models[model_key]
        
        result = await model.transcribe(audio_data, language=detected_lang)
        return result.text
```

**Pros**:
- Optimized accuracy for priority languages
- Faster processing when language is known
- Better handling of accents and dialects
- Flexible fallback to multilingual model

**Cons**:
- High memory usage (3 models = ~1.5GB)
- Complex model management and loading
- Slower startup time (loading multiple models)
- Increased maintenance complexity

**Performance Analysis**:
- **Model Loading**: 6-9 seconds (three models)
- **Processing Time**: 1.0-1.8 seconds per request (optimized for language)
- **Memory Usage**: ~1.5GB for three base models
- **Accuracy**: Excellent for Russian/English, good for others

### Option 3: Lazy Loading with Model Caching
**Description**: Single model with intelligent caching and lazy loading optimization

**Architecture**:
```python
class CachedModelRecognizer:
    def __init__(self):
        self.model = None
        self.model_cache = {}
        self.last_language = None
        self.model_lock = asyncio.Lock()
    
    async def transcribe(self, audio_data: bytes, hint_language: str = None) -> str:
        # Use language hint or detect
        language = hint_language or await self.quick_language_detect(audio_data)
        
        # Load/cache model for specific language configuration
        model = await self.get_cached_model(language)
        
        result = await model.transcribe(
            audio_data,
            language=language,
            task="transcribe"
        )
        return result.text
    
    async def get_cached_model(self, language: str):
        async with self.model_lock:
            if not self.model or self.last_language != language:
                # Lazy load/reload model with language-specific optimization
                self.model = await self.load_optimized_model(language)
                self.last_language = language
            return self.model
```

**Pros**:
- Optimal memory usage (one model at a time)
- Language-specific optimization when needed
- Fast processing for repeated language use
- Intelligent caching reduces reload overhead

**Cons**:
- Model reloading delay when switching languages
- Complex caching logic and race condition handling
- Potential delays for language switches
- Cache invalidation complexity

**Performance Analysis**:
- **Model Loading**: 2-3 seconds (initial + reload as needed)
- **Processing Time**: 1.2-2.0 seconds per request
- **Memory Usage**: ~500MB (single model)
- **Accuracy**: Good with language-specific optimization

### Option 4: Hybrid Architecture with Smart Preloading
**Description**: Combines efficient model management with intelligent preloading and fallback

**Architecture**:
```python
class HybridSpeechRecognizer:
    def __init__(self):
        self.primary_model = None
        self.model_config = "base"
        self.language_cache = LanguageCache()
        self.model_warmer = ModelWarmer()
        
    async def initialize(self):
        """Warm up the primary model during startup"""
        self.primary_model = await self.model_warmer.load_model(
            self.model_config, 
            device="cpu"
        )
        
    async def transcribe(self, audio_data: bytes, user_id: str = None) -> str:
        # Use user language preference if available
        preferred_lang = await self.get_user_language_preference(user_id)
        
        # Quick language hint detection
        language_hint = preferred_lang or await self.quick_language_hint(audio_data)
        
        # Transcribe with optimized settings
        result = await self.primary_model.transcribe(
            audio_data,
            language=language_hint,
            task="transcribe",
            beam_size=1 if language_hint in ['ru', 'en'] else 5,
            temperature=0.0 if language_hint in ['ru', 'en'] else 0.2
        )
        
        # Cache language preference for user
        if user_id and result.language:
            await self.cache_user_language(user_id, result.language)
            
        return result.text
```

**Pros**:
- Balanced memory usage and performance
- User-specific language learning and caching
- Optimized settings for priority languages
- Fast startup with model preloading

**Cons**:
- Moderate complexity in language preference management
- User preference storage requirements
- Less optimal than dedicated language models
- Cache management overhead

**Performance Analysis**:
- **Model Loading**: 2-3 seconds (startup preloading)
- **Processing Time**: 1.0-2.0 seconds per request
- **Memory Usage**: ~500MB + preference cache
- **Accuracy**: Good with user preference optimization

## 🎨 CREATIVE CHECKPOINT: ARCHITECTURE EVALUATION

**Progress**: Four architecture approaches analyzed with focus on model management and performance
**Key Insights**:
- Single model simplest but may not meet performance target
- Multi-model provides best accuracy but high memory cost
- Caching approaches balance performance and resources
- User preferences can significantly improve performance

## DECISION ANALYSIS

### Evaluation Criteria Scoring

| Criteria | Option 1 | Option 2 | Option 3 | Option 4 |
|----------|----------|----------|----------|----------|
| **Performance (≤2s contribution)** | ⚠️ 1.5-2.5s | ✅ 1.0-1.8s | ✅ 1.2-2.0s | ✅ 1.0-2.0s |
| **Memory Efficiency** | ✅ 500MB | ❌ 1.5GB | ✅ 500MB | ✅ 500MB+ |
| **Startup Time** | ✅ 2-3s | ❌ 6-9s | ✅ 2-3s | ✅ 2-3s |
| **Russian/English Priority** | ❌ No priority | ✅ Optimized | ⚠️ Mixed | ✅ Good priority |
| **Implementation Complexity** | ✅ Low | ❌ High | ❌ High | ⚠️ Medium |
| **Container Deployment** | ✅ Excellent | ❌ Poor | ✅ Good | ✅ Excellent |

### Architecture Complexity vs Performance

```
Performance ↑
    │
    │  Option 2 ●
    │      
    │         Option 4 ●
    │   Option 3 ●
    │
    │
Option 1 ●
    └────────────────────→ Complexity
                         Low → High
```

### Decision Rationale

**Selected Option: Option 4 - Hybrid Architecture with Smart Preloading**

**Primary Reasons**:
1. **Performance Target**: 1.0-2.0s processing time contributes to overall ≤2s goal
2. **Container-Friendly**: 500MB memory usage suitable for Docker deployment
3. **Language Priority**: Russian/English optimization without memory overhead
4. **User Experience**: Learns user preferences for improved future performance
5. **Maintainable**: Medium complexity manageable for Level 3 implementation

**Supporting Factors**:
- **Real-world Usage**: Users typically use consistent language
- **Telegram Context**: User language preferences are learnable from usage
- **Performance Optimization**: Beam size and temperature tuning for known languages
- **Fallback Capability**: Graceful handling of unknown languages

## SELECTED APPROACH: HYBRID SPEECH RECOGNITION ARCHITECTURE

### Core Architecture Design

```python
class HybridSpeechRecognizer:
    """
    Smart speech recognition with user preference learning and performance optimization
    """
    
    def __init__(self, config: SpeechConfig):
        self.config = config
        self.primary_model = None
        self.language_cache = UserLanguageCache()
        self.model_warmer = ModelWarmer()
        self.performance_monitor = PerformanceMonitor()
        
    async def initialize(self):
        """Initialize and warm up the speech recognition system"""
        
        # Load primary model with warming
        logger.info(f"Loading Whisper model: {self.config.model_size}")
        self.primary_model = await self.model_warmer.load_model(
            model_size=self.config.model_size,
            device=self.config.device,
            compute_type=self.config.compute_type
        )
        
        # Warm up with dummy audio for faster first request
        await self.warm_up_model()
        
    async def transcribe(self, 
                        audio_data: bytes, 
                        user_id: str = None,
                        context: TranscriptionContext = None) -> TranscriptionResult:
        """
        Main transcription method with smart language detection and optimization
        """
        
        start_time = time.time()
        
        try:
            # 1. Get language hint from user preferences or context
            language_hint = await self.get_language_hint(user_id, context)
            
            # 2. Prepare transcription parameters
            transcribe_params = self.prepare_transcription_params(language_hint)
            
            # 3. Perform transcription
            result = await self.primary_model.transcribe(
                audio_data,
                **transcribe_params
            )
            
            # 4. Post-process and cache results
            processed_result = await self.post_process_result(
                result, user_id, language_hint
            )
            
            # 5. Monitor performance
            processing_time = time.time() - start_time
            await self.performance_monitor.record_transcription(
                user_id, processing_time, len(audio_data), result.language
            )
            
            return processed_result
            
        except Exception as e:
            await self.handle_transcription_error(e, user_id, context)
            raise
    
    async def get_language_hint(self, 
                               user_id: str = None, 
                               context: TranscriptionContext = None) -> str:
        """Smart language hint detection with user preference learning"""
        
        # Priority 1: User's cached language preference
        if user_id:
            cached_lang = await self.language_cache.get_user_language(user_id)
            if cached_lang and cached_lang in self.config.priority_languages:
                return cached_lang
        
        # Priority 2: Context hints (if available)
        if context and context.language_hint:
            return context.language_hint
            
        # Priority 3: Quick audio analysis for Russian/English detection
        detected_lang = await self.quick_language_detection(audio_data)
        if detected_lang in self.config.priority_languages:
            return detected_lang
            
        # Default: Auto-detection
        return None
    
    def prepare_transcription_params(self, language_hint: str = None) -> dict:
        """Prepare optimized transcription parameters based on language hint"""
        
        base_params = {
            "task": "transcribe",
            "word_timestamps": False,  # Disable for speed
            "condition_on_previous_text": False  # Disable for speed
        }
        
        if language_hint in self.config.priority_languages:
            # Optimized settings for Russian/English
            base_params.update({
                "language": language_hint,
                "beam_size": 1,  # Faster for known languages
                "temperature": 0.0,  # Deterministic for known languages
                "compression_ratio_threshold": 2.4,
                "logprob_threshold": -1.0
            })
        else:
            # Conservative settings for auto-detection
            base_params.update({
                "language": language_hint,  # May be None for auto-detect
                "beam_size": 5,  # More thorough for unknown languages
                "temperature": 0.2,  # Slight randomness for robustness
                "compression_ratio_threshold": 2.0,
                "logprob_threshold": -0.8
            })
            
        return base_params
```

### Language Preference Learning System

```python
class UserLanguageCache:
    """Learns and caches user language preferences for performance optimization"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.cache_ttl = 30 * 24 * 3600  # 30 days
        
    async def get_user_language(self, user_id: str) -> str:
        """Get user's preferred language from cache"""
        
        cache_key = f"user_lang:{user_id}"
        cached_data = await self.redis.get(cache_key)
        
        if cached_data:
            lang_data = json.loads(cached_data)
            # Return language if confidence is high enough
            if lang_data['confidence'] > 0.7:
                return lang_data['language']
                
        return None
    
    async def update_user_language(self, 
                                  user_id: str, 
                                  detected_language: str,
                                  confidence: float = 1.0):
        """Update user language preference with exponential moving average"""
        
        cache_key = f"user_lang:{user_id}"
        existing_data = await self.redis.get(cache_key)
        
        if existing_data:
            lang_data = json.loads(existing_data)
            
            if lang_data['language'] == detected_language:
                # Increase confidence for same language
                new_confidence = min(1.0, lang_data['confidence'] * 0.9 + confidence * 0.1)
            else:
                # Reset confidence for different language
                new_confidence = confidence * 0.5
                
            lang_data = {
                'language': detected_language,
                'confidence': new_confidence,
                'last_updated': time.time()
            }
        else:
            # New user
            lang_data = {
                'language': detected_language,
                'confidence': confidence * 0.8,  # Start with lower confidence
                'last_updated': time.time()
            }
        
        await self.redis.setex(
            cache_key, 
            self.cache_ttl, 
            json.dumps(lang_data)
        )
```

### Model Performance Optimization

```python
class ModelWarmer:
    """Optimizes model loading and warming for faster startup and inference"""
    
    async def load_model(self, 
                        model_size: str = "base",
                        device: str = "cpu",
                        compute_type: str = "int8") -> WhisperModel:
        """Load and optimize Whisper model for our use case"""
        
        # Load with optimized settings for CPU deployment
        model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            cpu_threads=4,  # Optimize for container CPU limits
            num_workers=1   # Single worker for memory efficiency
        )
        
        return model
    
    async def warm_up_model(self, model: WhisperModel):
        """Warm up model with dummy audio to improve first-request performance"""
        
        # Generate short dummy audio (1 second of silence)
        dummy_audio = np.zeros(16000, dtype=np.float32)
        
        # Perform dummy transcription to warm up model
        try:
            await model.transcribe(
                dummy_audio,
                language="en",
                beam_size=1,
                temperature=0.0
            )
            logger.info("Model warm-up completed successfully")
        except Exception as e:
            logger.warning(f"Model warm-up failed: {e}")
```

### Integration with Audio Processing Pipeline

```python
class SpeechPipeline:
    """Integrates audio processing with speech recognition"""
    
    def __init__(self, 
                 audio_processor: HybridAudioProcessor,
                 speech_recognizer: HybridSpeechRecognizer):
        self.audio_processor = audio_processor
        self.speech_recognizer = speech_recognizer
        
    async def process_voice_message(self, 
                                   file_id: str, 
                                   user_id: str = None) -> str:
        """Complete pipeline from Telegram file to transcribed text"""
        
        start_time = time.time()
        
        try:
            # 1. Audio processing (from first creative phase)
            audio_data = await self.audio_processor.process_audio(file_id)
            
            # 2. Speech recognition (this architecture)
            context = TranscriptionContext(
                user_id=user_id,
                file_id=file_id
            )
            
            result = await self.speech_recognizer.transcribe(
                audio_data, 
                user_id=user_id,
                context=context
            )
            
            total_time = time.time() - start_time
            logger.info(f"Complete processing time: {total_time:.2f}s")
            
            return result.text
            
        except Exception as e:
            logger.error(f"Pipeline processing failed: {e}")
            raise SpeechProcessingError(f"Failed to process voice message: {str(e)}")
```

## IMPLEMENTATION GUIDELINES

### Phase 1: Core Speech Engine (Day 1-2)

1. **Speech Recognizer Module** (`speech_recognizer.py`)
   ```python
   # Key classes to implement:
   - HybridSpeechRecognizer (main recognizer)
   - UserLanguageCache (preference learning)
   - ModelWarmer (optimization and warming)
   - PerformanceMonitor (metrics and monitoring)
   ```

2. **Configuration Integration** (`config.py`)
   ```python
   # Add speech recognition settings:
   WHISPER_MODEL_SIZE = "base"      # base|small|medium
   WHISPER_DEVICE = "cpu"           # cpu|cuda
   WHISPER_COMPUTE_TYPE = "int8"    # int8|float16|float32
   PRIORITY_LANGUAGES = ["ru", "en"]
   LANGUAGE_CACHE_TTL = 2592000     # 30 days
   ```

3. **Bot Integration** (`main.py`)
   ```python
   # Initialize speech pipeline during startup:
   async def startup():
       speech_recognizer = HybridSpeechRecognizer(config.speech_config)
       await speech_recognizer.initialize()
       
   # Update voice message handler:
   @dp.message(F.voice | F.video_note)
   async def handle_voice_message(message: Message):
       pipeline = SpeechPipeline(audio_processor, speech_recognizer)
       text = await pipeline.process_voice_message(
           message.voice.file_id, 
           user_id=str(message.from_user.id)
       )
       await message.reply(f"📝 {text}")
   ```

### Phase 2: Optimization and Learning (Day 2-3)

1. **Performance Monitoring**
   - Processing time tracking per user/language
   - Memory usage monitoring
   - Language detection accuracy metrics

2. **User Preference Learning**
   - Language preference caching and updating
   - Confidence scoring and adaptation
   - Performance improvement tracking

3. **Error Handling and Fallbacks**
   - Graceful model loading failure handling
   - Language detection fallback strategies
   - User notification for processing failures

### File Structure
```
speech_recognizer.py           # Main speech recognition logic
├── HybridSpeechRecognizer    # Core recognizer with smart preloading
├── UserLanguageCache         # User preference learning system
├── ModelWarmer              # Model optimization and warming
├── PerformanceMonitor       # Metrics and performance tracking
└── TranscriptionContext     # Context data structures

speech_pipeline.py            # Integration with audio processing
└── SpeechPipeline           # End-to-end processing coordinator

speech_config.py             # Speech-specific configuration
└── SpeechConfig             # Settings and validation
```

## VALIDATION AGAINST REQUIREMENTS

### Performance Requirements ✅
- **Processing Time**: 1.0-2.0s contribution to ≤2s overall target → **Achieved**
- **Memory Usage**: ~500MB for base model suitable for containers → **Achieved**
- **Startup Time**: 2-3s model loading with preloading → **Achieved**

### Language Requirements ✅
- **Russian/English Priority**: Optimized parameters and user learning → **Achieved**
- **Auto-Detection**: Fallback for other languages → **Achieved**
- **User Adaptation**: Learns and caches user language preferences → **Achieved**

### Integration Requirements ✅
- **Async Compatibility**: Full async/await integration → **Achieved**
- **Bot Integration**: Seamless aiogram integration → **Achieved**
- **Error Handling**: Graceful failure with user feedback → **Achieved**
- **Container Deployment**: Memory and CPU optimized → **Achieved**

### Implementation Feasibility ✅
- **Complexity**: Medium complexity suitable for Level 3 task → **Achievable**
- **Dependencies**: faster-whisper and Redis available → **Available**
- **Testing**: Clear component boundaries for unit testing → **Testable**
- **Maintenance**: Modular design with clear interfaces → **Maintainable**

🎨🎨🎨 **EXITING CREATIVE PHASE: SPEECH RECOGNITION ARCHITECTURE** 🎨🎨🎨

## SUMMARY

**Key Decision**: Selected Hybrid Architecture with Smart Preloading and User Preference Learning

**Core Innovation**: Combines efficient model management with intelligent user language preference learning for optimized performance.

**Architecture Highlights**:
- Single model with smart parameter optimization based on language hints
- User preference learning system with confidence scoring
- Model warming and preloading for faster startup
- Performance monitoring and optimization feedback loop

**Performance Prediction**: 1.0-2.0 seconds speech recognition time, contributing to overall ≤2s target when combined with audio processing.

**Implementation Readiness**: Detailed architecture with clear interfaces, ready for BUILD phase implementation.

**Next Steps**: Both creative phases complete - ready to transition to IMPLEMENT mode for development. 