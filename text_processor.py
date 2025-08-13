"""
Text Processing Pipeline for Telegram Voice-to-Insight Bot

Handles parallel processing of transcribed text through multiple modes (DEFAULT, TONE, custom).
Provides structured output with summary, bullets, actions, and tone analysis.
"""

import asyncio
import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

import openai
from openai import OpenAI

from emotion_analyzer import EmotionAnalyzer, EmotionAnalysisIntegration

logger = logging.getLogger(__name__)


@dataclass
class Mode:
    """Configuration for a processing mode"""
    name: str
    model: str
    description: str
    prompt: str
    max_tokens: int
    temperature: float
    timeout: int
    enabled: bool
    created_at: str
    version: str


@dataclass
class ProcessingResult:
    """Result of text processing through multiple modes"""
    success: bool
    summary: Optional[str] = None
    bullets: Optional[List[str]] = None
    actions: Optional[str] = None
    questions: Optional[List[str]] = None
    risks: Optional[List[str]] = None
    tone_analysis: Optional[Dict[str, str]] = None
    emotion_scores: Optional[Dict[str, float]] = None
    emotion_levels: Optional[Dict[str, str]] = None
    emotion_high: Optional[Dict[str, bool]] = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    emotion_processing_time: Optional[float] = None


class ModeManager:
    """Manages loading and validation of processing modes"""
    
    def __init__(self, modes_directory: str = "modes"):
        self.modes_directory = Path(modes_directory)
        self.modes: Dict[str, Mode] = {}
        self._last_reload = None
        
    def load_modes(self) -> Dict[str, Mode]:
        """Load all modes from JSON files in modes directory"""
        try:
            self.modes = {}
            
            if not self.modes_directory.exists():
                logger.warning(f"Modes directory {self.modes_directory} does not exist")
                return self.modes
                
            for mode_file in self.modes_directory.glob("*.json"):
                try:
                    with open(mode_file, 'r', encoding='utf-8') as f:
                        mode_data = json.load(f)
                    
                    # Validate mode configuration
                    if self._validate_mode_config(mode_data):
                        mode = Mode(**mode_data)
                        self.modes[mode.name] = mode
                        logger.info(f"Loaded mode: {mode.name} (model: {mode.model})")
                    else:
                        logger.error(f"Invalid mode configuration in {mode_file}")
                        
                except Exception as e:
                    logger.error(f"Error loading mode from {mode_file}: {e}")
                    
            self._last_reload = datetime.now()
            logger.info(f"Loaded {len(self.modes)} modes: {list(self.modes.keys())}")
            return self.modes
            
        except Exception as e:
            logger.error(f"Error loading modes: {e}")
            return {}
    
    def _validate_mode_config(self, mode_data: Dict[str, Any]) -> bool:
        """Validate mode configuration has required fields"""
        required_fields = ['name', 'model', 'prompt', 'max_tokens', 'temperature', 'enabled']
        
        for field in required_fields:
            if field not in mode_data:
                logger.error(f"Missing required field '{field}' in mode configuration")
                return False
                
        return True
    
    def get_mode(self, name: str) -> Optional[Mode]:
        """Get mode by name"""
        return self.modes.get(name)
    
    def get_enabled_modes(self) -> List[Mode]:
        """Get all enabled modes"""
        return [mode for mode in self.modes.values() if mode.enabled]
    
    def add_custom_mode(self, name: str, config: Dict[str, Any]) -> bool:
        """Add a custom mode and save to file"""
        try:
            # Add default values if missing
            config.setdefault('enabled', True)
            config.setdefault('created_at', datetime.now().isoformat())
            config.setdefault('version', '1.0')
            config.setdefault('max_tokens', 1000)
            config.setdefault('temperature', 0.5)
            config.setdefault('timeout', 10)
            config['name'] = name
            
            if not self._validate_mode_config(config):
                return False
                
            # Save to file
            mode_file = self.modes_directory / f"{name.lower()}.json"
            with open(mode_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # Add to loaded modes
            mode = Mode(**config)
            self.modes[name] = mode
            
            logger.info(f"Added custom mode: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding custom mode {name}: {e}")
            return False


class TextProcessor:
    """Processes transcribed text through multiple modes in parallel"""
    
    def __init__(self, openai_api_key: str, modes_directory: str = "modes"):
        self.client = OpenAI(api_key=openai_api_key)
        self.mode_manager = ModeManager(modes_directory)
        self.mode_manager.load_modes()
        
        # Initialize emotion analysis
        self.emotion_analyzer = EmotionAnalyzer(self.client)
        self.emotion_integration = EmotionAnalysisIntegration(self.emotion_analyzer)
        
    async def process_parallel(self, text: str) -> ProcessingResult:
        """Process text through DEFAULT and TONE modes in parallel"""
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Get required modes
            default_mode = self.mode_manager.get_mode("DEFAULT")
            tone_mode = self.mode_manager.get_mode("TONE")
            
            if not default_mode or not tone_mode:
                missing = []
                if not default_mode:
                    missing.append("DEFAULT")
                if not tone_mode:
                    missing.append("TONE")
                
                error_msg = f"Required modes not found: {', '.join(missing)}"
                logger.error(error_msg)
                return ProcessingResult(success=False, error_message=error_msg)
            
            # Process both modes and emotion analysis in parallel
            tasks = [
                self._process_mode(text, default_mode),
                self._process_mode(text, tone_mode),
                self.emotion_analyzer.analyze_emotions(text)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Parse results
            default_result = results[0] if not isinstance(results[0], Exception) else None
            tone_result = results[1] if not isinstance(results[1], Exception) else None
            emotion_result = results[2] if not isinstance(results[2], Exception) else None
            
            # Ensure results are strings or None
            default_text = default_result if isinstance(default_result, str) else None
            tone_text = tone_result if isinstance(tone_result, str) else None
            
            # Parse DEFAULT mode result
            summary, bullets, actions, questions, risks = self._parse_default_result(default_text)
            
            # Parse TONE mode result
            tone_analysis = self._parse_tone_result(tone_text)
            
            # Process emotion analysis result
            emotion_scores = None
            emotion_levels = None
            emotion_high = None
            emotion_processing_time = None
            
            if emotion_result and not isinstance(emotion_result, Exception):
                from emotion_analyzer import EmotionScores
                if isinstance(emotion_result, EmotionScores):
                    emotion_scores = {
                        'sarcasm': emotion_result.sarcasm,
                        'toxicity': emotion_result.toxicity,
                        'manipulation': emotion_result.manipulation
                    }
                    emotion_levels = self.emotion_analyzer.get_emotion_levels(emotion_result)
                    emotion_high = self.emotion_analyzer.has_high_emotion(emotion_result)
                    emotion_processing_time = emotion_result.processing_time
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            return ProcessingResult(
                success=True,
                summary=summary,
                bullets=bullets,
                actions=actions,
                questions=questions,
                risks=risks,
                tone_analysis=tone_analysis,
                emotion_scores=emotion_scores,
                emotion_levels=emotion_levels,
                emotion_high=emotion_high,
                processing_time=processing_time,
                emotion_processing_time=emotion_processing_time
            )
            
        except Exception as e:
            logger.error(f"Error in parallel processing: {e}")
            return ProcessingResult(success=False, error_message=str(e))
    
    async def _process_mode(self, text: str, mode: Mode) -> Optional[str]:
        """Process text through a single mode"""
        try:
            # Format prompt with text
            formatted_prompt = mode.prompt.format(text=text)
            
            # Make API call
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=mode.model,
                messages=[
                    {"role": "user", "content": formatted_prompt}
                ],
                max_tokens=mode.max_tokens,
                temperature=mode.temperature,
                timeout=mode.timeout
            )
            
            content = response.choices[0].message.content
            if content:
                result = content.strip()
                logger.info(f"Mode {mode.name} processed successfully")
                return result
            else:
                logger.warning(f"Mode {mode.name} returned empty content")
                return None
            
        except Exception as e:
            logger.error(f"Error processing mode {mode.name}: {e}")
            return None
    
    def _parse_default_result(self, result: Optional[str]) -> Tuple[Optional[str], Optional[List[str]], Optional[str], Optional[List[str]], Optional[List[str]]]:
        """Parse DEFAULT mode result into summary, bullets, actions, questions, and risks"""
        if not result:
            return None, None, None, None, None
            
        try:
            lines = result.split('\n')
            summary = None
            bullets = []
            actions = None
            questions = []
            risks = []
            
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Support both old and new formats
                if line.startswith('📝 РЕЗЮМЕ:') or line.startswith('РЕЗЮМЕ:'):
                    summary = line.replace('📝 РЕЗЮМЕ:', '').replace('РЕЗЮМЕ:', '').strip()
                    current_section = 'summary'
                elif line.startswith('ОСНОВНЫЕ ПУНКТЫ') or line.startswith('ОСНОВНЫЕ ПУНКТЫ:'):
                    current_section = 'bullets'
                elif line.startswith('⚡ ДЕЙСТВИЯ') or line.startswith('ДЕЙСТВИЯ:'):
                    current_section = 'actions'
                elif line.startswith('нет явных действий'):
                    # Special case for "no actions"
                    actions = 'нет явных действий'
                    current_section = 'actions'
                elif line.startswith('❓ ОТКРЫТЫЕ ВОПРОСЫ'):
                    current_section = 'questions'
                elif line.startswith('⚠️ РИСКИ'):
                    current_section = 'risks'
                elif line.startswith('•') and current_section == 'bullets':
                    bullets.append(line.replace('•', '').strip())
                elif line.startswith('•') and current_section == 'actions':
                    # Collect action items
                    if actions is None:
                        actions = line.replace('•', '').strip()
                    else:
                        actions += '\n' + line.replace('•', '').strip()
                elif line.startswith('•') and current_section == 'questions':
                    questions.append(line.replace('•', '').strip())
                elif line.startswith('•') and current_section == 'risks':
                    risks.append(line.replace('•', '').strip())
            
            return summary, bullets if bullets else None, actions, questions if questions else None, risks if risks else None
            
        except Exception as e:
            logger.error(f"Error parsing DEFAULT result: {e}")
            return None, None, None, None, None
    
    def _parse_tone_result(self, result: Optional[str]) -> Optional[Dict[str, str]]:
        """Parse TONE mode result into structured analysis"""
        if not result:
            return None
            
        try:
            lines = result.split('\n')
            tone_data = {}
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Support both old and new formats for backward compatibility
                if line.startswith('🎯 СКРЫТОЕ НАМЕРЕНИЕ:') or line.startswith('🎯 СКРЫТЫЕ НАМЕРЕНИЯ:') or line.startswith('СКРЫТЫЕ НАМЕРЕНИЯ:'):
                    intent_text = line.replace('🎯 СКРЫТОЕ НАМЕРЕНИЕ:', '').replace('🎯 СКРЫТЫЕ НАМЕРЕНИЯ:', '').replace('СКРЫТЫЕ НАМЕРЕНИЯ:', '').strip()
                    tone_data['hidden_intent'] = intent_text
                elif line.startswith('😶‍🌫️ ДОМИНИРУЮЩАЯ ЭМОЦИЯ:') or line.startswith('😄 ДОМИНИРУЮЩАЯ ЭМОЦИЯ:') or line.startswith('ДОМИНИРУЮЩАЯ ЭМОЦИЯ:'):
                    emotion_text = line.replace('😶‍🌫️ ДОМИНИРУЮЩАЯ ЭМОЦИЯ:', '').replace('😄 ДОМИНИРУЮЩАЯ ЭМОЦИЯ:', '').replace('ДОМИНИРУЮЩАЯ ЭМОЦИЯ:', '').strip()
                    tone_data['dominant_emotion'] = emotion_text
                elif line.startswith('🗣️ СТИЛЬ ВЗАИМОДЕЙСТВИЯ:') or line.startswith('💬 СТИЛЬ ВЗАИМОДЕЙСТВИЯ:') or line.startswith('СТИЛЬ ВЗАИМОДЕЙСТВИЯ:'):
                    style_text = line.replace('🗣️ СТИЛЬ ВЗАИМОДЕЙСТВИЯ:', '').replace('💬 СТИЛЬ ВЗАИМОДЕЙСТВИЯ:', '').replace('СТИЛЬ ВЗАИМОДЕЙСТВИЯ:', '').strip()
                    tone_data['interaction_style'] = style_text
                elif line.startswith('🔎 ПРИЗНАКИ (цитаты):'):
                    # Skip quotes section for now, keep in interaction_style if needed
                    current_section = 'quotes'
                elif line.startswith('🎛 УВЕРЕННОСТЬ:'):
                    # Skip confidence section for now
                    current_section = 'confidence'
                elif line.startswith('• 🎯 СКРЫТОЕ НАМЕРЕНИЕ:'):
                    intent_text = line.replace('• 🎯 СКРЫТОЕ НАМЕРЕНИЕ:', '').strip()
                    tone_data['hidden_intent'] = intent_text
                elif line.startswith('• 😶‍🌫️ ДОМИНИРУЮЩАЯ ЭМОЦИЯ:'):
                    emotion_text = line.replace('• 😶‍🌫️ ДОМИНИРУЮЩАЯ ЭМОЦИЯ:', '').strip()
                    tone_data['dominant_emotion'] = emotion_text
                elif line.startswith('• 🗣️ СТИЛЬ ВЗАИМОДЕЙСТВИЯ:'):
                    style_text = line.replace('• 🗣️ СТИЛЬ ВЗАИМОДЕЙСТВИЯ:', '').strip()
                    tone_data['interaction_style'] = style_text
            
            return tone_data if tone_data else None
            
        except Exception as e:
            logger.error(f"Error parsing TONE result: {e}")
            return None
    
    def format_output(self, result: ProcessingResult) -> str:
        """Format processing result according to ТЗ specification"""
        if not result.success:
            return f"❌ Ошибка обработки: {result.error_message or 'Неизвестная ошибка'}"
        
        output_parts = []
        
        # Summary
        if result.summary:
            output_parts.append(f"📝 **Резюме**: {result.summary}")
        
        # Bullets
        if result.bullets:
            bullets_text = "\n".join([f"• {bullet}" for bullet in result.bullets])
            output_parts.append(f"**Основные пункты**:\n{bullets_text}")
        
        # Actions - support new format with multiple lines
        if result.actions and result.actions.strip():
            # Check for "no actions" case
            if result.actions.strip() == 'нет явных действий':
                output_parts.append(f"⚡ **Действия**: нет явных действий")
            # Check if actions contain multiple lines (new format)
            elif '\n' in result.actions:
                # New format with structured actions
                output_parts.append(f"⚡ **Действия**:\n{result.actions}")
            else:
                # Old format - single line
                output_parts.append(f"👉 **Действия**: {result.actions}")
        
        # Questions
        if result.questions:
            questions_text = "\n".join([f"• {q}" for q in result.questions])
            output_parts.append(f"❓ **Открытые вопросы**:\n{questions_text}")
        
        # Risks
        if result.risks:
            risks_text = "\n".join([f"• {risk}" for risk in result.risks])
            output_parts.append(f"⚠️ **Риски/ограничения**:\n{risks_text}")
        
        # Emotion analysis indicators - REMOVED from main output (available via /layers command)
        # if result.emotion_levels:
        #     emotion_parts = []
        #     emotion_parts.append(f"😈 уровень сарказма: {result.emotion_levels.get('sarcasm', 'неизвестно')}")
        #     emotion_parts.append(f"☠ уровень токсичности: {result.emotion_levels.get('toxicity', 'неизвестно')}")
        #     emotion_parts.append(f"🎣 уровень скрытой манипуляции: {result.emotion_levels.get('manipulation', 'неизвестно')}")
        #     output_parts.append("\n".join(emotion_parts))
        
        # Tone analysis - REMOVED from main output (available via /анализ command)
        # if result.tone_analysis:
        #     tone_lines = []
        #     if result.tone_analysis.get('hidden_intent'):
        #         tone_lines.append(f"  🎯 **Намерения**: {result.tone_analysis['hidden_intent']}")
        #     if result.tone_analysis.get('dominant_emotion'):
        #         tone_lines.append(f"  😶‍🌫️ **Эмоция**: {result.tone_analysis['dominant_emotion']}")
        #     if result.tone_analysis.get('interaction_style'):
        #         tone_lines.append(f"  🗣️ **Стиль**: {result.tone_analysis['interaction_style']}")
        #     
        #     if tone_lines:
        #         tone_text = "\n".join(tone_lines)
        #         output_parts.append(f"🧠 **Психологический анализ**:\n{tone_text}")
        
        # Processing time
        if result.processing_time:
            output_parts.append(f"\n⏱️ Обработано за {result.processing_time:.1f}с")
        
        return "\n\n".join(output_parts) if output_parts else "❌ Нет результатов обработки"
    
    def reload_modes(self):
        """Reload modes from files (hot-reload capability)"""
        self.mode_manager.load_modes()
        logger.info("Modes reloaded successfully")


# Example usage and testing
if __name__ == "__main__":
    async def test_processor():
        """Test the text processor with sample data"""
        # This would normally use real API key from config
        processor = TextProcessor("test-key")
        
        sample_text = "Привет, мне нужно завтра созвониться с командой по поводу нового проекта. Думаю, стоит обсудить бюджет и сроки."
        
        result = await processor.process_parallel(sample_text)
        formatted = processor.format_output(result)
        print(formatted)
    
    # Run test if executed directly
    # asyncio.run(test_processor()) 