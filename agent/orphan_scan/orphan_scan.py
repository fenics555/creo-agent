import os
import re
import sqlite3
import sys
import time
from datetime import datetime

# Константы
CREO_EXT_PATTERN = re.compile(r"\.(drw|drw\.\d+)$", re.I)
DB_AGENT = r"D:\AI\tools\agent\data\agent.sqlite"
DB_HARVEST = r"D:\AI\tools\agent\data\harvest.db"
SEARCH_PRO = r"Z:\PTC\Work\search.pro"
WORK_ROOT = r"Z:\PTC\Work"       # эталон «верхней папки» для распределения сирот
LOG_DIR = r"D:\AI\log\orphan_scan"
REPORT_DIR = r"D:\AI\log\reports"
REPORT_PREFIX = "REPORT_orphan_scan"          # имя отчёта не привязано к номеру спеки
# Закон трёх рук (манифест п.19): настройки окна живут в data\, рядом с остальными настройками дома
SETTINGS_PATH = r"D:\AI\tools\agent\data\orphan_scan_settings.json"
LEGACY_SETTINGS = r"D:\AI\tools\agent\orphan_scan\gui_settings.json"   # переносится при первом чтении

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
        self.progress = None       # приёмник строк для окна
        self._stop = False         # флаг мягкой остановки (кнопка СТОП окна)

    def request_stop(self):
        """Мягкая остановка обхода. Живая проверка 02.10.2026: присваивание
        `self.roots = []` НЕ прерывает `for root in self.roots` — цикл уже держит
        итератор (roots_visited=3 из 3), поэтому флаг проверяется в теле цикла."""
        self._stop = True

    def _reset(self):
        """Сброс накопленного состояния. Живая проверка 02.10.2026: повторный scan()
        на одном экземпляре удваивал счётчики (5 → 10 чертежей)."""
        self.stats = {"total_drawings": 0, "not_orphan": 0,
                      "model_elsewhere": 0, "orphan": 0}
        self.orphans = []
        self.model_elsewhere_list = []
        self.distribution = {}
        self._stop = False

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
            self._say("ошибка: %s не найден" % SEARCH_PRO)
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
            self._say("ошибка: %s не читается (кодировка?)" % SEARCH_PRO)
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
        self._reset()
        self.roots = list(roots) if roots else self.get_roots(argv)
        if not self.roots:
            self._say("No roots to scan.")
            return
        self._say("инвентарь моделей: подключаю базы (agent.sqlite + harvest.db)")
        self._load_inventory()
        self._say("моделей в инвентаре: %d" % len(self.inventory or ()))

        for root in self.roots:
            if self._stop:          # кнопка СТОП окна: выход из обхода (живая проверка 02.10.2026)
                self._say("остановка по запросу окна")
                break
            self._say("Scanning: %s" % root)
            for dirpath, _, filenames in os.walk(root):
                if self._stop:
                    break
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
                            rel_path = os.path.relpath(full_path, WORK_ROOT)
                            top_folder = rel_path.split(os.sep)[0] or "Unknown"
                        except ValueError:
                            top_folder = "вне %s" % WORK_ROOT
                        self.distribution[top_folder] = self.distribution.get(top_folder, 0) + 1

    def run_report(self):
        """Пишет лог прогона и отчёт. Имя отчёта больше не привязано к номеру спеки
        (живая правка 02.10.2026: было REPORT_spec113_local_leg_* — спека закрыта,
        и новое имя ломало бы поиск «последнего отчёта» в окне).
        ПОЛНЫЙ список сирот идёт отдельным .txt: 50 строк в .md не годятся для разбора."""
        os.makedirs(LOG_DIR, exist_ok=True)
        os.makedirs(REPORT_DIR, exist_ok=True)

        stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")   # секунды: два прогона
        log_file = os.path.join(LOG_DIR, f"run_{stamp}.txt")   # в одну минуту больше не сливаются
        report_file = os.path.join(REPORT_DIR, "%s_%s.md" % (REPORT_PREFIX, stamp))
        list_file = os.path.join(LOG_DIR, f"orphans_{stamp}.txt")
        stopped = " (остановлено по запросу)" if self._stop else ""

        # Полный список сирот — отдельным файлом (в .md попадают первые 50).
        with open(list_file, "w", encoding="utf-8") as f_lst:
            for p in self.orphans:
                f_lst.write(p + "\n")
            for p in self.model_elsewhere_list:
                f_lst.write("модель в другом месте\t" + p + "\n")

        with open(log_file, "w", encoding="utf-8") as f_log:
            f_log.write(f"=== ORPHAN SCAN RUN: {stamp}{stopped} ===\n")
            f_log.write(f"Roots: {self.roots}\n\n")

            with open(report_file, "w", encoding="utf-8") as f_rep:
                f_rep.write(f"# Отчёт: Поиск чертежей-сирот{stopped}\n")
                f_rep.write(f"**Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                f_rep.write(f"**Инструмент:** orphan_scan (класс Р, только чтение)\n\n")
                
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
                        f_rep.write(f"\n*... и ещё {len(self.orphans)-50} сирот; "
                                    f"полный список — `{list_file}`.*\n")
                f_rep.write("\n")

                f_rep.write("## 4. Корни прогона\n")
                for r in self.roots[:20]:
                    f_rep.write("- `%s`\n" % r)
                if len(self.roots) > 20:
                    f_rep.write("- …и ещё %d корней\n" % (len(self.roots) - 20))
                f_rep.write("\n## 5. Откуда что взято\n")
                f_rep.write(f"- корни: {len(self.roots)} "
                            f"(свёрнуты: вложенные папки не обходятся дважды)\n")
                f_rep.write(f"- инвентарь моделей: {len(self.inventory or ())} базовых имён "
                            f"из `{DB_AGENT}:models` и `{DB_HARVEST}:models_raw` (только чтение)\n")
                f_rep.write(f"- пути поиска Creo: `{SEARCH_PRO}`\n")
                f_rep.write(f"- эталон верхней папки для распределения: `{WORK_ROOT}`\n")
                f_rep.write(f"- журнал прогона: `{log_file}`\n")
                f_rep.write(f"- полный список сирот: `{list_file}`\n\n")
                f_rep.write("*Приёмку делает первая нога своими командами: контрольные случаи — "
                            "`приваи` (сирота), `ыва` (не сирота), `00-06` (сирота).*\n\n")

                f_rep.write("--- \n*Отчёт сформирован инструментом orphan_scan*\n")

            f_log.write(f"Total drawings: {self.stats['total_drawings']}\n")
            f_log.write(f"Orphans: {self.stats['orphan']}\n")
            f_log.write(f"Model elsewhere: {self.stats['model_elsewhere']}\n")
            f_log.write(f"Not orphan: {self.stats['not_orphan']}\n")
            f_log.write(f"Report: {report_file}\n")
            f_log.write(f"Orphan list: {list_file}\n")

        self._say(f"готово: отчёт {report_file}")
        self._say(f"полный список сирот: {list_file}")
        return report_file

if __name__ == "__main__":
    scanner = OrphanScanner()
    start_time = time.time()
    scanner.scan(sys.argv[1:])
    if not scanner.roots:
        # было: тихий выход с кодом 0 — планировщик и агент считали прогон успешным
        scanner._say("НЕЧЕГО ПРОВЕРЯТЬ: корни не заданы и не найдены "
                     "(проверьте путь или %s)" % SEARCH_PRO)
        sys.exit(2)
    scanner.run_report()
    scanner._say(f"время: {time.time() - start_time:.2f} с")

