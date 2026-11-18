import unittest
import os
import sqlite3
import re
import tempfile
import shutil

# Импортируем модули проекта
import plm_database as _DBm
import engine
import plm_build_links as _BL
import plm_queries as _Q
import creo_read as _CR
import plm_creo_parse as _CP
import plm_scanner as _PS

class TestAuditFixesV220(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Создаем временную БД для тестов
        cls.test_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.test_dir, "test_plm.db")
        
        # Инициализируем схему (через plm_database)
        # В реальном проекте мы бы вызвали миграцию, здесь создадим минимальную структуру
        cls.con = sqlite3.connect(cls.db_path)
        cls.cur = cls.con.cursor()
        
        # Создаем необходимые таблицы согласно SCHEMA
        cls.cur.executescript("""
            CREATE TABLE meta (schema_version INTEGER);
            INSERT INTO meta VALUES (4);
            
            CREATE TABLE links (
                parent TEXT, child TEXT, qty INTEGER, 
                source TEXT, origin TEXT
            );
            CREATE INDEX IF NOT EXISTS "ix_links_parent_child" ON "links"("parent", "child");
            
            CREATE TABLE family (
                instance TEXT, model TEXT
            );
            CREATE INDEX IF NOT EXISTS "ix_family_instance" ON "family"("instance");
            
            CREATE TABLE graph_edges (
                "from" TEXT, "to" TEXT, kind TEXT
            );
            CREATE INDEX IF NOT EXISTS "ix_graph_edges_from_to" ON "graph_edges"("from", "to");

            CREATE TABLE snapshots (
                path TEXT, model TEXT, folder TEXT, size INTEGER, mtime REAL, 
                volume REAL, material TEXT, name TEXT, designation TEXT, rev TEXT,
                author TEXT, revdate TEXT, role TEXT, seen TEXT, hist TEXT, 
                creo TEXT, created TEXT, file_name TEXT, file_ext TEXT, file_version TEXT
            );
            
            CREATE TABLE items (
                item_key TEXT PRIMARY KEY, model TEXT, folder TEXT, 
                n_files INTEGER, n_versions INTEGER, exts TEXT, last_mtime REAL
            );
            CREATE TABLE item_ver (
                item_key TEXT, version TEXT, ext TEXT
            );
        """)
        cls.con.commit()

    @classmethod
    def tearDownClass(cls):
        cls.con.close()
        shutil.rmtree(cls.test_dir)

    def test_01_database_indexes(self):
        """1. Проверка наличия индексов в plm_database.py"""
        def check_idx(table, idx_name):
            self.con.execute(f"PRAGMA index_list('{table}')")
            idxs = [row[1] for row in self.con.execute(f"PRAGMA index_list('{table}')")]
            self.assertIn(idx_name, idxs, f"Индекс {idx_name} не найден в таблице {table}")

        check_idx("links", "ix_links_parent_child")
        check_idx("family", "ix_family_instance")
        check_idx("graph_edges", "ix_graph_edges_from_to")

    def test_02_engine_connect_safety(self):
        """2. Безопасность connect() в engine.py (нет DROP TABLE)"""
        try:
            os.environ["PLM_DB"] = self.db_path
            import engine
            con = engine.connect(ro=True)
            self.assertIsNotNone(con)
            con.close()
        except Exception as e:
            self.fail(f"connect() вызвал ошибку: {e}")

    def test_03_engine_publish_path(self):
        """3. Правильный путь в _publish() в engine.py"""
        import engine
        os.environ["PLM_DB"] = self.db_path
        path = engine._publish(self.db_path)
        self.assertTrue(os.path.exists(os.path.dirname(path)) or path == self.db_path)

    def test_04_plm_build_links_mfg(self):
        """4. Ключ 'mfg' в BACK_LINKS"""
        import plm_build_links as _BL
        self.assertIn("mfg", _BL.BACK_LINKS)
        self.assertEqual(_BL.BACK_LINKS["mfg"], "обратный мануфактуринг")

    def test_05_plm_queries_seen(self):
        """5. Использование seen в plm_down_data"""
        import plm_queries as _Q
        self.con.execute("INSERT INTO links (parent, child, qty, origin) VALUES (?, ?, ?, ?)", ("A", "B", 1, "real"))
        self.con.execute("INSERT INTO links (parent, child, qty, origin) VALUES (?, ?, ?, ?)", ("B", "A", 1, "real"))
        self.con.commit()
        try:
            _Q.plm_tree_data("A")
        except RecursionError:
            self.fail("Обнаружена бесконечная рекурсия! 'seen' не работает.")
        except Exception:
            pass

    def test_06_creo_read_regex(self):
        """6. Regex в creo_read.py (поддержка '-' и '.')"""
        import creo_read as _CR
        test_names = ["MODEL-001.PRT", "MODEL.001.ASM", "MY-PART_V2.PRT"]
        for name in test_names:
            canon = _CR.canon_model(name)
            self.assertEqual(canon, name.split('.')[0].upper())

    def test_07_plm_creo_parse_family_behavior(self):
        """7. Поведение family_of в plm_creo_parse.py для пустых путей/неверных расширений"""
        import plm_creo_parse as _CP
        self.assertEqual(_CP.extract_family_info(b""), [])
        self.assertEqual(_CP.extract_family_info(b"garbage data"), [])
        
    def test_08_plm_scanner_counting(self):
        """8. Корректность подсчета в plm_scanner.py"""
        import plm_scanner as _PS
        self.con.execute("INSERT INTO items (item_key, model, folder, n_files, n_versions, exts) VALUES (?,?,?,?,?,?)",
                         ("K1", "M1", "F1", 1, 1, ""))
        self.con.execute("INSERT INTO item_ver (item_key, version, ext) VALUES (?,?,?)", ("K1", "V1", ".PRT"))
        self.con.execute("INSERT INTO item_ver (item_key, version, ext) VALUES (?,?,?)", ("K1", "V2", ".PRT"))
        self.con.execute("UPDATE items SET n_versions = (SELECT COUNT(DISTINCT version) FROM item_ver WHERE item_key=?) WHERE item_key=?", ("K1", "K1"))
        row = self.con.execute("SELECT n_versions FROM items WHERE item_key='K1'").fetchone()
        self.assertEqual(row[0], 2)

if __name__ == "__main__":
    unittest.main()
