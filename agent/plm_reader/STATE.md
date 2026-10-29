# STATE — ЖИВОЕ СОСТОЯНИЕ PLM READER (обновлять при КАЖДОМ шаге)

> Правило: «Сессия смертна. Всё, что не в файле — потеряно». Три строки, дата замера,
> источник каждого утверждения. Версия формата — 28.10.2026 (предложение эстафеты, §3 «чего не хватает»).

**Обновлено:** 29.10.2026, фаза 21 · нога Cline (ЗАКОН МЕТОДА: читать ВСЁ через `#UGC_TOC`)

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
🏆 ПОЛЕ `type` РАЗОБРАНО (29.10.2026, фаза 16): карта блока фичера = 14 полей (адреса `0x003D63..0x003E30`):
           `revnum · dep_id · attributes · feat_id · appl_id · ref_id_user · ref_id ·
           ref_id_coll_flags · ref_id_strength · use_feats_tab · id · **type** · coll_flags · strength`.
           ТИП поля: `01`=скаляр · `09`=со структурой (перед ним `F8 <N> C8 00 <M> 00`) · `00`=ссылка.
           ⇒ **`type` — ЭТО КОД ВИДА** (искали фазы 6–8); поле `parent` — в блоке `0x0041FE`.
           ⚠️ НЕ СВЕРЕНО с `TYPENUM` Creo — следующий шаг. → `SKILL_GRABLI` §140.
🏆 `MACHINING_TIME` ЧИТАЕТСЯ — 10 из 10 (29.10.2026, фаза 16): `val = struct.unpack('>f', bytes[1:5])[0]`
           от 8 байт сразу после `E3 32`. Даёт минуты 2.63…3.50 (порядок совпал с графиком).
           🔴 ГРАБЛЯ №5: 8 байт начинаются с `F7 40` ⇒ все парсят как double → `6.02e-08` (мусор).
           `F7 40` — ЗАГОЛОВОК, значение — float32 BE из байт 1..5.
           ДОГАДКА владельца «время не срегенерировано» — ОПРОВЕРГНУТА (9 разных значений из 10).
           ⚠️ НЕ ЗАКРЫТО: `SPINDLE_SPEED`/`CUT_FEED`/`CUTTER_DIAM`/`NOSE_RADIUS`/`STEP_DEPTH`/`CLEAR_DIST` —
           у них значение 3 БАЙТА (без `F7 40`), формула не разгадана; подбор ЗАПРЕЩЁН (3 промаха, §5.1).
           Ход: решать ОБРАТНУЮ задачу от известного числа (`23-16508.asm`: FR50 → 30.7 мм / 4.2 мин).
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
🔴🔴 ЗАКОН МЕТОДА (29.10.2026, фаза 21, ПОРУЧЕНИЕ ВЛАДЕЛЬЦА): «**с верхней главной карты нужно и ВСЁ
           ДРУГОЕ прочитать/разобрать, строение скорее всего примерно одинаковое**».
           ⇒ ЧИТАТЬ ЛЮБОЙ ФАЙЛ CREO ТОЛЬКО ЧЕРЕЗ `#UGC_TOC`: (1) заголовок `#UGC:2 <ТИП> <ВЕРСИЯ>`;
           (2) записи `<ИМЯ> <off> <len> <len-10> <ВЕРСИЯ ИЗ ЗАГОЛОВКА> <flag> <-1> <a4> <b4>`;
           (3) цепочка `NEXT_TOC_ENTRY <off> <len>`; (4) полная карта; (5) читать секцию ПО АДРЕСУ.
           🚦 ГРАБЛЯ: НЕ хардкодить число версии — PRT `1873` · MFG `2350` · вложенные `2149`.
           Зашил 2350 → на `.prt` получил 0 записей. → `SKILL_GRABLI` §147.
           РАЗОБРАТЬ ТАК ЖЕ: `AllFeatur` · `FeatDefs` · `MdlStatus` · `NeuAsmSld` · `LargeText` ·
           `MdlRefInfo` · `FeatRefData` · `BasicData/Text` · `Geomlists/Depen` · `DispCntrl` ·
           `ModelView#N` · `FamilyInf` · `SldRegenRevInfo` · `*AltIdMgr0`.
