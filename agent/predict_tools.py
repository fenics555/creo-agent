# -*- coding: utf-8 -*-
def tool_trail_predict(top=10, **kw):
    """Прогноз деградации: прямое чтение таблицы trail_problems (без парсинга текста trail_trend)."""
    try:
        import trail_tools as TT
        from core import db
        c = db()
        rows = c.execute("SELECT kind,subject,count,total_sec,status FROM trail_problems ORDER BY total_sec DESC").fetchall()
        c.close()
    except Exception as e:
        return "нет данных для прогноза (%s)" % e
    if not rows:
        return "нет данных для прогноза"
    try: top = int(top or 10)
    except Exception: top = 10
    names = getattr(TT, "_NAMES", {})
    out = ["ПРОГНОЗ ДЕГРАДАЦИИ (риск = суммарные потери времени по накопленным болезням):"]
    for kind, subj, cnt, tsec, st in rows[:top]:
        out.append("⚠ [%s] %s — %.0f сек (%.1f мин) за %d случаев — %s" % (names.get(kind, kind), subj, tsec or 0, (tsec or 0) / 60.0, cnt or 0, st))
    worst = rows[0]
    out.append("Главный риск: %s / %s. Рекомендация: purge версий, упрощение регенерации, разбор болезни «%s»." % (names.get(worst[0], worst[0]), worst[1], names.get(worst[0], worst[0])))
    return "\n".join(out)

TOOLS = [{"name": "trail_predict", "desc": "Прогноз деградации моделей", "params": {"top": "строк"}, "approval": False, "fn": tool_trail_predict}]

