# -*- coding: utf-8 -*-
"""dead_settings.py — список настроек, которые никто не читает (постоянная проверка).

Правило дома: инлайн `python -c` запрещён (crash_ctl-inline-stderr-truncated),
поэтому проверка живёт файлом. Печатает МЁРТВЫЕ настройки и их тип.
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))
import settings as S  # noqa: E402

SKIP = {"__pycache__", "data", "_legacy", "_disabled", "log"}
NAMES = {"settings.py", "dead_settings.py", "audit_all.py"}


def main():
    dead = {}
    # ДЕФЕКТ ПРОВЕРКИ (03.10.2026, найден на себе): настройки моделей читаются через
    # `settings.model_for(role)` — по СБОРКЕ имени `"model_" + role`, а не литералом.
    # Поиск по имени их не видел, и 8 живых настроек попадали в «мёртвые». Учитываем их.
    MODEL_ROLES = {"index", "chat", "fast", "creo", "spec", "trail", "web", "audit"}
    for space, k, name, typ, defl, desc, ui in S.REGISTRY:
        if k.startswith("model_") and k.split("_", 1)[1] in MODEL_ROLES:
            continue                      # читается через model_for(role) — проверено в settings.py:165
        found = []
        for py in AGENT.rglob("*.py"):
            rel = py.relative_to(AGENT)
            if any(p in SKIP for p in rel.parts) or py.name in NAMES:
                continue
            try:
                if k in py.read_text(encoding="utf-8", errors="replace"):
                    found.append(str(rel).replace("\\", "/"))
            except Exception:
                pass
        if not found:
            dead[k] = (typ, name, space)
    print("МЁРТВЫХ НАСТРОЕК: %d из %d" % (len(dead), len(S.REGISTRY)))
    for k, (typ, name, space) in dead.items():
        print("   %-24s [%s] %-22s %s" % (k, typ, space, name))
    return 0


if __name__ == "__main__":
    sys.exit(main())