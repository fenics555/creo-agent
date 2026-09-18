import re

path = r'D:\AI\tools\agent\http_handlers.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the /log block and fix it
# We want to replace everything from elif p == "/log": to the next elif
pattern = r'elif p == "/log":.*?elif p == "/settings":'
replacement = """        elif p == "/log":
            try:
                with open(core.LOGF, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                    tail = "".join(lines[-100:])
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(tail.encode("utf-8"))
            except Exception as e:
                self._j({"error": str(e)}, 500)
        elif p == "/settings":"""

# Using DOTALL to match across lines
new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Indentation fixed")