🏆🏆 КОРНЕВАЯ КАРТА ФАЙЛА — `#UGC_TOC` (29.10.2026, фаза 20, совет владельца): ЗАГОЛОВОК
           `#UGC:2 ASSEMBLY/ASSEM_MFG …`; ЗАПИСЬ = `<ИМЯ> <offset_hex> <len_hex> <len-10> 2350 <flag> <-1> <a4> <b4>`;
           цепочка через `NEXT_TOC_ENTRY <offset> <len>`; терминатора нет. 52 записи. Ключевые:
           `AllFeatur 0x120B6/0x10483` · **`FullMData 0x267DC/0x6852` (★ ВЕСЬ МАНУФАКТУРИНГ)** ·
           **`LargeText 0x68BE/0x7977` (★ параметры CL: ВРЕМЯ/режимы)** · `FeatDefs 0x3F80E/0x22AC8` ·
           `MdlStatus 0x377F0/0x7F7E` · `NeuAsmSld 0x2D05B/0xA793` · `VisibGeom 0xE85D/0x1A90` ·
           `SolidPrimdata 0x27A1/0x1006` (тесселяция, НЕ точная геометрия).
           ПРОВЕРКА: `0x68BE+0x7977=0xE235` ⇒ `MACHINING_TIME@0x8905` ВНУТРИ `LargeText` ✅;
           `0x267DC+0x6852=0x2D02E` ⇒ `tool_array@0x26E81` ВНУТРИ `FullMData` ✅.
           ⇒ АДРЕС ИСКАТЬ ЧЕРЕЗ TOC, а не перебором файла. → `SKILL_GRABLI` §145.
🏆 ИЕРАРХИЯ МАНУФАКТУРИНГА (фаза 19-20, подтверждена замером 605 имён FullMData в ПОРЯДКЕ):
           `mfg_ptr → tool_array(ПАРК: tool_id=\"SVERLO_D18\"/tool_params) → tool_ref_id→adapter_ref_id
           (SVERLO_D14_5 · ZENKOVKA · METCHIK_M16/M8 · REZBOFREZA · CNMG · T0001/0003) →
           SET_NAME(УСТАНОВКА) → OPERATION_NAME/NC_SEQUENCE_NAME(ПЕРЕХОД) →
           SPINDLE_SPEED/CUT_FEEDRATE/PLUNGE_FEEDRATE(РЕЖИМЫ) → MACHINING_TIME(ВРЕМЯ) →
           TOOL_NAME/TOOL_TYPE/TOOL_POSITION_NUMBER → CUTTER_DIAM/DRILL_DIAMETER/NOSE_RADIUS`.
           Смещения блоков: ПАРК `0x26E81..0x2903C` · ПЕРЕХОДЫ(19) `0x2D890..0x2E002`
           (`TOOL_ID`19 · `PRE_/POST_MACHINING_FILE`19 · `MACH_COLLISION_STATUS`18 · `MACHINE_CSYS`18 ·
           `PTC_TOOLPATH_REV_NUM`18 · `CONSIDER_TOOL_LENGTH`10) · ЭКЗЕМПЛЯР `0x34793..0x370BD`
           (`TOOL_CENTER`/`HOLDER_DIAMETER`/`HOLDER_LENGTH`) · CL-ПАРАМЕТРЫ(11) `0x8905..0xB136`.
           🚦 РЕГИСТР ЗНАЧИМ: `TOOL_ID`(19, список) ≠ `tool_id`(2, структура). → §144-§146.
