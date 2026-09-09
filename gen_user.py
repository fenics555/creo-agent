import secrets, hashlib, time
from pathlib<io> import Path

# Копия логики из users.py для генерации
def _hash(pw, salt):
    return hashlib.pbkdf2_hmac("sha256", (pw or "").encode("utf-8"), salt.encode("utf-8"), 120000).hex()

login = "qa_bot_admin"
pw = "QaBot2_2026"
role = "Администратор"
salt = secrets.token_hex(8)
h = _hash(pw, salt)

print(f'{{"login": "{login}", "salt": "{salt}", "hash": "{h}", "display_name": "{login}", "role": "{role}", "created": "2026-09-09 12:00", "last_seen": ""}}')
