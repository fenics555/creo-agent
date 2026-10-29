# STATE — ЖИВОЕ СОСТОЯНИЕ PLM READER (обновлять при КАЖДОМ шаге)

> Правило: «Сессия смертна. Всё, что не в файле — потеряно». Три строки, дата замера,
> источник каждого утверждения. Версия формата — 28.10.2026 (предложение эстафеты, §3 «чего не хватает»).

**Обновлено:** 29.10.2026, фаза 15 · нога Cline (НАЙДЕНА КАРТА ПОЛЕЙ в файле + карта мануфактуринга `F8..F7 16`)

```
на диске:  engine.py (CREO_EXTS 167-170, role_by_path 707/719, _base_dir 1113), creo_read.py (role by ext 224/243),
           STRATEGY_PLM.md §2.2+§2.3+§2.4 (276), AGENTS.md правила 5-6, version.json V140/22 (замер RESULT: OK)
в git:     tools master 1801c42 (впереди origin на 7 коммитов, push не делал) + repo 352354c (GRABLI 102-105, карта);
           git status чист, кроме ?? _s.txt — per-run вывод смоука, НАМЕРЕННО вне git
работает:  скан склада 3.6 с (new/skip/errors в результате), публикация в папку active_db(), роли по расширению,
           приёмка _smoke_v87.py → SMOKE OK + «ЦЕЛОСТНОСТЬ ПОСТАВКИ» (22 файла, все SHA256)
не работает: значения family-таблицы (в библиотечных файлах их нет — только имена), размеры dN из байтов
           (только J-Link), plm_links.py НЕ внедрён (расчёт: 38 мест построения связей), мусор links 22 646 строк
не сделано: DELETE мусора в links (только по слову владельца); built 23 240 из 92 963 (25 %)
СЕТ НА ПРОВЕРКУ — ИСПОЛНЯЕМЫЙ: `python _test_set.py` (9 файлов, 32 проверки, 0 записи; `--neg` обязан
           упасть). ВХОДИТ В ПРИЁМКУ `_smoke_v87.py` перед SMOKE OK. Пути сета — STRATEGY §2.5
КИРИЛЛИЦА — ЛЕЧЕНА И РАБОТАЕТ (проверено 28.10): engine.asm_components(цткд_437_001.asm.1) = 5 компонентов,
           в т.ч. ЦТКД_437_001_Z (заготовка, 9). Кодировка имён = UTF-8 (не cp1251). creo_read.names() = {} —
           ЗАКОННО (канал состава выброшен, engine.py:3033); судить по нему НЕЛЬЗЯ (была ошибка замера).
ДЕРЕВО И РАЗМЕРЫ (эталон J-Link, `tools\agent\creo_export\tree_probe.bat`, Creo запущен):
           g22033 = 9 элементов / 8 размеров; ctkd_015_23_001 = 19 / 40. Типы элементов — числами ТОЛЬКО
           ЧЕРЕЗ J-LINK (TYPE_13 — плоскости, TYPE_1 — тела): в ФАЙЛАХ Электона `TYPE_13`/`TYPE_6/7/16`
           = 0 вхождений (замер 29.10.2026, 323 файла), а `TYPE_1/2/3` в файле = тип РАЗМЕРА
           (линейный 571 / радиус 25 / угол 67), не вид элемента. Имена операций В ФАЙЛЕ по-русски:
           ВЫТЯГИВАНИЕ 9 (= Creo 9!), СКРУГЛЕНИЕ 4, ВРАЩЕНИЕ 1, ОПОРНАЯ ПЛОСКОСТЬ 31.
           Типы размеров: TYPE_0 линейный · TYPE_2 радиус/диаметр · TYPE_3 угол (у углов tol пусто).
           Квалитеты в файле ТЕКСТОМ: 6g 8 · f7 6 · h6 3 · H8 2 · g6 2 · Z6 2 · H7 1 · H9 1; в Creo — DimTolISODIN.
           НОМИНАЛ размера в файле НЕ НАЙДЕН (double/float32/текст = 0) — формат не разгадан; канал:
           symbol + text(i_val) + parent_dim_id; читать номинал пока J-Link-ом.
           Ложный делимитер фич FB E3 F7 80 ОПРОВЕРГНУТ (97 частей ≠ 19 элементов); ключ — feat_defs_<ID>.
РАЗМЕРЫ ПОСТРОЕНИЙ — ЧИТАЮТСЯ (замер боевой базы 29.10, только чтение): arch_dims 248 572
           (JSON {"d26": 27.19}), arch_dim_ch 224 845 (история было->стало), params 1 078 484.
           Замыкание: имя dN = "d" + dimid (Creo: sym=d10 dimid=10 — совпало). Код: engine.model_params
           (arch_dims + params), plm_history, plm_graph:207. В БАЙТАХ номиналов НЕТ (§104 скилла).
КОД ВИДА — ВОПРОС ЗАКРЫТ ОТРИЦАТЕЛЬНО (29.10.2026, фаза 8; сверка с ЖИВЫМ Creo, 9 элементов):
           `b` = КЛАСС ЗАПИСИ (`2`=компонент, `3`=фичер/операция, `5`=плоскость, `21`=ось, `25`=СК/размер),
           НЕ вид фичера: один `b=3` обслуживает СВЕРЛЕНИЕ(TYPE_30) · ФРЕЗЕРОВАНИЕ(29) · ТОЧЕНИЕ(28) ·
           СТАНОК(97) · ОПЕРАЦИЯ(96). ВИД В ФАЙЛЕ НЕ ХРАНИТСЯ ЧИСЛОМ — Creo выводит `TYPENUM` сам.
           Словарь `pfcFEATTYPE` (280 типов) — из живого `pfcFeature.h` (Creo 13), НЕ равен `TYPENUM`.
           ЗАКРЫТЫ 5 кандидатов: `b`, `obj_type`, `symbol_key`, `geom_type`, `pfcFEATTYPE`.
           ПРАВИЛО: вид — ТОЛЬКО из Creo; без Creo писать «элемент с `b=<код>`» (→ `SKILL_GRABLI` §131).
СТАТУС ФИЧЕРА — В ФАЙЛЕ НЕТ, БРАТЬ ОТ CREO (29.10.2026, фаза 9, живой прогон 53 эл.):
           43 × FEAT_ACTIVE + 10 × FEAT_SUPPRESSED ⇒ **19 % подавлено**.
           В файле признака НЕТ (6 проверок): `b` одинаков, запись `names_table` идентична,
           `DispCntrl→item_data→status` = 1 запись (слои), `reg_status` = поле модели,
           `refs_n_status`/`topol_state` = единичны, слова `suppress` = 0 вхождений.
           ПОДТИП (`SUB=`: `Сверление`·`Фрезерование резьбы`·`Операция`) — **0 вхождений в файле**.
           ПОЛНЫЙ ВИД = `TYPENAME` + `SUB` + `TYPENUM` — всё ТОЛЬКО от Creo.
           ИНСТРУМЕНТ: `TreeProbe.java` печатает ИМЯ статуса (`featStatusName`), компиляция OK.
           БЕЗ CREO: помечать «статус неизвестен», НЕ считать активным (→ `SKILL_GRABLI` §132).
ПОРЯДОК/СВЯЗИ (29.10.2026, фаза 10, живой Creo): `TreeProbe` печатает `number`/`parents`/`children`.
           `#FEAT 53 · #DIM 1696 · #ERR 0`; 43 ACTIVE + 10 SUPPRESSED.
           🔴 `number=null` — 20 записей, из них **10 АКТИВНЫХ** ⇒ `null` НЕ значит «подавлен»:
           это «не в последовательности регенерации» (вспомогательные датумы `Глубина_зенковки_*`).
           `parents`/`children` — ПУСТЫ (0 вхождений): нужен файл, где фичер построен НА фичере.
           ТРИ нумерации: номер в списке · `feat_id` · `number` (порядок регенерации) — не путать.
           → `SKILL_GRABLI` §133.
