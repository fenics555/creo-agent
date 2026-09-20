import os

files_to_write = {
    r'D:\AI\repo\PROGRESS_spec101.md': """# PROGRESS SPEC 101 «Harvest GUI Module»
НОГИ: <нога 1 — Cline — 20.09.2026, нога 2 — Cline — 20.09.2026>
SPEC: <not created>
STATUS: ЗАВЕРШЕНА

## Ф1 <нога 1, Cline, 20.09.2026>
СДЕЛАНО: 
- Снято противоречие в скиллах (verbatim prophylaxis).
- Восстановлена целостность `harvest_gui.py`.
- Реализован `harvest_gui.py` (thin module).
- Пройдены все пробы (py_compile, import, settings, badge).
- Сделаны коммиты и GIT_SYNC.
НЕ СДЕЛАНО: —
ЯКОРЬ: everything is committed and synced.
ПЛАН: —

## Ф2 <нога 2, Cline, 20.09.2026>
СДЕЛАНО:
- Verbatim prophylaxis implemented in skills.
- Fixed skill counters.
- Verified Cyrillic integrity in `harvest_gui.py`.
- All files synced.
НЕ СДЕЛАНО: —
ЯКОРЬ: everything is committed and synced.
ПЛАН: —

=== END ===""",
    r'D:\AI\log\reports\REPORT_spec101_Cline_20.09.2026.md': """# REPORT SPEC 101 (Cline)
Date: 20.09.2026

## 1. Resolve Contradictions
- Fixed `SKILL_editor_too_large.md` and `SKILL_crash_editor_context_mismatch.md` with verbatim prophylaxis.
- Set `ПОВТОРЫ: 5;` in `SKILL_editor_too_large.md`.

## 2. Restoration & Integrity
- Restored `D:\\AI\\tools\\agent\\harvest_gui.py` via `git checkout`.
- Verified `harvest_gui_panels.py` and `harvest_gui.py` via `py_compile`.
- Confirmed `data\\harvest_settings.json` is correct.
- Ran `ui_check.py` -> **ALL GREEN**.
- Probes:
    - Import without mainloop: OK.
    - Round-trip settings: OK.
    - Badge on stale-lock: OK (showed READY).

## 3. Spec 101 Implementation
- Created `D:\\AI\\tools\\agent\\harvest_gui.py` (thin window module).
- Committed changes to `D:\\AI\\tools` (hash `8d96215`) and `D:\\AI\\repo` (hash `36ab449`).

## 4. Status
- DONE.

## 5. Final Verification & Cleanup
- Verified Cyrillic string: `self.update_badge(f"ИДЁТ СБОР (PID {pid})" if pid else "READY")` (line 63) is active.
- Skills prophylaxis updated to strict law.
- All files (harvest_gui.py, harvest_gui_panels.py, skills) are committed and synced.
"""
}

def main():
    for path, content in files_to_write.items():
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Successfully wrote: {path}")
        except Exception as e:
            print(f"Failed to write {path}: {e}")

if __name__ == "__main__":
    main()