📋 ПОЛНЫЙ ПЕРЕЧЕНЬ ТИПОВ ФАЙЛОВ CREO (29.10.2026, фаза 22, ЗАМЕР 97 226 файлов + библиотека 16 960):
           ПОДТВЕРЖДЕНО: `.prt`21270 · `.xpr`14815(копия детали) · `.drw`12413 · `.asm`11227 ·
           `.lay`2144 · `.m_p`841 · `.mfg`422 · `.sec`73 · `.frm`36 · `.crc`32 · `.neu`5 ·
           `.rep`2 · `.cem`1.
           🔴 НАЙДЕНО ЗАНОВО (нет ни в §102, ни в списке владельца):
           **`.xas`1206 = КОПИЯ СБОРКИ (★ «сборка взаимозамены», пара к `.xpr`!)** ·
           **`.mtl`2607 (материалы, новый формат)** · **`.tph`1779 (ТЕХПРОЦЕСС)** ·
           **`.dsn`1306 (design/компоновка)** · **`.stk`931 (stock/заготовка)** · `.tst`831 ·
           `.idx`722 · `.mnu`580 · **`.tls`561 (TOOLS)** · **`.tp`503 (TOOL/ТП)** · `.sym`391 ·
           `.gph`356 · **`.tpm`284 (параметры инструмента)** · `.m3d`220 · `.mat`208 · `.tbl`144 ·
           `.lsl`148 · `.mrd`59 · `.acc`17 · `.pro`23 · `.dtl`2.
           БИБЛИОТЕКА `CREO-START\Libraries` (16 960): `.lay`2144 · `.prt`1259 · `.txt`67 ·
           `.asm`63 · `.gph`32 · `.mnu`24 · `.sec`22 · `.drw`15 · `.lsl`14 · `.tbl`9 · `.inf`7 ·
           **`.ctg`2 (★ CATALOG)** · **`.bnd`1 (★ BUNDLE)**.
           ❌ НЕТ НИГДЕ: `.blk`0 · `.skl`0 · `.dgm`0 · `.mrk`0 · `.module`0 · `.confasm`0.
           ⇒ РОЛЬ (заготовка/приспособление/родитель/мастер-модель) — ТОЛЬКО ИЗ СОДЕРЖИМОГО файла,
           НЕ из расширения (§М.1г). ⇒ В `engine.CREO_EXTS` добавить: `.xas`(copy!) · `.mtl`/`.mat` ·
           `.tph` · `.dsn` · `.stk` · `.tls`/`.tp`/`.tpm` · `.idx` · `.mnu` · `.sym` · `.gph` ·
           `.tbl` · `.m3d` · `.ctg` · `.bnd` · `.lsl` · `.inf`. → `SKILL_GRABLI` §148.
🏆🏆 ТИП ФАЙЛА — В ЗАГОЛОВКЕ `#UGC:2 <ТИП>`, НЕ В РАСШИРЕНИИ (29.10.2026, фаза 23, §149):
           ЗАМЕР 441 файла `D:\РАБОЧАЯ ПАПКА\sergei\UCHASTOK-S-DOMOM`:
             `PART` 217 · `ASSEMBLY` 42 · `DRAWING` 34 · **`INST_PART` 10 (это `.xpr`!)** ·
             **`PART/SKEL_MODEL` 6 (★ СКЕЛЕТОН)** · **`ASSEMBLY/ASSEM_MFG` 4** ·
             **`MFG_TOOL_PATH` 4 (★ `.tph` = ТРАЕКТОРИЯ)** · **`PART/BULK` 1 (★ «BLK»!)**
           НАЙДЕНО ТО, ЧТО ИСКАЛ ВЛАДЕЛЕЦ:
             «BLK» = `#UGC:2 PART/BULK` → `besedka-kirpich.prt.1` (52 880 Б)
             СКЕЛЕТОН = `#UGC:2 PART/SKEL_MODEL` + суффикс `_skel` → `besedka-000-sb_skel0001.prt.1`
             ТРАЕКТОРИЯ = `#UGC:2 MFG_TOOL_PATH` → `КЛЕММА-14.tph.1` (573 163 Б)
           🎁 `.tp` = `Pro/CLfile Version 10.0` — ТЕКСТОВЫЙ CL-ФАЙЛ (БЕЗ байтового разбора!):
             `OP010.tp` 476 КБ / 8 962 строки: `MFGNO` · `PARTNO` · `FEATNO` · `MACHIN` ·
             `PPRINT / OPERATION NAME : OP010` · `NC SEQUENCE NAME : CHERN` · `DATE TIME : 13-JUN-24` ·
             `TOOL_TYPE : END MILL` · `CUTTER DIAMETER, 20.000` · `SPINDL / RPM, 2864, CLW` ·
             `FEDRAT / 6014, MMPM` · `LOADTL` · `CUTTER` · `GOTO`/`CIRCLE`/`RAPID`.
             ⇒ ВСЯ ТЕХНОЛОГИЯ ТЕКСТОМ — ответ на «время/установы/инструмент» БЕЗ J-Link!
           🔴 ИСПРАВЛЕНО: `.stk`/`.dsn` = `VERICUT-model Version-3.0` — НЕ Creo!
           🔴 ИСПРАВЛЕНО: `.xpr` = `INST_PART` (самостоятельный тип), не «копия family-table» (§102.2).
           🔊 ГРАБЛЯ (3× за смену): `editor` с `old_text` = заголовок соседней секции ТЕРЯЕТ её.
           ЛЕЧЕНИЕ: вставлять новой секцией через `insert_line`, НЕ заменой; после — проверять нумерацию.
