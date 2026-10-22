# 📓 Session Log: Creo Reverse Engineering
## Date: 21.10.2026

### ❌ Crashes & Errors
- **PowerShell Syntax**: `dir` failed in `run_commands`.
- **Editor Limit**: `old_text` failed for files >6KB.
- **Python Syntax Error**: `'return' outside function` caused by fragmented `editor` calls.

### 💡 Lessons Learned (Skill-rakes)
1.  **Use PowerShell explicitly**: `powershell -Command "..."` is safer.
2.  **Full Rewrite for Large Files**: Avoid `old_text` for files near the 6KB limit.
3.  **Atomic File Writing**: When building a class, write the whole block to avoid indentation/scope hell.

---
*Status: Recovering from SyntaxError. Ready to re-run orchestration.*
