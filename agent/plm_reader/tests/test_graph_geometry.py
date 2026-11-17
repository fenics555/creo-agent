# -*- coding: utf-8 -*-
"""Регресс-тест V213: строй/геометрия нижнего «Графа» + устойчивый парсер дат журнала.

Ловит два живых дефекта (доделка S2):
  (1) окно ИГНОРИРОВАЛО `graph_graph_layout` (строй) и зашивало геометрию 170/64/158/40 —
      настройка «СТРОЙ ГРАФА: горизонтально / вертикально» работала только в HTML-консоли;
  (2) парсер `changes.ts` понимал ТОЛЬКО ISO — легаси-записи «дд.мм.гггг» молча выпадали из «Реки».

Шару Z: не трогает. Выход: 0 — ок, 1 — провал.
"""
import datetime
import os
import sys

HERE = r"D:\AI\tools\agent\plm_reader"
sys.path.insert(0, HERE)
os.chdir(HERE)
import plm_toolwin as tw      # noqa: E402

fails = []
NW, NH, STEP = 158, 40, 64

# 1) СТРОЙ: vert=True («col») — уровень идёт ВНИЗ; vert=False («row») — ВПРАВО
xv, yv = tw.graph_point(0, 3, True, NW, NH, STEP)
xh, yh = tw.graph_point(0, 3, False, NW, NH, STEP)
print("строй col (уровень вниз):", (xv, yv), "| строй row (уровень вправо):", (xh, yh))
if (xv, yv) != (0, 3 * STEP):
    fails.append("col: уровень должен идти ВНИЗ (0, 3*step), получено %r" % ((xv, yv),))
if (xh, yh) != (3 * (NW + 95), 0):
    fails.append("row: уровень должен идти ВПРАВО (3*(nw+95), 0), получено %r" % ((xh, yh),))

# индекс раскладки: в col — по горизонтали, в row — по вертикали
if tw.graph_point(2, 0, True, NW, NH, STEP) != (2 * (NW + 12), 0):
    fails.append("col: x-индекс раскладки должен сдвигать ВПРАВО")
if tw.graph_point(2, 0, False, NW, NH, STEP) != (0, 2 * STEP):
    fails.append("row: x-индекс раскладки должен сдвигать ВНИЗ")

# 2) ВЫХОД РЕБРА — перпендикулярно строю
if tw.graph_out(1, True, NW, NH) != (0, NH // 2):
    fails.append("col: выход ребра «ниже» = (0, nh/2)")
if tw.graph_out(-1, True, NW, NH) != (0, -(NH // 2)):
    fails.append("col: выход ребра «выше» = (0, -nh/2)")
if tw.graph_out(1, False, NW, NH) != (NW // 2, 0):
    fails.append("row: выход ребра «правее» = (nw/2, 0)")

# 3) ШАГ (следствие настроек graph_card_h / graph_thumb) реально влияет на геометрию
if tw.graph_point(1, 1, True, NW, NH, 52) == tw.graph_point(1, 1, True, NW, NH, 200):
    fails.append("шаг между узлами должен влиять на геометрию (col)")
if tw.graph_point(1, 1, False, NW, NH, 52) == tw.graph_point(1, 1, False, NW, NH, 200):
    fails.append("шаг между узлами должен влиять на геометрию (row)")

# 3б) V216: ЛОКАЛЬНЫЙ РАНГ ВНУТРИ УРОВНЯ — компактная раскладка (`graph_ranks`).
# Раньше по оси «внутри уровня» шёл ГЛОБАЛЬНЫЙ индекс листьев ⇒ узлы уровня разлетались.
pos = {"A": (0.0, 0.0), "B": (5.0, 0.0), "C": (12.0, 0.0),
       "D": (5.0, 1.0), "E": (6.0, 1.0)}
rk = tw.graph_ranks(pos)
print("локальные ранги уровня:", rk)
if rk != {"A": 0, "B": 1, "C": 2, "D": 0, "E": 1}:
    fails.append("graph_ranks: локальный ранг внутри уровня посчитан неверно: %r" % (rk,))
if not (rk["D"] < rk["E"]):          # порядок внутри уровня — по исходному xi (5 < 6)
    fails.append("graph_ranks: порядок по xi внутри уровня нарушен")
if rk["D"] != 0:                     # каждый уровень нумеруется с 0 — уровни не мешают друг другу
    fails.append("graph_ranks: первый узел уровня должен иметь ранг 0")

# 4) ПАРСЕР ДАТ журнала: ISO + ЛЕГАСИ «дд.мм.гггг»
d1 = tw.parse_change_date("2026-11-17 10:33:41")
d2 = tw.parse_change_date("31.07.2023 31.07.23 10:46")
d3 = tw.parse_change_date("02.02.2023 ")
d4 = tw.parse_change_date("")
d5 = tw.parse_change_date(None)
print("ISO:", d1, "| легаси:", d2, "/", d3, "| мусор:", d4, "/", d5)
if d1 != datetime.date(2026, 11, 17):
    fails.append("ISO-дата не распознана: %r" % (d1,))
if d2 != datetime.date(2023, 7, 31):
    fails.append("легаси-дата с хвостом не распознана: %r" % (d2,))
if d3 != datetime.date(2023, 2, 2):
    fails.append("легаси-дата «дд.мм.гггг» не распознана: %r" % (d3,))
if d4 is not None or d5 is not None:
    fails.append("пустой/None ts должен давать None")

print("")
print("ИТОГ: " + ("ОК — строй графа читается из настроек, даты ISO+легаси" if not fails
                  else "ПРОВАЛЫ: " + "; ".join(fails)))
sys.exit(1 if fails else 0)