🏆🏆🏆 СВЯЗИ РАСКРЫТЫ (29.10.2026, фаза 24, §150): задача владельца «Деталь/сборка/мануфактуринг + СВЯЗИ».
           🔴 ГРАБЛЯ №6 — В ФАЙЛЕ **ДВЕ КАРТЫ `#UGC_TOC`**: #1 @0x31F (18 зап.) и #2 @0x61556 (18 зап., В КОНЦЕ).
           СКЛЕЙКА карт → адреса ушли ЗА границу файла (0x6D604 > 0x62075) → читалось ПУСТО.
           ПРАВИЛО: парсить карты РАЗДЕЛЬНО; адрес обязан быть `< размера файла`.
           ★★★ ТАБЛИЦЫ СВЯЗЕЙ (адреса точные):
             `FeatDefsCmp` @0x55BC8 (3305 Б, 79 полей) — КОМПОНЕНТЫ: symbol_key · model_type ·
               local_sys · **own_ref_id** · orient · offset · **geometry1_id/geometry2_id** ·
               memb_num1/2 · **sel_assem_pnt/sel_comp_pnt/_uvparam** · **trf_arr**.
             `FeatDefsDtm` @0x54FBF (3079 Б) — ДАТУМЫ: то же + transf · plcm_revnum · comment.
             `IdsGenAllRepsDb` @0x53DB8 (4613 Б) — МОСТ: **geom_id · geom_type · feat_id** ·
               boundary_type · outline · topol_ref_data · owner_feat_revnum +
               `all_reps_items: owner_item · owner_id · db_type · revnum_item` ← КОРЕНЬ СВЯЗЕЙ ПЛМ.
             `ModelView#N` @0x58071 (1181 Б) — РАСПОЛОЖЕНИЕ: matrix · world_matrix_ptr · geom_id ·
               **model_name · unrep_model_name · position · model_cosm_rev_num(РЕВИЗИЯ)**.
           📊 MFG vs PART (TOC): `AllFeatur` 99 Б (PART!) vs 13 006 Б (MFG) · `FullMData` 6703/8350 ·
             `FeatDefs*` только у MFG · `SldRegenRevInfo` (ИСТОРИЯ) только у MFG · `ModelView` 2/8 ·
             `MechanicaData` 315 477 (только MFG). → §150.
           ❓ У ДЕТАЛИ `AllFeatur` ПУСТО (99 Б) — дерево элементов детали лежит в другом месте
             (`BasicData`/`MdlStatus`/`LargeText`) — ПРОВЕРИТЬ следующей ноге. → §151.
