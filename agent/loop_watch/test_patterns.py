# -*- coding: utf-8 -*-
# ПРОГОН ВСЕХ ПРИЗНАКОВ сторожа на СЕБЕ (синтетические сессии)
import sys, io
sys.path.insert(0, r'D:\AI\tools\agent\loop_watch')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import loop_watch as LW

def test(name, calls, msgs):
    r = LW.pattern_loop(calls, msgs)
    cl = LW.cycle_loop(calls)
    print("%-16s | pattern_loop=%s | cycle=%s" % (name, r, cl))

# 1. edit-miss (text not found ×2)
test("edit-miss", [("editor", "Error: text not found in file"), ("editor", "text not found")], [])
# 2. edit-big
test("edit-big", [("editor", "Editor input too large"), ("editor", "too large")], [])
# 3. migration
test("migration", [("search_codebase", "[migration] Tool result missing"), ("search_codebase", "[migration] x")], [])
# 4. path-guess
test("path-guess", [("run_commands", "PathNotFound: D:\\AI\\foo"), ("run_commands", "PathNotFound")], [])
# 5. buffer
test("buffer", [("run_commands", "(пусто)"), ("run_commands", "(пусто)")], [])
# 6. context-death
test("context-death", [("read_files", "context length exceeded"), ("read_files", "context length")], [])
# 7. plan-loop (3 текста с «план» без «вызов»)
test("plan-loop", [], [{"role": "assistant", "content": "план: сначала читаю файл"},
                       {"role": "assistant", "content": "план: сначала читаю файл"},
                       {"role": "assistant", "content": "план: сначала читаю файл"}])
# 8. чистая сессия (не должно быть срабатываний)
test("чисто", [("run_commands", "ok output"), ("editor", "edited fine")], [{"role": "assistant", "content": "готово"}])
