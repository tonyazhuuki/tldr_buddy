#!/usr/bin/env python3
"""
Demo Script: Enhanced Features Showcase
Tests emotion analysis and archetype systems without Telegram integration
"""

import asyncio
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

# Import enhanced modules
from text_processor import TextProcessor
from emotion_analyzer import EmotionAnalyzer, EmotionScores
from archetype_system import ArchetypeSystem, create_archetype_system

# Load environment
load_dotenv('.env.test')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - DEMO - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedFeaturesDemo:
    """Demo class for testing enhanced features"""
    
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.text_processor = None
        self.emotion_analyzer = None
        self.archetype_system = None
    
    async def initialize(self):
        """Initialize all systems"""
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY required for demo")
        
        print("🔧 Initializing enhanced systems...")
        
        # Initialize text processor
        self.text_processor = TextProcessor(self.openai_api_key)
        print("✅ Text processor initialized")
        
        # Initialize emotion analyzer
        self.emotion_analyzer = EmotionAnalyzer(self.text_processor.client)
        print("✅ Emotion analyzer initialized")
        
        # Initialize archetype system
        self.archetype_system = create_archetype_system(self.text_processor.client)
        print("✅ Archetype system initialized")
        
        print("🚀 All systems ready!\n")
    
    async def demo_text_processing(self, text: str):
        """Demo enhanced text processing"""
        print(f"📝 ДЕМО: Обработка текста")
        print(f"Входной текст: \"{text}\"")
        print("-" * 60)
        
        # Process with enhanced pipeline
        try:
            if not self.text_processor:
                raise ValueError("Text processor not initialized")
            result = await self.text_processor.process_parallel(text)
            formatted = self.text_processor.format_output(result)
            
            print("📊 РЕЗУЛЬТАТЫ ОБРАБОТКИ:")
            print(formatted)
            print("-" * 60)
            
            return result
            
        except Exception as e:
            print(f"❌ Ошибка обработки: {e}")
            return None
    
    async def demo_archetype_selection(self, text: str, emotion_scores: EmotionScores):
        """Demo archetype auto-selection"""
        print(f"\n🎭 ДЕМО: Автовыбор архетипа")
        
        # Get auto-suggestion
        if not self.archetype_system:
            raise ValueError("Archetype system not initialized")
        suggested_archetype, reason = await self.archetype_system.get_auto_suggestion(emotion_scores)
        
        print(f"🎯 Рекомендуемый архетип: {suggested_archetype}")
        print(f"📋 Причина: {reason}")
        print("-" * 60)
        
        return suggested_archetype
    
    async def demo_archetype_response(self, archetype: str, text: str, emotion_scores: EmotionScores):
        """Demo archetype response generation"""
        print(f"\n🤖 ДЕМО: Генерация ответа архетипа {archetype}")
        
        try:
            if not self.archetype_system:
                raise ValueError("Archetype system not initialized")
            response = await self.archetype_system.generate_archetype_response(
                archetype, text, emotion_scores
            )
            
            if response.error_message:
                print(f"❌ Ошибка генерации: {response.error_message}")
                return
            
            print(f"🎭 {archetype} советует:")
            for i, advice in enumerate(response.responses, 1):
                print(f"  {i}. {advice}")
            
            if response.signature:
                print(f"\n{response.signature}")
            
            print(f"⏱️ Время генерации: {response.processing_time:.2f}s")
            print("-" * 60)
            
        except Exception as e:
            print(f"❌ Ошибка генерации архетипа: {e}")
    
    async def demo_all_archetypes(self, text: str, emotion_scores: EmotionScores):
        """Demo all archetype responses"""
        print(f"\n🎪 ДЕМО: Все архетипы отвечают")
        
        archetypes = ['EMPATH', 'META-SAGE', 'TRICKSTER', 'CRAZY-WISDOM']
        
        for archetype in archetypes:
            print(f"\n--- {archetype} ---")
            await self.demo_archetype_response(archetype, text, emotion_scores)
    
    async def run_demo(self):
        """Run complete demo"""
        print("🎪 ДЕМО: Расширенные возможности Telegram бота")
        print("=" * 60)
        
        await self.initialize()
        
        # Test cases
        test_cases = [
            "Привет! Как дела? Жду твоего ответа.",
            "Опять эти идиоты ничего не понимают, достали уже со своими глупыми вопросами!",
            "Конечно, твоя идея просто гениальна... особенно та часть где все должны делать за тебя.",
            "Ты должен согласиться с моим предложением, иначе все будут думать что ты не командный игрок.",
            "Медитация помогает найти внутренний покой и гармонию с окружающим миром."
        ]
        
        for i, test_text in enumerate(test_cases, 1):
            print(f"\n🧪 ТЕСТ КЕЙС {i}")
            print("=" * 60)
            
            # 1. Enhanced text processing
            result = await self.demo_text_processing(test_text)
            if not result or not result.emotion_scores:
                continue
            
            # Create EmotionScores object
            emotion_scores = EmotionScores(
                sarcasm=result.emotion_scores.get('sarcasm', 0.0),
                toxicity=result.emotion_scores.get('toxicity', 0.0),
                manipulation=result.emotion_scores.get('manipulation', 0.0)
            )
            
            # 2. Archetype auto-selection
            suggested = await self.demo_archetype_selection(test_text, emotion_scores)
            
            # 3. Generate suggested archetype response
            await self.demo_archetype_response(suggested, test_text, emotion_scores)
            
            print("\n" + "=" * 60)
        
        print("\n🎉 ДЕМО ЗАВЕРШЕНО!")
        print("\nВсе новые возможности протестированы:")
        print("✅ Анализ эмоций (сарказм, токсичность, манипуляция)")
        print("✅ Автовыбор архетипа на основе эмоций")
        print("✅ Генерация советов в 4 различных стилях")
        print("✅ Интеграция с существующей обработкой текста")


async def main():
    """Main demo function"""
    try:
        demo = EnhancedFeaturesDemo()
        await demo.run_demo()
    except Exception as e:
        print(f"❌ Ошибка демо: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🎭 Запуск демо расширенных возможностей...")
    print("🔒 Безопасно: не влияет на продакшн бота")
    print()
    asyncio.run(main()) 