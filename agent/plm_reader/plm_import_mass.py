# -*- coding: utf-8 -*-
r"""
plm_import_mass.py — дозаливка базы ПЛМ из прохода plm_scan_out.json
  (1) params += MASS / PRO_MP_VOLUME / PRO_MP_AREA / PRO_MP_DENSITY (числа из файла Creo)
  (2) history += чистые записи истории .drw (action='first'/'last', rev='N/M')
  (3) ЧИСТКА мусора history.creo ('\x03Proe_version' -> '')
ТОЛЬКО запись в plm_reader.db. БЭКАП ДЕЛАТЬ ДО ЗАПУСКА:
  Copy-Item db\plm_reader.db db\backup\plm_reader_<дата>_pre_mass.db
Канон: SKILL_GRABLI.md §167 (масса) · §169 (история) · §170 (конвейер).
"""
import json, sqlite3, time, os

HERE = os.path.dirname(os.path.abspath(__file__))
DB   = os.path.join(HERE, "db", "plm_reader.db")
JSN  = r"D:\AI\PROBA\plm_scan_out.json"


def model_of(rec):
    """Имя модели = из 'file' (без .prt.N/.drw.N), иначе из 'path'."""
    f = rec.get("file") or ""
    for ext in (".prt", ".asm", ".drw", ".mfg", ".frm", ".lay", ".sec"):
        i = f.lower().find(ext)
        if i > 0:
            return f[:i]
    return rec.get("path", "").split("\\")[-1].rsplit(".", 1)[0]


def main():
    t0 = time.time()
    D = json.load(open(JSN, encoding="utf-8"))
    prt = D.get("prt", [])
    drw = D.get("drw", [])
    print(f"ВХОД: prt={len(prt)}  drw={len(drw)}")

    c = sqlite3.connect(DB)
    cur = c.cursor()

    # --- 1) МАССА / ОБЪЁМ / ПЛОЩАДЬ / ПЛОТНОСТЬ в params ---
    rows = []
    for r in prt:
        p = r.get("path"); m = model_of(r)
        if not p or "mass_kg" not in r:
            continue
        rows.append((p, m, "MASS", "num", str(r["mass_kg"])))
        if "volume_mm3" in r:
            rows.append((p, m, "PRO_MP_VOLUME", "num", str(r["volume_mm3"])))
        if "area_mm2" in r:
            rows.append((p, m, "PRO_MP_AREA", "num", str(r["area_mm2"])))
        if "rho" in r:
            rows.append((p, m, "PRO_MP_DENSITY", "num", str(r["rho"])))

    cur.execute("DELETE FROM params WHERE name IN ('MASS','PRO_MP_VOLUME','PRO_MP_AREA','PRO_MP_DENSITY')")
    cur.executemany("INSERT INTO params(path,model,name,type,value) VALUES(?,?,?,?,?)", rows)
    print(f"params: +{len(rows)} строк")

    # --- 2) ИСТОРИЯ .drw: 2 записи на файл (первая правка + последняя) ---
    hrows = []
    for r in drw:
        p = r.get("path"); m = model_of(r)
        cnt = r.get("hist_count") or 0
        if not p or not cnt:
            continue
        u = r.get("user_name") or ""
        if r.get("hist_first"):
            hrows.append((p, m, r["hist_first"], u, "", "", f"1/{cnt}", "first"))
        if r.get("hist_last") and r.get("hist_last") != r.get("hist_first"):
            hrows.append((p, m, r["hist_last"], u, "", "", f"{cnt}/{cnt}", "last"))
    if hrows:
        paths = tuple({h[0] for h in hrows})
        for i in range(0, len(paths), 500):
            chunk = paths[i:i+500]
            cur.execute("DELETE FROM history WHERE path IN (%s)" % ",".join("?"*len(chunk)), chunk)
        cur.executemany(
            "INSERT INTO history(path,model,ts,user,computer,creo,rev,action) VALUES(?,?,?,?,?,?,?,?)",
            hrows)
    print(f"history: +{len(hrows)} строк (.drw, {len({h[0] for h in hrows})} файлов)")

    # --- 3) ЧИСТКА мусора creo ---
    cur.execute("UPDATE history SET creo='' WHERE creo LIKE '%Proe_version%' OR creo LIKE '%\x03%'")
    print(f"history: очищено мусорных creo = {cur.rowcount}")

    c.commit()
    c.close()
    print(f"ГОТОВО за {time.time()-t0:.1f} с")


if __name__ == "__main__":
    main()
