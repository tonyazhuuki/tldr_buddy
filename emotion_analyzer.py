"""
Emotion Analysis Module for Telegram Voice-to-Insight Bot

Provides GPT-4o-based emotion detection for sarcasm, toxicity, and manipulation
with configurable thresholds and integration with existing text processing pipeline.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Optional, Any
from dataclasses import dataclass

import openai
from openai import OpenAI

logger = logging.getLogger(__name__)


@dataclass
class EmotionScores:
    """Emotion analysis scores for a text"""
    sarcasm: float = 0.0
    toxicity: float = 0.0
    manipulation: float = 0.0
    processing_time: Optional[float] = None
    error_message: Optional[str] = None


class EmotionAnalyzer:
    """
    GPT-4o-based emotion analysis system for detecting sarcasm, toxicity, and manipulation.
    
    Provides configurable threshold-based analysis with performance optimization
    and integration with existing text processing patterns.
    """
    
    def __init__(self, openai_client: OpenAI):
        self.client = openai_client
        self.model = "gpt-4o"
        self.max_tokens = 200
        self.temperature = 0.1  # Low temperature for consistent scoring
        self.timeout = 5  # Target ≤0.3s overhead, allow buffer for network
        
        # Emotion detection thresholds (from creative specifications)
        self.thresholds = {
            'sarcasm_high': 0.7,
            'toxicity_high': 0.6,
            'manipulation_high': 0.5
        }
        
        # Emotion analysis prompt (optimized for Russian content)
        self.emotion_prompt = self._build_emotion_prompt()
    
    def _build_emotion_prompt(self) -> str:
        """Build optimized GPT-4o prompt for emotion detection"""
        return """Проанализируй эмоциональный подтекст текста и оцени уровни по трём критериям.

КРИТЕРИИ АНАЛИЗА:
1. САРКАЗМ: Ирония, насмешка, говорить одно, подразумевать противоположное
2. ТОКСИЧНОСТЬ: Агрессия, оскорбления, деструктивность, враждебность  
3. МАНИПУЛЯЦИЯ: Скрытое принуждение, эмоциональное давление, попытки контроля

ШКАЛА ОЦЕНКИ: 0.0 (отсутствует) до 1.0 (максимальный уровень)

ИНСТРУКЦИЯ: Верни ТОЛЬКО JSON в точном формате:
{{
    "sarcasm": 0.0,
    "toxicity": 0.0, 
    "manipulation": 0.0
}}

