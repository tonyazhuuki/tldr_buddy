#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Демонстрация нового промпта DEFAULT режима
"""

def demo_new_prompt():
    """Демонстрация нового формата"""
    
    print("🎯 ДЕМОНСТРАЦИЯ НОВОГО ПРОМПТА DEFAULT РЕЖИМА")
    print("=" * 60)
    
    # Пример входящего текста
    sample_text = """
    Проект по разработке мобильного приложения для доставки еды находится в критической фазе. 
    Команда из 8 разработчиков работает над финальными функциями. 
    Срок релиза - 15 декабря 2024 года. 
    Основные проблемы: нестабильная работа API, медленная загрузка изображений, 
    отсутствие интеграции с платежными системами. 
    Бюджет проекта: $150,000, потрачено $120,000. 
    Нужно срочно нанять 2 QA инженеров и 1 DevOps специалиста. 
    Риски: возможная задержка релиза на 2 недели, превышение бюджета на $20,000.
    """
    
    print("📥 ВХОДЯЩИЙ ТЕКСТ:")
    print(sample_text.strip())
    print("\n" + "=" * 60)
    
    # Симуляция ответа GPT с новым промптом
    mock_response = """📝 РЕЗЮМЕ: Проект мобильного приложения доставки еды в критической фазе с риском задержки релиза и превышения бюджета.

ОСНОВНЫЕ ПУНКТЫ (3–7):
• Проект доставки еды в финальной фазе разработки
• Команда: 8 разработчиков, срок релиза 15 декабря 2024
• Проблемы: нестабильный API, медленные изображения, нет платежей
• Бюджет: $150K запланировано, $120K потрачено
• Требуется: 2 QA + 1 DevOps специалист

⚡ ДЕЙСТВИЯ (если есть):
• нанять QA инженеров — HR/менеджер проекта — до 1 декабря — P1
• нанять DevOps специалиста — HR/менеджер проекта — до 1 декабря — P1
• исправить API стабильность — разработчики — до 10 декабря — P1
• оптимизировать загрузку изображений — frontend команда — до 8 декабря — P2
• интегрировать платежные системы — backend команда — до 12 декабря — P1

❓ ОТКРЫТЫЕ ВОПРОСЫ (если есть):
• Какие платежные системы приоритетны для интеграции?
• Достаточно ли 2 недель для найма специалистов?
• Есть ли резервный план при задержке релиза?

⚠️ РИСКИ/ОГРАНИЧЕНИЯ (если есть):
• Задержка релиза на 2 недели
• Превышение бюджета на $20,000
• Нехватка специалистов может замедлить разработку
• Технические проблемы могут усугубиться без DevOps"""
    
    print("🤖 ОТВЕТ GPT (новый формат):")
    print(mock_response)
    print("\n" + "=" * 60)
    
    # Симуляция парсинга и форматирования
    print("📤 ФОРМАТИРОВАННЫЙ ВЫВОД БОТА:")
    
    # Парсим результат (симуляция)
    lines = mock_response.split('\n')
    summary = None
    bullets = []
    actions = []
    questions = []
    risks = []
    
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('📝 РЕЗЮМЕ:'):
            summary = line.replace('📝 РЕЗЮМЕ:', '').strip()
        elif line.startswith('ОСНОВНЫЕ ПУНКТЫ'):
            current_section = 'bullets'
        elif line.startswith('⚡ ДЕЙСТВИЯ'):
            current_section = 'actions'
        elif line.startswith('❓ ОТКРЫТЫЕ ВОПРОСЫ'):
            current_section = 'questions'
        elif line.startswith('⚠️ РИСКИ'):
            current_section = 'risks'
        elif line.startswith('•') and current_section == 'bullets':
            bullets.append(line.replace('•', '').strip())
        elif line.startswith('•') and current_section == 'actions':
            actions.append(line.replace('•', '').strip())
        elif line.startswith('•') and current_section == 'questions':
            questions.append(line.replace('•', '').strip())
        elif line.startswith('•') and current_section == 'risks':
            risks.append(line.replace('•', '').strip())
    
    # Форматируем вывод как в боте
    output_parts = []
    
    if summary:
        output_parts.append(f"📝 **Резюме**: {summary}")
    
    if bullets:
        bullets_text = "\n".join([f"• {bullet}" for bullet in bullets])
        output_parts.append(f"**Основные пункты**:\n{bullets_text}")
    
    if actions:
        actions_text = "\n".join([f"• {action}" for action in actions])
        output_parts.append(f"⚡ **Действия**:\n{actions_text}")
    
    if questions:
        questions_text = "\n".join([f"• {q}" for q in questions])
        output_parts.append(f"❓ **Открытые вопросы**:\n{questions_text}")
    
    if risks:
        risks_text = "\n".join([f"• {risk}" for risk in risks])
        output_parts.append(f"⚠️ **Риски/ограничения**:\n{risks_text}")
    
    print("\n".join(output_parts))

if __name__ == "__main__":
    demo_new_prompt() 