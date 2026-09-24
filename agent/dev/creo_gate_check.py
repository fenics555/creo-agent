# -*- coding: utf-8 -*-
"""Проверка вентиля Creo: дом НЕ должен поднимать Creo сам. Безопасно — без подъёма CREOSON/Creo."""
import sys, os
sys.path.insert(0, r"D:\AI\tools\agent")
os.chdir(r"D:\AI\tools\agent")
import settings
import creo_tools as C

out = []
out.append("настройка «Разрешить агенту стартовать Creo» (creo_allow_start) = %r" % settings.get("creo_allow_start"))
out.append("creo_running() сейчас (CREOSON может быть выключен) = %r" % C.creo_running())
g = C._creo_gate("file", "list_files")
out.append("вентиль на ЧТЕНИЕ файлов при выключенном Creo: %s" % ("БЛОКИРУЕТ — правильно" if g else "пропускает (не должен!)"))
if g:
    out.append("  текст, который увидит агент: " + g[:150])
g2 = C._creo_gate("connection", "start_creo")
out.append("явная команда start_creo: %s" % ("пропускается (это просьба человека, только под согласованием)" if g2 is None else "заблокирована"))
out.append("connect() без живого Creo -> %r (пусто = сессию не открываем, значит Creo не поднимется)" % C.connect())
open(r"D:\AI\log\reports\creo_gate_check.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