ТЕКСТ ДЛЯ АНАЛИЗА: {text}"""

    async def analyze_emotions(self, text: str) -> EmotionScores:
        """
        Analyze emotional subtext of given text using GPT-4o.
        
        Args:
            text: Text to analyze for emotional content
            
        Returns:
            EmotionScores with sarcasm, toxicity, and manipulation levels (0.0-1.0)
        """
        if not text or not text.strip():
            return EmotionScores(error_message="Empty text provided")
        
        start_time = datetime.now()
        
        try:
            # Prepare prompt with text
            prompt = self.emotion_prompt.format(text=text.strip())
            
            # Make GPT-4o API call
            response = await self._make_api_call(prompt)
            
            # Parse emotion scores from response
            emotion_scores = self._parse_emotion_response(response)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            emotion_scores.processing_time = processing_time
            
            logger.info(f"Emotion analysis completed in {processing_time:.3f}s - "
                       f"sarcasm: {emotion_scores.sarcasm:.2f}, "
                       f"toxicity: {emotion_scores.toxicity:.2f}, "
                       f"manipulation: {emotion_scores.manipulation:.2f}")
            
            return emotion_scores
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"Emotion analysis failed: {str(e)}"
            logger.error(f"{error_msg} (after {processing_time:.3f}s)")
            
            return EmotionScores(
                processing_time=processing_time,
                error_message=error_msg
            )
    
    async def _make_api_call(self, prompt: str) -> str:
        """Make async GPT-4o API call with timeout and error handling"""
        try:
            # Use asyncio timeout for performance control
            response = await asyncio.wait_for(
                self._sync_api_call(prompt),
                timeout=self.timeout
            )
            return response
            
        except asyncio.TimeoutError:
            raise Exception(f"Emotion analysis timeout after {self.timeout}s")
        except openai.RateLimitError:
            raise Exception("OpenAI rate limit exceeded")
        except openai.APIError as e:
            raise Exception(f"OpenAI API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error during API call: {str(e)}")
    
    async def _sync_api_call(self, prompt: str) -> str:
        """Synchronous OpenAI API call wrapped for async usage"""
        def make_call():
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Ты эксперт по анализу эмоционального подтекста в русских текстах."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                timeout=self.timeout
            )
            content = response.choices[0].message.content
            
            # Handle None or empty response
            if not content:
                logger.warning("GPT-4o returned empty content")
                return "{\"sarcasm\": 0.0, \"toxicity\": 0.0, \"manipulation\": 0.0}"
            
            return content.strip()
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, make_call)
    
    def _parse_emotion_response(self, response: str) -> EmotionScores:
        """Parse GPT-4o response into EmotionScores with robust error handling"""
        try:
            # Handle None or empty response
            if not response or not response.strip():
                logger.warning("Empty response from GPT-4o")
                return EmotionScores(
                    sarcasm=0.0,
                    toxicity=0.0,
                    manipulation=0.0,
                    error_message="Empty response"
                )
            
            # Clean response and extract JSON
            response = response.strip()
            
            # Remove markdown formatting - more robust approach
            lines = response.split('\n')
            json_lines = []
            inside_json = False
            
            for line in lines:
                line = line.strip()
                
                # Start of JSON block
                if line.startswith('```json') or line == '```':
                    inside_json = True
                    continue
                # End of JSON block
                elif line == '```' and inside_json:
                    break
                # JSON content
                elif inside_json or line.startswith('{'):
                    json_lines.append(line)
                    inside_json = True
                # Direct JSON without markdown
                elif '"sarcasm"' in line or '"toxicity"' in line or '"manipulation"' in line:
                    json_lines.append(line)
            
            # Join JSON lines
            json_text = '\n'.join(json_lines).strip()
            
            # Fallback: try to find JSON-like pattern
            if not json_text:
                import re
                json_pattern = r'\{[^}]*"sarcasm"[^}]*\}'
                match = re.search(json_pattern, response, re.DOTALL)
                if match:
                    json_text = match.group(0)
                else:
                    logger.warning(f"No JSON pattern found in response: {response[:100]}...")
                    return EmotionScores(
                        sarcasm=0.0,
                        toxicity=0.0,
                        manipulation=0.0,
                        error_message="No JSON found in response"
                    )
            
            # Parse JSON response
            emotion_data = json.loads(json_text)
            
            # Extract and validate scores with defaults
            sarcasm = float(emotion_data.get('sarcasm', 0.0))
            toxicity = float(emotion_data.get('toxicity', 0.0))
            manipulation = float(emotion_data.get('manipulation', 0.0))
            
            # Clamp values to valid range [0.0, 1.0]
            sarcasm = max(0.0, min(1.0, sarcasm))
            toxicity = max(0.0, min(1.0, toxicity))
            manipulation = max(0.0, min(1.0, manipulation))
            
            return EmotionScores(
                sarcasm=sarcasm,
                toxicity=toxicity,
                manipulation=manipulation
            )
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse emotion response. Response: '{response[:200]}...'. Error: {e}")
            # Return neutral scores on parse failure
            return EmotionScores(
                sarcasm=0.0,
                toxicity=0.0,
                manipulation=0.0,
                error_message=f"Parse error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error in emotion parsing: {e}")
            return EmotionScores(
                sarcasm=0.0,
                toxicity=0.0,
                manipulation=0.0,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    def get_emotion_levels(self, scores: EmotionScores) -> Dict[str, str]:
        """
        Convert emotion scores to human-readable levels (высокий/средний/низкий).
        
        Args:
            scores: EmotionScores object with numeric values
            
        Returns:
            Dict with emotion names and their level descriptions
        """
        if scores.error_message:
            # Show first 30 chars of error for debugging
            error_short = scores.error_message[:30] + "..." if len(scores.error_message) > 30 else scores.error_message
            return {
                'sarcasm': f'ошибка: {error_short}',
                'toxicity': f'ошибка: {error_short}', 
                'manipulation': f'ошибка: {error_short}'
            }
        
        def score_to_level(score: float, high_threshold: float) -> str:
            if score >= high_threshold:
                return 'высокий'
            elif score >= high_threshold * 0.6:  # Medium threshold at 60% of high
                return 'средний'
            else:
                return 'низкий'
        
        return {
            'sarcasm': score_to_level(scores.sarcasm, self.thresholds['sarcasm_high']),
            'toxicity': score_to_level(scores.toxicity, self.thresholds['toxicity_high']),
            'manipulation': score_to_level(scores.manipulation, self.thresholds['manipulation_high'])
        }
    
    def has_high_emotion(self, scores: EmotionScores) -> Dict[str, bool]:
        """
        Check which emotions exceed high thresholds (for archetype selection).
        
        Args:
            scores: EmotionScores object
            
        Returns:
            Dict indicating which emotions are at high levels
        """
        if scores.error_message:
            return {'sarcasm': False, 'toxicity': False, 'manipulation': False}
        
        return {
            'sarcasm': scores.sarcasm >= self.thresholds['sarcasm_high'],
            'toxicity': scores.toxicity >= self.thresholds['toxicity_high'], 
            'manipulation': scores.manipulation >= self.thresholds['manipulation_high']
        }


class EmotionAnalysisIntegration:
    """Integration helper for adding emotion analysis to existing text processing"""
    
    def __init__(self, emotion_analyzer: EmotionAnalyzer):
        self.analyzer = emotion_analyzer
    
    async def enhance_processing_result(self, text: str, processing_result: dict) -> dict:
        """
        Add emotion analysis to existing processing result.
        
        Args:
            text: Original text that was processed
            processing_result: Existing text processing result dict
            
        Returns:
            Enhanced result with emotion scores and levels
        """
        # Analyze emotions in parallel with other processing
        emotion_scores = await self.analyzer.analyze_emotions(text)
        
        # Add emotion data to processing result
        enhanced_result = processing_result.copy()
        enhanced_result.update({
            'emotion_scores': {
                'sarcasm': emotion_scores.sarcasm,
                'toxicity': emotion_scores.toxicity,
                'manipulation': emotion_scores.manipulation
            },
            'emotion_levels': self.analyzer.get_emotion_levels(emotion_scores),
            'emotion_high': self.analyzer.has_high_emotion(emotion_scores),
            'emotion_processing_time': emotion_scores.processing_time,
            'emotion_error': emotion_scores.error_message
        })
        
        return enhanced_result 