🏆🏆🏆 СВЯЗИ И СТАТУС — В `AllFeatur`! (29.10.2026, фаза 25, §152) — C API НЕ НУЖЕН.
           🔴 ГРАБЛЯ №6 РАСШИРЕНА: карт `#UGC_TOC` ОТ 2 ДО 3 у КАЖДОГО файла (замер 8 файлов):
             PART/BULK 3 (`0x314`/`0xC6A8`/`0xCD91`) · PART/SKEL 3 · PART ЦТКД 3 ·
             ASSEM_MFG 2 · ASSEMBLY 2 · INST_PART 2 · PART PSB 2.
             ПРАВИЛА: (1) карт 2–3, парсить РАЗДЕЛЬНО; (2) адрес `< размера файла`;
             (3) ДЕДУП по (имя, offset) — `SldRegenRevInfo` иначе считается ДВАЖДЫ.
           ★★★ `AllFeatur` = КАРТА ЭЛЕМЕНТА + СВЯЗИ. Формат `AllFeatur` детали @0x27D15
             (35 107 Б, 107 полей; SKEL 20 994/75; MFG 13 006):
               `table_id · type · feattype_key · form · attributes · placement · intersection`
               `blend_choice · depth_choice · angle_choice · pat_choice · round_choice`
               MFG-блок СВЯЗЕЙ: `dtm_id_tab → dtm_id · dim_id` + `info(geom_item_rev_info) →
               **parents_checksum · num_parents · is_item_alive** + `mdl_geom_rev` + `extnd_revnum_data`
               + **`ref_models_data` (ГРАФ СВЯЗЕЙ!)** + `info_arr → id_tab · has_complex_ref · checksum`.
             ⇒ ЭТО ЗАКРЫВАЕТ ТО, ЧТО J-Link НЕ ДАВАЛ: `num_parents` (= ProFeatureParentsGet=0!),
               `is_item_alive` (= FEAT_SUPPRESSED), `extnd_revnum_data` (ревизии), `ref_models_data`.
             ⇒ **C API / MSVC НЕ НУЖЕН — связи и статус лежат В ФАЙЛЕ.**
           📊 СВЯЗИ У ВСЕХ ТИПОВ: `FeatDefsDtm` есть у детали (2257/26) и скелетона (4971/31);
             `FeatDefsCmp` — ТОЛЬКО у сборок (3305/79); `MdlRefInfo` — только у сборок.
🏆🏆🏆 `feat_defs_<N>` = ТИПЫ ЭЛЕМЕНТОВ, `feattype_key` = ОПИСАНИЕ (29.10.2026, фаза 25, §153):
           ФОРМАТ ЗАПИСИ ПОЛЯ: `<ЗНАЧЕНИЕ> E0 <тип-маркер> <ИМЯ> 00`, напр.
             `f6 e0 01 "type" 00` · `83 9b e0 0a "feattype_key" 00` · `00 e0 01 "blend_choice" 00`.
             `E0` = «далее имя»; маркер: 01=простое, 0a=сложное/ключ; `f6`/`e1` = ссылки, `00` = число.
           СТРУКТУРА: `feattype_key` = 1 раз (ОПИСАНИЕ) · `feat_defs_<N>` = 6 раз:
             **911 · 916 · 917 · 923 · 926 · 979 = 6 ТИПОВ ЭЛЕМЕНТОВ этой детали!**
           ⇒ `b` из `names_table` = ИНДЕКС/ССЫЛКА в список типов (НЕ «съеденный байт», не код вида).
           ⇒ Вид = СВЯЗКА `feat_defs_<N>` ↔ `names_table` ↔ `AllFeatur` (ТРИ секции, не одно поле) —
             ровно то, о чём говорил владелец («извлекать контекст»).
           ⚠️ Связь `feat_defs_<N>` ↔ `TYPENUM` Creo НЕ проверена (нужен прогон Creo).
🏆🏆🏆 КОДЫ ТИПОВ ЭЛЕМЕНТОВ (29.10.2026, фаза 26, §154): `feat_defs_<N>` — УСТОЙЧИВЫЕ коды!
           PART ЦТКД: 911·916·917·923·926·979 · ЛИТЕЙКА 052401: 913·916·917·923·927·1031·1238·1306 ·
           MFG КЛЕММА-14: 923·939·940·949·979·1000·1007·1008·1232·1234 ·
           SKEL беседка: 923·926·949·950·979·1234.
           ПОВТОРЯЮТСЯ: **923 у ВСЕХ 4** (базовый) · 979 у 4 · 916/917 у 2 · 926/949/1234 у 2.
           **`1000` = КОМПОНЕНТ** (`FeatDefsCmp → feat_defs_1000`). ⇒ ЭТО И ЕСТЬ «КОД ВИДА»!
🏆🏆🏆 ФОРМАТ ЧИСЕЛ РАЗГАДАН (29.10.2026, фаза 26, §155) — `F8 <len> <байты>` / `F4` / `F1`:
           `f8 14 <14Б>` = МАССИВ/ХЕШ · `f8 01 1e` = 30 · прямой байт = число (`0b`=11) ·
           `f4 05`=5 · `f1 1b`=27 · 2 байта (`8c 06`=1676) · **`e1`/`e2`/`e3`/`f6` = МАРКЕРЫ ССЫЛОК**.
           ⇒ `num_parents` литейки = **0x0B = 11** (РОДИТЕЛИ ЕСТЬ!) · `is_item_alive`=01 · `type`=03 ·
             `rev_cnt`=0x38=56 · `version`=5 · `revnum`=0x1B=27 (снова 27!).
           🔴 ГРАБЛЯ №7: ЗНАЧЕНИЕ ЧИТАТЬ **ПЕРЕД** `E0` (а я читал после) + `e1`/`e2` = ссылки, не значения.
           📍 РОДИТЕЛИ (`num_parents`/`parents_checksum`) — в **`VisibGeom`** (`info(geom_item_rev_info)`),
             а НЕ в `AllFeatur`! Литейка `052401-model-master.prt` @0xAD19C/@0xAD1C9.
           📍 ИМЯ СОБСТВЕННОЙ МОДЕЛИ: `<0><КОД><имя>` — `013ctkd_015_23_001.prt` · `01bbesedka-...` ·
             `017052401-model-master.prt` · `014170meta-1-master.prt` · `013клемма-14.asm` (коды 13/14/17/1b).
           📊 `AllFeatur` у ЛИТЕЙКИ огромен: 550 379 (052401) · 1 348 653 (170meta-1) · 302 174 (052402).
🏆🏆🏆 СЛОВАРЬ ТИПОВ СОШЁЛСЯ: `feat_defs_<N>` = `pfcFEATTYPE` **+ 910** (29.10.2026, фаза 27, §156):
           Владелец напомнил: словарь уже был записан (`SKILL_GRABLI` 2223-2227, `SKILL_creo_read_feat` 47/106).
           Источник (живой): `D:\PTC\CREO13\...\otk_cpp\include\pfcFeature.h` (20 038 Б, enum 314 имён, FEATTYPE=280).
           ★★★ ФОРМУЛА: **тип = feat_defs_<N> − 910** (проверено на 30 кодах, 16 совпали СО СМЫСЛОМ):
             911→HOLE · 913→ROUND · 916→CUT · 917→PROTRUSION · 923→DATUM_PLANE (у ВСЕХ 4 файлов!)
             926→DATUM_AXIS · **927→DRAFT (у литейки 21 уклон — ИДЕАЛЬНО)** · 939→MILL · 940→DRILL
             949→CURVE · 979→CHANNEL · 1000→MFGMERGE · **1007→WORKCELL (совпало с MILLTURN01!)** · 1008→CUT_MOTION.
           ⚠️ ГРАНИЦА: 1232/1234/1238/1306 — ВНЕ таблицы (индексы 322+) ⇒ ДРУГОЙ источник.
           ⚠️ НЕ СРАВНЕНО с `TYPENUM` Creo (TYPE_13/TYPE_30) — отдельная шкала (§131).
           📌 ТРИ ШКАЛЫ: `pfcFEATTYPE` 0…279 (API) · `feat_defs_<N>` 911…1031 (ФАЙЛ, −910) · `TYPENUM` 10…100 (Creo).
🏆🏆🏆 РАЗГРАНИЧЕНИЕ ТИПОВ (29.10.2026, фаза 28, §157):
           ★ П.2 ЗАКРЫТ: `feat_defs_1232` — это **`id` ЗАПИСИ**, а НЕ код типа!
             замер: `xsec_geom 00 e2 f2 23 0a #FeatDefs 0a e0 00 Sld_FeatDefs 00 e3 e0 00
             f8 01 f7 02 fb e3 e0 01 "id" 00 82 0a` → id=0x0A82=2690.
             ⇒ ТИПЫ = только `911…1031`; `1232…1306` = внутренние номера/имена записей.
           ★ ГРАБЛЯ №9: ПЕРЕБОР БАЗ (900…1232) даёт ЛЮБОЕ имя → метод ложных ответов.
             Истина = СОВПАДЕНИЕ СО СМЫСЛОМ (923→DATUM_PLANE у всех 4 · 927→DRAFT у литейки/21 уклон ·
             1007→WORKCELL=MILLTURN01 от Creo).
           ★ П.1: формат записи FeatDefs: `<имя> feat_defs_<N> 00 · f8 <len> · fb e3 e0 01 "id" 00 ·
             <зн> e0 01 "symbol_key" 00 <знач>` — 917→symbol_key=0x63 · 923→symbol_key=0x01.
             ⚠️ `symbol_key` ≠ индекс в `names_table` (проверено, ОТВЕРГНУТО) → имя элемента ОТКРЫТО.
           ★ П.3: три шкалы разграничены; прямая сверка с Creo `TYPENUM` = нужен прогон.
           ★ `names_table` @0xB95E (деталь, 77 строк): RIGHT·TOP·FRONT·PRT_CSYS_DEF·DEFAULT + параметры.
           ★ ГРАБЛЯ №8: `#FeatDefs` (раздел) ≠ `feat_defs_<N>` (запись). Не смешивать регистры.

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
