# -*- coding: utf-8 -*-
r"""
АГЕНТ v12 — ЧТЕНИЕ ИЗ ПАМЯТИ (memory_facts_tools.py)
Простой инструмент для чтения фактов из базы данных памяти.
"""

from core import get_facts

def tool_memory_facts(entity_type=None, entity_name=None, limit=100):
    """Прочитать факты из памяти дома"""
    facts = get_facts(entity_type=entity_type, entity_name=entity_name, limit=limit)
    
    if not facts:
        return {"message": "фактов не найдено", "facts": []}
    
    return {"count": len(facts), "facts": facts}

TOOLS = [
    {
        "name": "memory_facts",
        "desc": "Прочитать факты из памяти дома: массы, параметры, отношения, с датами и источниками",
        "params": {
            "entity_type": "тип сущности (необязательно)",
            "entity_name": "имя сущности (необязательно)", 
            "limit": "количество записей (по умолчанию 100)"
        },
        "approval": False,
        "fn": tool_memory_facts
    }
]