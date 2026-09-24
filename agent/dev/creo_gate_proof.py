# -*- coding: utf-8 -*-
"""Доказательство главного: если Creo НЕ запущен, дом не поднимает его.
Подменяем только функцию проверки (Creo и CREOSON не трогаем, ничего не запускаем)."""
import sys, os
sys.path.insert(0, r"D:\AI\tools\agent")
os.chdir(r"D:\AI\tools\agent")
import creo_tools as C

out = []
out.append("ДО подмены: creo_running() = %r (у хозяина Creo может быть открыт)" % C.creo_running())

# Имитируем «Creo не запущен» и убеждаемся, что дом не откроет сессию (а значит не запустит Creo)
C.creo_running = lambda: False
g = C._creo_gate("file", "list_files")
out.append("Creo выключен → вентиль на чтение: %s" % ("БЛОКИРУЕТ (правильно)" if g else "пропускает — ОШИБКА"))
out.append("  что скажет агент: " + (g or "")[:160])
sess = C.connect()
out.append("Creo выключен → connect(): %r  %s" % (sess, "сессия НЕ открыта, POST connection/connect НЕ отправлен → Creo не поднимется" if not sess else "ОШИБКА: сессия открылась"))
out.append("явный start_creo при выключенном Creo: %s" % ("пропускается (только по согласованию с человеком)" if C._creo_gate("connection", "start_creo") is None else "заблокирован"))
open(r"D:\AI\log\reports\creo_gate_proof.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
