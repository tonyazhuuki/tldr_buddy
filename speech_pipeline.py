#!/usr/bin/env python3
"""
Speech Pipeline Integration for Telegram Voice-to-Insight Pipeline
Coordinates audio processing and speech recognition for end-to-end processing
"""

import asyncio
import logging
import time
from typing import Optional

from audio_processor import HybridAudioProcessor, AudioProcessingError
from speech_recognizer import (
    HybridSpeechRecognizer, 
    SpeechConfig, 
    TranscriptionContext, 
    TranscriptionResult,
    OpenAISpeechRecognitionError
)

logger = logging.getLogger(__name__)


class SpeechPipelineError(Exception):
    """Custom exception for speech pipeline errors"""
    
    def __init__(self, message, user_notified=False):
        super().__init__(message)
        self.user_notified = user_notified


class SpeechPipeline:
    """
    End-to-end speech processing pipeline integrating audio processing 
    and speech recognition with performance monitoring
    """
    
    def __init__(self, 
                 audio_processor: HybridAudioProcessor,
                 speech_recognizer: HybridSpeechRecognizer):
        self.audio_processor = audio_processor
        self.speech_recognizer = speech_recognizer
        self.pipeline_metrics = {
            'total_processed': 0,
            'total_time': 0.0,
            'audio_processing_time': 0.0,
            'speech_recognition_time': 0.0,
            'success_count': 0,
            'error_count': 0
        }
        
    async def process_voice_message(self, 
                                   file_id: str, 
                                   user_id: Optional[str] = None,
                                   bot=None,
                                   chat_id: Optional[str] = None) -> str:
        """
        Complete pipeline from Telegram file to transcribed text
        
        Args:
            file_id: Telegram file identifier
            user_id: User identifier for preference learning
            
        Returns:
            Transcribed text string
            
        Raises:
            SpeechPipelineError: If processing fails at any stage
        """
        
        start_time = time.time()
        audio_start_time = None
        speech_start_time = None
        
        try:
            logger.info(f"Starting speech pipeline for file {file_id}, user {user_id}")
            
            # 1. Audio processing phase
            audio_start_time = time.time()
            try:
                audio_data = await self.audio_processor.process_audio(file_id)
                audio_processing_time = time.time() - audio_start_time
                
                logger.info(f"Audio processing completed in {audio_processing_time:.2f}s, "
                           f"got {len(audio_data)} bytes")
                
            except AudioProcessingError as e:
                self._record_error("audio_processing", str(e))
                raise SpeechPipelineError(f"Audio processing failed: {str(e)}")
            
            # 2. Speech recognition phase
            speech_start_time = time.time()
            try:
                context = TranscriptionContext(
                    user_id=user_id,
                    file_id=file_id
                )
                
                result: TranscriptionResult = await self.speech_recognizer.transcribe(
                    audio_data, 
                    user_id=user_id,
                    context=context,
                    bot=bot,
                    chat_id=chat_id
                )
                
                speech_processing_time = time.time() - speech_start_time
                
                logger.info(f"Speech recognition completed in {speech_processing_time:.2f}s, "
                           f"detected language: {result.language}, "
                           f"confidence: {result.confidence:.2f}")
                
            except OpenAISpeechRecognitionError as e:
                self._record_error("speech_recognition", str(e))
                
                # Check if user message was already sent to avoid nested errors
                if hasattr(e, 'user_message_sent') and e.user_message_sent:
                    # User already notified, raise silent error
                    raise SpeechPipelineError("Speech recognition failed - user notified", user_notified=True)
                else:
                    # Regular error handling
                    raise SpeechPipelineError(f"Speech recognition failed: {str(e)}")
            
            # 3. Record success metrics
            total_time = time.time() - start_time
            self._record_success(total_time, audio_processing_time, speech_processing_time)
            
            logger.info(f"Pipeline completed successfully in {total_time:.2f}s total "
                       f"(audio: {audio_processing_time:.2f}s, "
                       f"speech: {speech_processing_time:.2f}s)")
            
            return result.text
            
        except SpeechPipelineError:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Unexpected pipeline error: {e}")
            self._record_error("pipeline", str(e))
            raise SpeechPipelineError(f"Unexpected pipeline error: {str(e)}")
    
    async def process_voice_message_detailed(self, 
                                           file_id: str, 
                                           user_id: Optional[str] = None) -> dict:
        """
        Process voice message and return detailed results including metadata
        
        Returns:
            Dictionary with transcription text and processing metadata
        """
        
        start_time = time.time()
        
        try:
            # Get detailed transcription result
            audio_data = await self.audio_processor.process_audio(file_id)
            
            context = TranscriptionContext(
                user_id=user_id,
                file_id=file_id
            )
            
            result: TranscriptionResult = await self.speech_recognizer.transcribe(
                audio_data, 
                user_id=user_id,
                context=context
            )
            
            total_time = time.time() - start_time
            
            return {
                'text': result.text,
                'language': result.language,
                'confidence': result.confidence,
                'processing_time': total_time,
                'speech_processing_time': result.processing_time,
                'audio_size_bytes': len(audio_data),
                'user_id': user_id,
                'file_id': file_id
            }
            
        except Exception as e:
            logger.error(f"Detailed processing failed: {e}")
            raise SpeechPipelineError(f"Detailed processing failed: {str(e)}")
    
    def _record_success(self, total_time: float, audio_time: float, speech_time: float):
        """Record successful processing metrics"""
        
        self.pipeline_metrics['total_processed'] += 1
        self.pipeline_metrics['success_count'] += 1
        self.pipeline_metrics['total_time'] += total_time
        self.pipeline_metrics['audio_processing_time'] += audio_time
        self.pipeline_metrics['speech_recognition_time'] += speech_time
    
    def _record_error(self, error_type: str, error_message: str):
        """Record error metrics"""
        
        self.pipeline_metrics['total_processed'] += 1
        self.pipeline_metrics['error_count'] += 1
        
        logger.error(f"Pipeline error ({error_type}): {error_message}")
    
    def get_performance_metrics(self) -> dict:
        """Get comprehensive performance metrics"""
        
        total_processed = self.pipeline_metrics['total_processed']
        
        if total_processed == 0:
            return {
                'total_processed': 0,
                'success_rate': 0.0,
                'average_total_time': 0.0,
                'average_audio_time': 0.0,
                'average_speech_time': 0.0
            }
        
        success_count = self.pipeline_metrics['success_count']
        
        return {
            'total_processed': total_processed,
            'success_count': success_count,
            'error_count': self.pipeline_metrics['error_count'],
            'success_rate': success_count / total_processed,
            'average_total_time': self.pipeline_metrics['total_time'] / max(1, success_count),
            'average_audio_time': self.pipeline_metrics['audio_processing_time'] / max(1, success_count),
            'average_speech_time': self.pipeline_metrics['speech_recognition_time'] / max(1, success_count),
            'performance_target_met': (self.pipeline_metrics['total_time'] / max(1, success_count)) <= 2.0
        }
    
    async def health_check(self) -> dict:
        """Perform system health check"""
        
        health_status = {
            'status': 'healthy',
            'components': {},
            'timestamp': time.time()
        }
        
        # Check audio processor
        try:
            # Audio processor is always ready if initialized
            health_status['components']['audio_processor'] = {
                'status': 'healthy',
                'message': 'Audio processor ready'
            }
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['components']['audio_processor'] = {
                'status': 'error',
                'message': f'Audio processor error: {str(e)}'
            }
        
        # Check speech recognizer (OpenAI API-based)
        try:
            # For API-based recognizer, check if API client is available
            if hasattr(self.speech_recognizer, 'api_client') and self.speech_recognizer.api_client:
                health_status['components']['speech_recognizer'] = {
                    'status': 'healthy',
                    'message': 'OpenAI API speech recognizer ready'
                }
            else:
                health_status['status'] = 'unhealthy'
                health_status['components']['speech_recognizer'] = {
                    'status': 'error',
                    'message': 'OpenAI API speech recognizer not initialized'
                }
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['components']['speech_recognizer'] = {
                'status': 'error',
                'message': f'Speech recognizer error: {str(e)}'
            }
        
        return health_status


