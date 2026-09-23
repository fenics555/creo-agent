import os
import re
import sqlite3
import sys
import time
from datetime import datetime

# Константы
CREO_EXT_PATTERN = re.compile(r"\.(drw|drw\.\d+)$", re.I)
MODEL_EXT_PATTERN = re.compile(r"\.(prt|asm)(\.\d+)?$", re.I)
DB_AGENT = r"D:\AI\tools\agent\data\agent.sqlite"
DB_HARVEST = r"D:\AI\tools\agent\data\harvest.db"
SEARCH_PRO = r"Z:\PTC\Work\search.pro"
LOG_DIR = r"D:\AI\log\orphan_scan"
REPORT_DIR = r"D:\AI\log\reports"

def BASE_OF(fn):
    """Базовое имя модели: `00080-03-z.prt.1` → `00080-03-z` (регистр не важен).
    ВАЖНО: в базах дома имена хранятся С ВЕРСИЕЙ и расширением — сравнивать надо базовые."""
    return re.sub(r"\.(prt|asm|drw|frm|sec|lay)(\.\d+)?$", "", str(fn).lower(), flags=re.I).strip()


class OrphanScanner:
    def __init__(self):
        self.stats = {
            "total_drawings": 0,
            "not_orphan": 0,
            "model_elsewhere": 0,
            "orphan": 0
        }
        self.orphans = []
        self.model_elsewhere_list = []
        self.distribution = {}
        self.roots = []
        
        # Инициализация баз (лениво)
        self.conn_agent = None
        self.conn_harvest = None
        self.inventory = None      # множество БАЗОВЫХ имён моделей (ленивая загрузка)

    def _say(self, s):
        """Печать, безопасная для окна: в pythonw `sys.stdout` = None, и обычный print падает."""
        try:
            if sys.stdout:
                print(s)
        except Exception:
            pass
        if getattr(self, "progress", None):
            try:
                self.progress(s)
            except Exception:
                pass

    def _connect_db(self):
        if self.conn_agent is None:
            try:
                self.conn_agent = sqlite3.connect(DB_AGENT)
            except Exception as e:
                self._say("Error connecting to agent.sqlite: %s" % e)
        if self.conn_harvest is None:
            try:
                self.conn_harvest = sqlite3.connect(DB_HARVEST)
            except Exception as e:
                self._say("Error connecting to harvest.db: %s" % e)

    def _load_inventory(self):
        """Собирает БАЗОВЫЕ имена моделей из обеих баз (один раз).
        В базах имя хранится с версией и расширением (`x.prt.1`) — прямое сравнение
        с `x` не работает (проверено 23.09.2026: точное совпадение давало 0)."""
        if self.inventory is not None:
            return
        self.inventory = set()
        self._connect_db()
        for conn, table in ((self.conn_agent, "models"), (self.conn_harvest, "models_raw")):
            if not conn:
                continue
            try:
                for (n,) in conn.execute("SELECT name FROM %s" % table):
                    if not n:
                        continue
                    low = str(n).lower()
                    # только МОДЕЛИ (prt/asm): чертежи в базе — это сам проверяемый файл,
                    # иначе каждый чертёж «находил» бы себя и сирот не стало бы вовсе
                    if re.search(r"\.(prt|asm)(\.\d+)?$", low):
                        self.inventory.add(BASE_OF(low))
            except Exception as e:
                self._say("inventory %s: %s" % (table, e))

    def _name_in_inventory(self, name):
        """Есть ли базовое имя модели в инвентаре (agent.sqlite или harvest.db)."""
        if not name:
            return False
        self._load_inventory()
        return name.strip().lower() in self.inventory

    @staticmethod
    def _collapse(roots):
        """Убираем вложенные корни: search.pro содержит 4099 папок, и обход каждой
        рекурсивно обошёл бы одни и те же подкаталоги многократно."""
        uniq = {}
        for r in roots:
            n = os.path.normpath(r)
            uniq.setdefault(n.lower(), n)
        out = []
        for r in sorted(uniq.values(), key=len):
            rl = r.lower().rstrip("\\") + "\\"
            if any(rl.startswith(kept.lower().rstrip("\\") + "\\") for kept in out):
                continue
            out.append(r)
        return out

    def get_roots(self, argv=None):
        if argv:
            # Если переданы аргументы, используем их
            roots = [arg.replace('"', '') for arg in argv if os.path.isdir(arg.replace('"', ''))]
            self.roots = self._collapse(roots)
            return self.roots
        
        if not os.path.exists(SEARCH_PRO):
            print(f"Error: {SEARCH_PRO} not found.")
            return []
        
        # search.pro дома в cp1251 (проверено 23.09.2026: чтение как utf-8 падало UnicodeDecodeError)
        with open(SEARCH_PRO, 'rb') as f:
            raw = f.read()
        text = None
        for enc in ('utf-8', 'cp1251'):
            try:
                text = raw.decode(enc)
                break
            except Exception:
                continue
        if text is None:
            print(f"Error: {SEARCH_PRO} — не читается (кодировка?)")
            return []
        for line in text.splitlines():
            path = line.strip().strip('"')
            if path and not path.startswith('#') and os.path.isdir(path):
                self.roots.append(path)
        self.roots = self._collapse(self.roots)
        return self.roots

    def scan(self, argv=None, roots=None, progress=None):
        """Обход и классификация чертежей. `roots` — явный список папок (для окна),
        `progress` — функция-приёмник строк (для окна). Без аргументов — как раньше: по argv/search.pro."""
        self.progress = progress
        self.roots = list(roots) if roots else self.get_roots(argv)
        if not self.roots:
            self._say("No roots to scan.")
            return
        self._say("инвентарь моделей: подключаю базы (agent.sqlite + harvest.db)")
        self._load_inventory()
        self._say("моделей в инвентаре: %d" % len(self.inventory or ()))

        for root in self.roots:
            self._say("Scanning: %s" % root)
            for dirpath, _, filenames in os.walk(root):
                for fn in filenames:
                    match = CREO_EXT_PATTERN.search(fn)
                    if not match:
                        continue
                    
                    self.stats["total_drawings"] += 1
                    full_path = os.path.join(dirpath, fn)
                    
                    # Базовое имя X из X.drw[.N]
                    ext_len = len(match.group(0))
                    base_name = fn[:-ext_len]
                    
                    # 1. Проверка модели рядом — ТОЧНОЕ имя (не префикс: 00-06 ≠ 00-06-другое)
                    rx_local = re.compile(r"^" + re.escape(base_name) + r"\.(prt|asm)(\.\d+)?$", re.I)
                    has_local_model = any(rx_local.match(f) for f in os.listdir(dirpath))
                    
                    if has_local_model:
                        self.stats["not_orphan"] += 1
                        continue
                    
                    # 2. Если локальной нет, проверяем инвентарь
                    if self._name_in_inventory(base_name):
                        self.stats["model_elsewhere"] += 1
                        self.model_elsewhere_list.append(full_path)
                    else:
                        self.stats["orphan"] += 1
                        self.orphans.append(full_path)
                        
                        # Распределение по верхним папкам (000_...)
                        # Распределение по верхним папкам (000_...). Живая находка 23.09.2026: relpath падает,
                        # если папка не на диске Z: (ValueError «path is on mount 'D:', start on mount 'Z:'»),
                        # а окно программы умеет проверять ЛЮБУЮ папку — поэтому считаем безопасно.
                        try:
                            rel_path = os.path.relpath(full_path, r"Z:\PTC\Work")
                            top_folder = rel_path.split(os.sep)[0] or "Unknown"
                        except ValueError:
                            top_folder = "вне Z:\\PTC\\Work"
                        self.distribution[top_folder] = self.distribution.get(top_folder, 0) + 1

    def run_report(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        os.makedirs(REPORT_DIR, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        log_file = os.path.join(LOG_DIR, f"run_{timestamp}.txt")
        report_file = os.path.join(REPORT_DIR,
                                   "REPORT_spec113_local_leg_%s.md" % datetime.now().strftime("%Y-%m-%d_%H%M"))
        
        with open(log_file, "w", encoding="utf-8") as f_log:
            f_log.write(f"=== ORPHAN SCAN RUN: {timestamp} ===\n")
            f_log.write(f"Roots: {self.roots}\n\n")
            
            with open(report_file, "w", encoding="utf-8") as f_rep:
                f_rep.write(f"# Отчёт: Поиск чертежей-сирот\n")
                f_rep.write(f"**Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
                
                f_rep.write("## 1. Сводная статистика\n")
                f_rep.write(f"- Всего чертежей: {self.stats['total_drawings']}\n")
                f_rep.write(f"- Не сироты (модель рядом): {self.stats['not_orphan']}\n")
                f_rep.write(f"- Модель в другом месте (есть в базе): {self.stats['model_elsewhere']}\n")
                f_rep.write(f"- **ЧЕРТЕЖИ-СИРОТЫ (нет модели): {self.stats['orphan']}**\n\n")
                
                f_rep.write("## 2. Распределение сирот по папкам\n")
                for folder, count in sorted(self.distribution.items()):
                    f_rep.write(f"- `{folder}`: {count}\n")
                f_rep.write("\n")

                if self.orphans:
                    f_rep.write("## 3. Первые 50 сирот\n")
                    for p in self.orphans[:50]:
                        f_rep.write(f"- `{p}`\n")
                    if len(self.orphans) > 50:
                        f_rep.write(f"\n*... и ещё {len(self.orphans)-50} сирот.*\n")
                f_rep.write("\n")

                f_rep.write("## 4. Корни прогона\n")
                for r in self.roots[:20]:
                    f_rep.write("- `%s`\n" % r)
                if len(self.roots) > 20:
                    f_rep.write("- …и ещё %d корней\n" % (len(self.roots) - 20))
                f_rep.write("\n*Приёмку делает первая нога своими командами: контрольные случаи — "
                            "`приваи` (сирота), `ыва` (не сирота), `00-06` (сирота).*\n\n")
                
                f_rep.write("--- \n*Отчёт сформирован инструментом orphan_scan*\n")

            f_log.write(f"Total drawings: {self.stats['total_drawings']}\n")
            f_log.write(f"Orphans: {self.stats['orphan']}\n")
            f_log.write(f"Model elsewhere: {self.stats['model_elsewhere']}\n")
            f_log.write(f"Not orphan: {self.stats['not_orphan']}\n")
            f_log.write(f"Report: {report_file}\n")

        print(f"Done! Report: {report_file}")

if __name__ == "__main__":
    scanner = OrphanScanner()
    start_time = time.time()
    scanner.scan(sys.argv[1:])
    scanner.run_report()
    print(f"Time taken: {time.time() - start_time:.2f}s")

