import users
import json
from pathlib import Path

UFILE = Path(r"D:\AI\tools\agent\data\users.json")

def reset_admin_pw(new_pw):
    d = json.loads(UFILE.read_text(encoding="utf-8"))
    found = False
    for u in d["users"]:
        if u["login"] == "admin":
            import hashlib, secrets
            salt = secrets.token_hex(8)
            h = hashlib.pbkdf2_hmac("sha256", (new_pw).encode("utf-8"), salt.encode("utf-8"), 120000).hex()
            u["salt"] = salt
            u["hash"] = h
            found = True
            break
    if found:
        with open(UFILE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        print("Admin password reset successfully.")
    else:
        print("Admin user not found.")

if __name__ == "__main__":
    reset_admin_pw("1945")