class SpeechPipelineFactory:
    """Factory for creating configured speech pipeline instances"""
    
    @staticmethod
    async def create_pipeline(bot, redis_client=None) -> SpeechPipeline:
        """
        Create and initialize a complete speech pipeline
        
        Args:
            bot: Telegram bot instance
            redis_client: Optional Redis client for caching
            
        Returns:
            Fully initialized SpeechPipeline instance
        """
        
        logger.info("Creating OpenAI API-based speech pipeline...")
        
        # Import config to get API key
        from config import get_config
        config = get_config()
        
        # Create audio processor
        audio_processor = HybridAudioProcessor(bot, redis_client)
        
        # Create speech recognizer with configuration and API key
        speech_config = SpeechConfig()
        
        # Ensure API key is available
        if not config.openai_api_key:
            raise SpeechPipelineError("OpenAI API key not configured")
        
        speech_recognizer = HybridSpeechRecognizer(
            speech_config, 
            config.openai_api_key,
            redis_client
        )
        
        # Initialize speech recognizer (sets up API client)
        await speech_recognizer.initialize()
        
        # Create pipeline
        pipeline = SpeechPipeline(audio_processor, speech_recognizer)
        
        logger.info("OpenAI API-based speech pipeline created and initialized successfully")
        
        return pipeline


# Example usage and testing
async def main():
    """Test function for development"""
    
    print("SpeechPipeline module loaded successfully")
    print("Key components:")
    print("- SpeechPipeline: End-to-end processing coordinator")
    print("- SpeechPipelineFactory: Pipeline creation and initialization")
    print("- Comprehensive error handling and metrics tracking")
    print("- Health checking and performance monitoring")
    
    # Example of how pipeline would be created:
    # bot = Bot(token="YOUR_TOKEN")
    # pipeline = await SpeechPipelineFactory.create_pipeline(bot)
    # result = await pipeline.process_voice_message("file_id", "user_id")


if __name__ == "__main__":
    asyncio.run(main()) 