XToolkitAmbiguous — ЭТО ДВА CREO (29.10.2026, фаза 11): два процесса `xtop` одновременно;
           `tree_probe.bat` поднимает Creo и оставляет жить. Лечение: закрыть лишний Creo;
           ЛУЧШЕ — `tree_probe.bat FILE1 FILE2 …` (Creo 1 раз, проверено: 2 модели, #ERR 0).
           «Поставить в начало кода» НЕ помогает — Creo занят, а не «не найден».
СВЯЗИ (parents/children) — J-LINK НЕ ДАЁТ (замер 4 файла / 143 элемента = 0), но ДАЁТ C API:
           `ProToolkit.h`/`ProFeature.h:1014` → `ProFeatureParentsGet(handle, &parents, …)`.
           + флаги `PRO_FEAT_STAT_CHILD_OF_FAILED (1<<8)` · `PRO_TK_SUPP_PARENTS`.
           СТАТУС: C-проба НЕ СОБРАНА — нет `cl.exe` (MSVC). Путь открыт.
ПЛМ (из `STRATEGY_PLM.md` §5): 5 слоёв — Мастер(`FeatDefs`) · Заготовка(`MERGE_BASE_PART`) ·
           Отливка(`PTC_SHRINKAGE_FACTOR`) · Оснастка MSTR · CAM(`FullMData`). → `SKILL_GRABLI` §134.
ГЕНЕАЛОГИЯ — ЧИТАЕТСЯ ТЕКСТОМ (29.10.2026, фаза 12, замер 40 пар / 43 файла приспособлений):
           `\xe0\n from_mdl_name \x00 \xf1 "PSB_3-Z.PRT" \x00 \xe0\n to_mdl_name \x00 "01-INSERT-PSB-03-Z.PRT" \x00`
           4 типа связей: ЗАГОТОВКА (`-Z`) · ИТЕРАЦИЯ (`_NN`) · ПЕРЕИСПОЛЬЗОВАНИЕ (`KP-08`→`KP-04`) ·
           ЗАИМСТВОВАНИЕ из чужого проекта (`ЦИ-1-ИНДИКАТОР`→`INSERT-PSB-01-02`).
           🔴 `to_mdl_name` — НЕ имя файла (`to=01-INSERT-PSB-03.PRT`, файл=`001-insert-psb-03.prt.1`)
           ⇒ связь только ИЗ СОДЕРЖИМОГО (§М.1г). `MERGE_BASE_PART` в приспособлениях = 0.
           → `SKILL_GRABLI` §135.
C-КОМПИЛЯТОР — В СИСТЕМЕ НЕТ (замер 29.10.2026): `cl/gcc/g++/clang/tcc` = нет; нет `vswhere`, нет `Windows Kits`.
           ⇒ C-проба `ProFeatureParentsGet` НЕ СОБРАНА. В VS Code расширение C/C++ компилятор НЕ даёт.
           НУЖНО: MSVC Build Tools (~2-3 ГБ, бесплатно) — официальный компилятор PTC.
🔴 РУЧНЫЕ ТЕХПАРАМЕТРЫ ОТМЕНЕНЫ (29.10.2026, фаза 14, слово владельца): `НОРМОЧАС`/`ПАРТИЯ`/
           `НОРМА_НАЛАДКИ`/`СТОИМОСТЬ_*` — ВСТАВЛЕНЫ ВЛАДЕЛЬЦЕМ вручную, УСТАРЕЛИ. Creo считает САМ.
МАШИННЫЕ ДАННЫЕ ЧПУ (правильный источник, замер 116 файлов asm/mfg): `CL_`(8127/101 файл) ·
           `traj`(327/104) · `OPERATION`(309/86) · `NC_SEQ`(258/86) · `tool_id`(203/102) · `CL_DATA`(131/99).
           ЖИВЫЕ ПОЛЯ: `tool_array → tool_id="SVERLO_D18" · tool_params[18]` (подача/обороты/диаметр) ·
           `OPERATION_NAME` · `NC_SEQUENCE_NAME` · `CL_DATA_MODE=MULTAX_DATA` · `custom_cl_text` · `ancpp_data`.
           ⚠️ Java-API `pfcMFG.MFG` = ТОЛЬКО `GetSolid()`; CL-инструкции пусты ⇒ ВРЕМЕНИ в J-Link НЕТ.
           Время — РАСЧЁТНОЕ (подача × длина траектории) либо C API. → `SKILL_GRABLI` §137.
МАНУФАКТУРИНГ — ТЕХПАРАМЕТРЫ ЧИТАЮТСЯ (29.10.2026, фаза 13, замер 324 файла):
           схема: `\xe3 "ПАРТИЯ" \x00 ' \x88 ... \xe3 4 value(i_val) \x00 <ЗНАЧЕНИЕ> \xf1 \xf7\x1d`
           ЗНАЧЕНИЯ: `ПАРТИЯ`=10 (229×) · `НОРМОЧАС`=129 (244×) · `НОРМА_НАЛАДКИ`=47/10 (142×) ·
           `МАТЕРИАЛ`=ссылка (178×). ИМЕНА без значений здесь: `ВРЕМЯ_ОБРАБОТКИ`(48) ·
           `ВРЕМЯ_НАЛАДКИ`(106) · `СТОИМОСТЬ_ПАРТИИ`(70) · `СТОИМОСТЬ_НАЛАДКИ`(106).
           🔴 ГРАБЛЯ: якорь `\xe3\x32…\xf7\x1d` даёт ВСЕГДА `25394` = ссылка, НЕ значение;
           верный якорь — `value(i_val)`+байт. И `\uXXXX` в `rb""` НЕ работает — кириллица байтами.
           ПЛМ-карточка: `НАИМЕНОВАНИЕ`(424) · `ОБОЗНАЧЕНИЕ`(236) · `КАТАЛОЖНЫЙ_НОМЕР`(262) ·
           `СТАНДАРТ`(372) · `РАЗРАБОТАЛ`/`ПРОВЕРИЛ`/`УТВЕРДИЛ` (подписи). → `SKILL_GRABLI` §136.
ГРАБЛЯ МЕТОДА (→ `SKILL_GRABLI` §130): диапазон `[\xc0-\xff]` в шаблоне для UTF-8-строки теряет ВСЮ
           кириллицу (continuation-байты `\x80-\xbf` вне диапазона). Замер: старый шаблон 0, `[^\x00]` 89/89.
🏆 КАРТА ПОЛЕЙ ЕСТЬ В САМОМ ФАЙЛЕ (29.10.2026, фаза 15, совет владельца «ищи шире, делай параллели»):
           формат поля: `<знач> E0 <ТИП> <ИМЯ> 00` (01 простой · 09 с данными · 0A строка).
           ПОЛНАЯ карта: revnum_ptr · geom_revnum · cosm_revnum · insert_layer_id · layer_count ·
           rel_part_eps · model_eps · fixed_model_eps · part_type · first_ent_id · outline ·
           attrib_array · max_part_size · gr_creo_src_ver · ref_part_tabs · ref_part_tab · objname ·
           object_type · name · simpl_rep · inherit_rep · p_foreign_source · ext · long_name · revnum
           → ФИЧЕР: dep_id · attributes · feat_id · appl_id · ref_id_user · ref_id · ref_id_coll_flags ·
           ref_id_strength · use_feats_tab · id · type · coll_flags · strength.
           ⇒ ПОЛЕ `type` и `parent` СУЩЕСТВУЮТ (искали в фазах 6–8!). Заголовок модели читается:
           `E0 0A "name" 00 "CTKD_015_23_001_MILL_TURN"` (object_type=01). → `SKILL_GRABLI` §138.
🏆 МАНУФАКТУРИНГ В ФАЙЛЕ (29.10.2026, фаза 15): точка входа `F8 <КОД> F7 16 FB E3 F7 17` (22 шт).
           Имена только в ЧПУ: `PTC_MFG_PRM_CL_FILE`(38) · `PTC_TOOLPATH_REV_NUM`(18) · `mpoint`(14) ·
           `mp_source`/`mp_struct_attr`/`mp_checksum` · `NC_ASM_*` · `PRO_MP_ALT_*` (MASS/VOLUME/AREA/COG/I).
           Параметры операции: `DESCRIPTION` · `MACHINING_TIME` · `SPINDLE_SPEED` · `CUTTER_DIAM` ·
           `CUT_FEED` · `STEP_DEPTH` · `CLEAR_DIST` · `TOOL_WIDTH` · `NOSE_RADIUS` · `NUMBER_OF_TEETH` ·
           `POINT_ANGLE` · `SHANK_DIAMETER` · `HOLDER_NAME` · `HEAD_NO` (= КОЛОНКИ таблицы процесса).
           🔴 ГРАБЛЯ №4 (±1, с §118/§126/§128): 8 байт после `E3 32` — НЕ double (начинаются с `F7 40`,
           код упакованного числа); double там = 6.02e-08 ❌. ТЕКСТОВЫЕ значения лежат рядом и читаются:
           `"1000"` · `"30.3"` · `"0.8"` · `"0.045"` · `"0.45"` · `"0.34"` · `"((200"` · `"FLOOR"`. → §139.
C API (справка, компилятора НЕТ): `ProMfgProctableVisit` · `ProMfgprocitemPropertyGet(item,
           PRO_MFGPROP_ACTUAL_MACHINING_TIME, ...)` · `ProMfgprocitemElemtreeGet` (ИНСТРУМЕНТ) ·
           `ProMfgprocitemSubtype {STEP, OPERATION, WORKCELL}` · `promfgproctable_h.html` (56 КБ) в
           `D:\PTC\CREO13\...\protoolkit\online_help\creo_toolkit\api\dita\`.

```

## Как проверять (команды дома)

```powershell
# СЕТ НА ПРОВЕРКУ (9 реальных файлов, только чтение; на Z: ничего не пишет)
cd D:\AI\tools\agent\plm_reader
python _test_set.py          # ожидается: «СЕТ: ЗЕЛЁНЫЙ», проверок 32, провалов 0
python _test_set.py --neg    # ожидается: «СЕТ: КРАСНЫЙ», код выхода 1 (доказательство проверки)
# поставка цела? (Get-FileHash ЗАПРЕЩЁН — GRABLI §100, только нормализующий хашер)
cd D:\AI\tools\agent\plm_reader; python make_version_json.py "проверка"   # пересобирает, затем сверить files==sha256
python _smoke_v87.py                                                       # ожидается SMOKE OK
python -m py_compile engine.py creo_read.py plm_queries.py plm_links.py plm_build_links.py
# что не закоммичено?
cd D:\AI\tools; git status --short; git diff HEAD --stat -- agent/plm_reader
```

## Что НЕ трогать без слова владельца

- шара `Z:\PTC\CREO-START\plm_reader` — **агент не касается** (GRABLI §82, SKILL_plm_reader_sync);
- боевая база (она на шаре) — пробы только на **копии**;
- одна база / связи по структуре файла, не по имени (GRABLI §85, §95).
