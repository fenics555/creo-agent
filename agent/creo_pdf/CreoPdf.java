import com.ptc.cipjava.*;
import com.ptc.pfc.pfcSession.*;
import com.ptc.pfc.pfcModel.*;
import com.ptc.pfc.pfcExport.*;
import com.ptc.pfc.pfcAsyncConnection.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.*;

/**
 * CREO PDF SCANNER (JLINK, без CREOSON).
* V2: папка вывода PDF (--out <папка>) и копия рядом с чертежом (--dup).
 *   Без --out PDF пишется рядом с чертежом (прежнее поведение); с --out — в отдельную папку,
 *   структура подпапок зеркалится. Скан при заданной папке вывода ищет устаревший PDF ТАМ.
 * Рутина дома: рядом с чертежом <имя>.drw[.N] должен лежать <имя>.pdf и быть не старше чертежа.
 *
 * Режимы:
 *   scan         <папка>            - только отчёт (Creo НЕ нужен): где PDF нет / старше чертежа
 *   export       <папка> [лимит]    - scan + создать недостающие/устаревшие PDF
 *   pdf          <папка> <имя> [out]- экспорт PDF одного чертежа (имя без расширения)
 *   config-read  [config.pro]       - ключевые опции живой сессии (или из файла)
 *   config-load  <config.pro>       - применить боевые опции (форматки, MY_ESKD.dtl, table.pnt)
 */
public class CreoPdf {
  static final String[] KEYS = {
    "pro_format_dir", "format_setup_file", "drawing_setup_file", "pro_dtl_setup_dir",
    "pen_table_file", "pro_plot_config_dir", "pro_table_dir", "start_model_dir",
    "pro_symbol_dir", "pro_group_dir", "pro_material_dir", "tolerance_table_dir",
    "pro_sheet_met_dir", "mfg_template_dir", "template_solidpart", "template_designasm",
    "template_drawing", "search_path_file", "pdf_use_pentable", "use_8_plotter_pens"
  };

  static boolean OPEN_PDF = false;      // открывать PDF после создания (иначе ничего не открывается)

  public static void main(String[] a) {
    try {
      for (int i = 0; i < a.length; i++) a[i] = a[i].replace("\"", "").trim();   // терпим кавычки в путях
      String mode = a.length > 0 ? a[0].toLowerCase() : "help";
      if (mode.equals("scan")) { scanOutFlags(a, 1); return; }
      if (mode.equals("config-scan")) { configScan(); return; }
      if (mode.equals("creo-find")) { creoFind(); return; }
      if (mode.equals("creo-start")) {
        // Аргументы: [config.pro] [--dry]. Флаг не должен приниматься за путь к конфигу.
        String cfgArg = "";
        boolean dry = false;
        for (int i = 1; i < a.length; i++) {
          if (a[i].equalsIgnoreCase("--dry")) dry = true;
          else if (cfgArg.isEmpty()) cfgArg = a[i];
        }
        creoStart(cfgArg, dry);
        return;
      }
      if (mode.equals("help")) { usage(); return; }

      System.loadLibrary("pfcasyncmt");
      AsyncConnection c = pfcAsyncConnection.AsyncConnection_Connect(null, null, null, 60);
      Session s = c.GetSession();
      String cwd0 = s.GetCurrentDirectory();
      System.out.println("cwd=" + cwd0);

      if (mode.equals("config-find")) {
        // Где Creo мог взять config.pro: рабочая папка сессии (там и стартовал), профиль, loadpoint Creo.
        java.util.List<String> cand = new java.util.ArrayList<>();
        String cwd = s.GetCurrentDirectory().replace('/', File.separatorChar);
        cand.add(cwd + "config.pro");
        cand.add(System.getProperty("user.home") + File.separator + "config.pro");
        for (String lp : loadPoints()) cand.add(lp + File.separator + "text" + File.separator + "config.pro");
        System.out.println("cwd сессии: " + cwd);
        for (String p : cand) {
          File f = new File(p);
          System.out.println("  " + (f.exists() ? ("ЕСТЬ  " + f.length() + " б   ") : "нет           ") + p);
        }
      } else if (mode.equals("config-read")) {
        Map<String, String> f = a.length > 1 ? parseConfig(a[1]) : null;
        for (String k : KEYS)
          System.out.println("  " + k + " = " + ((f != null) ? f.get(k) : readOpt(s, k)));
      } else if (mode.equals("config-load")) {
        if (a.length < 2) { System.out.println("ERR: нужен путь к config.pro"); return; }
        Map<String, String> f = parseConfig(a[1]);
        int n = 0, skip = 0;
        for (String k : KEYS) {
          String v = f.get(k);
          if (v == null || v.isEmpty()) continue;
          if (v.indexOf('$') >= 0) { skip++; continue; }
          try { s.SetConfigOption(k, v); System.out.println("  set " + k + " = " + v); n++; }
          catch (Throwable t) { System.out.println("  FAIL " + k + " : " + t); }
        }
        System.out.println("применено опций: " + n + " (пропущено из-за $: " + skip + ")");
      } else if (mode.equals("pdf")) {
        doPdf(s, a.length > 1 ? a[1] : ".", a.length > 2 ? a[2] : "",
              a.length > 3 ? a[3] : (a.length > 1 ? a[1] : "."), null);
      } else if (mode.equals("export")) {
        String dir = a.length > 1 ? a[1] : ".";
        int limit = a.length > 2 ? Integer.parseInt(a[2]) : 100;
        if (limit <= 0) limit = Integer.MAX_VALUE;      // 0 = без ограничения
        String outRoot = null; boolean dup = false;
        for (int i = 3; i < a.length; i++) {
          if (a[i].equalsIgnoreCase("open")) OPEN_PDF = true;
          else if (a[i].equalsIgnoreCase("--dup")) dup = true;
          else if (a[i].equalsIgnoreCase("--out")) {
            String v = (i + 1 < a.length) ? a[++i] : "";
            if (v.isEmpty()) { System.out.println("ERR: --out без значения (папка назначения пустая)"); return; }
            outRoot = v;
          }
        }
        if (dup && outRoot == null) outRoot = dir;     // только рядом — вывод по умолчанию
        if (outRoot != null) {
          File of = new File(outRoot);
          if (!of.isDirectory()) {
            if (!of.mkdirs()) {
              System.out.println("ERR: папка назначения не создаётся: " + outRoot);
              return;
            }
            System.out.println("папка назначения создана: " + outRoot);
          }
        }
        loadNames();
        System.out.println("режим: " + (OPEN_PDF ? "PDF открывать и оставлять" : "PDF не открывать") +
                           " | после экспорта чертёж убирается из сессии Creo");
        System.out.println("ВЫВОД: " + (outRoot == null ? "РЯДОМ с чертежом" : ("в папку " + outRoot +
                           (dup ? " + копия рядом с чертежом" : ""))));
        List<String> need = scan(dir, false, limit, outRoot, dup);
        System.out.println("к обработке: " + need.size());
        int ok = 0, bad = 0, orphans = 0;
        boolean lost = false;
        for (String base : need) {
          File f = new File(base);
          if (isOrphan(f.getParentFile(), f.getName())) {
            orphans++;
            System.out.println("  СИРОТА (нет модели): " + f.getPath());
            System.out.flush();
            continue;
          }
          // отдельная папка: структуру подпапок зеркалим, иначе одноимённые чертежи схлопываются
// БЕЗ --out вывод идёт РЯДОМ с чертежом: outDir = папка чертежа.
          // null здесь даёт XToolkitCantWrite (путь «null\имя.pdf» вместо папки) —
          // регресс V2, найден живым прогоном 02.10.2026.
          String outDir = (outRoot == null) ? f.getParent() : outRoot, dupDir = null;
          if (outRoot != null) {
            String rel = f.getParent().substring(Math.min(dir.length(), f.getParent().length()));
            File sub = new File(outRoot, rel);
            outDir = (sub.isDirectory() || sub.mkdirs()) ? sub.getPath() : outRoot;
            if (dup) dupDir = f.getParent();          // копия рядом с чертежом
          }
          try { doPdf(s, f.getParent(), f.getName(), outDir, dupDir); ok++; }
          catch (Throwable t) {
            String msg = String.valueOf(t);
            if (msg.contains("XToolkitCommError")) {
              System.out.println("  СВЯЗЬ С CREO ПОТЕРЯНА на «" + f.getName() + "»: " + msg);
              System.out.println("  Прогон остановлен: перезапусти Creo и повтори — свежие PDF пропустятся сами.");
              lost = true;
              break;
            }
            System.out.println("  ОШИБКА " + f.getName() + ": " + t);
            bad++;
          }
        }
        System.out.println("ИТОГО: сделано " + ok + ", сирот (нет модели) " + orphans +
                           (lost ? ", ПРЕРВАНО (связь с Creo потеряна)" : ", прочих ошибок " + bad));
      } else usage();
      try { s.ChangeDirectory(cwd0); System.out.println("cwd восстановлена: " + cwd0); } catch (Throwable t) {}
      c.Disconnect(10);
      System.out.println("готово");
    } catch (Throwable t) { System.out.println("ERR: " + t); }
  }

  /** Разбор флагов папки вывода для режима scan: --out <папка>, --dup, --limit N.
    *  Без --out скан идёт по старому правилу: PDF рядом с чертежом. */
  static void scanOutFlags(String[] a, int from) {
    String root = null;                                  // первый не-флаг = папка скана
    String outRoot = null; boolean dup = false; int limit = Integer.MAX_VALUE;
    for (int i = from; i < a.length; i++) {
      if (a[i].equalsIgnoreCase("--dup")) dup = true;
      else if (a[i].equalsIgnoreCase("--limit") && i + 1 < a.length) {
        try { limit = Integer.parseInt(a[++i]); } catch (NumberFormatException e) { limit = Integer.MAX_VALUE; }
      } else if (a[i].equalsIgnoreCase("--out")) {
        String v = (i + 1 < a.length) ? a[++i] : "";
        if (v.isEmpty() || v.startsWith("--")) { System.out.println("ERR: --out без значения (папка назначения пустая)"); return; }
        outRoot = v;
      } else if (root == null && !a[i].startsWith("--")) root = a[i];
    }
    if (root == null) root = ".";
    if (outRoot != null) {
      File of = new File(outRoot);
      if (!of.isDirectory() && !of.mkdirs()) {
        System.out.println("ERR: папка назначения не создаётся: " + outRoot);
        return;
      }
    }
    System.out.println("СКАН: PDF ищем " + ((outRoot == null) ? "РЯДОМ с чертежом"
        : ("в папке " + outRoot + (dup ? " + копия рядом с чертежом" : ""))));
    scan(root, false, limit, outRoot, dup);
  }

  static void usage() {
    System.out.println("creo_pdf scan <папка> [--out <папка PDF>] [--dup] [--limit N] | " +
                       "export <папка> [лимит, 0=без ограничения] [--out <папка PDF>] [--dup] [open] | " +
                       "pdf <папка> <имя> [out] |\n" +
                       "         config-scan | config-find | config-read [config.pro] | config-load <config.pro> |\n" +
                       "         creo-find | creo-start [config.pro] [--dry]\n" +
                       "  --out <папка> — складывать PDF в ОТДЕЛЬНУЮ папку (структура подпапок зеркалится);\n" +
                       "  --dup         — дополнительно копировать PDF рядом с чертежом;\n" +
                       "  без --out PDF пишется рядом с чертежом (прежнее поведение).");
  }

  static String readOpt(Session s, String k) {
    try { return String.valueOf(s.GetConfigOption(k)); } catch (Throwable t) { return "(нет)"; }
  }

  /** Значение переменной окружения или запасное: bat передаёт сюда пути из единого файла настроек. */
  static String envOr(String name, String def) {
    String v = System.getenv(name);
    return (v == null || v.isEmpty()) ? def : v;
  }

  /** Путь установки Creo: сначала настройка (CREO_INSTALL из bat), потом реестр, потом скан папок.
    *  Благодаря настройке инструмент переносится на другую версию Creo без правки кода. */
  static String findParametric() {
    String fromEnv = System.getenv("CREO_INSTALL");
    if (fromEnv != null && !fromEnv.isEmpty()) {
      File exe0 = new File(fromEnv, "bin" + File.separator + "parametric.exe");
      if (exe0.isFile()) return exe0.getPath();
    }
    try {
      Process p = new ProcessBuilder("reg", "query", "HKLM\\SOFTWARE\\PTC\\PTC Creo Parametric", "/s")
          .redirectErrorStream(true).start();
      try (BufferedReader r = new BufferedReader(new InputStreamReader(p.getInputStream(), StandardCharsets.UTF_8))) {
        String ln;
        while ((ln = r.readLine()) != null) {
          if (ln.contains("InstallDir") && ln.contains("REG_SZ")) {
            String dir = ln.substring(ln.indexOf("REG_SZ") + 6).trim();
            File exe = new File(dir, "bin" + File.separator + "parametric.exe");
            if (exe.isFile()) return exe.getPath();
          }
        }
      }
      p.waitFor();
    } catch (Exception e) { }
    for (String root : new String[]{"D:\\PTC\\CREO12", "D:\\PTC", "C:\\Program Files\\PTC",
                                   "C:\\Program Files (x86)\\PTC", "E:\\PTC"}) {
      File r = new File(root);
      File[] vers = r.listFiles(File::isDirectory);
      if (vers == null) continue;
      for (File v : vers) {
        File exe = new File(v, "Parametric" + File.separator + "bin" + File.separator + "parametric.exe");
        if (exe.isFile()) return exe.getPath();
      }
    }
    return null;
  }

  static void creoFind() {
    String exe = findParametric();
    System.out.println("установка Creo:");
    System.out.println("  parametric.exe : " + (exe == null ? "НЕ НАЙДЕН (реестр и скан пусты)" : exe));
    try {
      Process p = new ProcessBuilder("reg", "query", "HKLM\\SOFTWARE\\PTC\\PTC Creo Parametric\\12.4.2.0")
          .redirectErrorStream(true).start();
      try (BufferedReader r = new BufferedReader(new InputStreamReader(p.getInputStream(), StandardCharsets.UTF_8))) {
        String ln;
        while ((ln = r.readLine()) != null)
          if (ln.contains("REG_SZ") && (ln.contains("InstallDir") || ln.contains("CommonFilesLocation")))
            System.out.println("  " + ln.trim());
      }
      p.waitFor();
    } catch (Exception e) { }
  }

  /** Штатный запуск Creo: parametric.exe с рабочей папкой = папка боевого config.pro
   *  (Creo читает config.pro из рабочей папки — так же, как это делает домашний бат, но без бата). */
  static void creoStart(String cfgPath, boolean dry) {
    if (cfgPath == null || cfgPath.isEmpty()) cfgPath = envOr("CONFIG_PRO", "");
    if (cfgPath.isEmpty()) {
      System.out.println("ERR: не задан config.pro. Укажи его в аргументе или в настройках инструмента.");
      System.out.println("     (python creo_pdf_env.py --set config_pro=...)");
      return;
    }
    File cfg = new File(cfgPath);
    String startDir = cfg.getParent();
    String exe = findParametric();
    System.out.println("config.pro     : " + (cfg.isFile() ? ("ЕСТЬ " + cfg.length() + " б  ") : "НЕТ  ") + cfgPath);
    System.out.println("рабочая папка  : " + startDir);
    System.out.println("parametric.exe : " + (exe == null ? "НЕ НАЙДЕН" : exe));
    if (exe == null || startDir == null || !new File(startDir).isDirectory()) {
      System.out.println("запуск невозможен: нет exe или рабочей папки");
      return;
    }
    if (dry) { System.out.println("[dry] было бы: \"" + exe + "\"  cwd=" + startDir); return; }
    try {
      new ProcessBuilder(exe).directory(new File(startDir)).start();
      System.out.println("Creo запущен штатно: рабочая папка = " + startDir + " → config.pro подхватится оттуда");
      System.out.println("через 1-2 минуты нажми «Из сессии» — проверить сессию и домашний конфиг.");
    } catch (Exception e) { System.out.println("не удалось запустить: " + e); }
  }

  /** Поиск config.pro БЕЗ сессии Creo: известные места дома + профиль + loadpoint Creo. */
  static void configScan() {
    java.util.List<String> cand = new java.util.ArrayList<>();
    // СНАЧАЛА настройка инструмента (единый источник), потом известные места дома.
    String fromCfg = envOr("CONFIG_PRO", "");
    if (!fromCfg.isEmpty()) cand.add(fromCfg);
    cand.add("Z:\\PTC\\CREO-START\\START-STD\\config.pro");
    cand.add("Z:\\PTC\\CREO-START\\START-Config\\config.pro");
    cand.add("Z:\\PTC\\CREO-START\\START-Config\\lokal для Сергея\\config.pro");
    cand.add("Z:\\PTC\\CREO-START\\START-Config\\Иные конфиги\\config3-lokal.pro");
    cand.add("D:\\PTC\\CREO-LOCAL-SETUP\\CREO-LOCAL-START\\config.pro");
    cand.add(System.getProperty("user.home") + File.separator + "config.pro");
    for (String lp : loadPoints()) cand.add(lp + File.separator + "text" + File.separator + "config.pro");
    System.out.println("config.pro — где искать БЕЗ сессии Creo:");
    for (String p : cand) {
      File f = new File(p);
      if (!f.exists()) { System.out.println("  нет                              " + p); continue; }
      boolean house = false;
      try {
        Map<String, String> m = parseConfig(p);
        house = m.containsKey("pro_format_dir") && m.containsKey("pen_table_file")
                && m.containsKey("drawing_setup_file");
      } catch (Exception e) { }
      System.out.println("  " + (house ? "БОЕВОЙ (годен для PDF)  " : "есть, но БЕЗ домашних путей  ") +
                         f.length() + " б   " + p);
    }
    System.out.println("стартовые скрипты Creo:");
    for (String s : new String[]{"Z:\\PTC\\CREO-START\\START-STD\\CREO-START.bat",
                                 "D:\\PTC\\CREO-LOCAL-SETUP\\CREO-LOCAL-START\\Creo_LOCAL.bat"})
      System.out.println("  " + (new File(s).exists() ? "ЕСТЬ " : "нет  ") + s);
  }

  /** Каталоги Creo (loadpoint): выводим из x86e_win64 внутри java.library.path (даёт bat из настроек),
    *  затем из CREO_INSTALL, и только потом — жёсткий запасной вариант. */
  static java.util.List<String> loadPoints() {
    java.util.LinkedHashSet<String> out = new java.util.LinkedHashSet<>();
    String p = System.getProperty("java.library.path", "");
    for (String part : p.split(";")) {
      File f = new File(part);
      if (!f.getName().equalsIgnoreCase("x86e_win64")) continue;
      File arch = f, common = arch.getParentFile(), lp = (common == null ? null : common.getParentFile());
      if (lp != null) out.add(lp.getPath());
    }
    String ins = envOr("CREO_INSTALL", "");
    if (!ins.isEmpty()) {
      File d = new File(ins).getParentFile();
      if (d != null) out.add(d.getPath());
    }
    if (out.isEmpty()) out.add("D:\\PTC\\CREO12\\Creo 12.4.2.0");
    return new java.util.ArrayList<>(out);
  }

  /** Разбор config.pro: строки "ключ значение"; строки с ! и # — комментарии. */
  static Map<String, String> parseConfig(String path) throws IOException {
    Map<String, String> m = new LinkedHashMap<>();
    for (String ln : Files.readAllLines(Paths.get(path), StandardCharsets.UTF_8)) {
      String t = ln.trim();
      if (t.isEmpty() || t.startsWith("!") || t.startsWith("#")) continue;
      int i = 0;
      while (i < t.length() && !Character.isWhitespace(t.charAt(i))) i++;
      if (i <= 0 || i >= t.length()) continue;
      m.put(t.substring(0, i).toLowerCase(), t.substring(i).trim());
    }
    return m;
  }

  static java.util.Set<String> NAMES = null;   // базовые имена моделей дома (индекс, если есть)

  /** Индекс имён моделей (путь — из настроек, NAMES_INDEX; иначе рядом с движком).
    *  Без него сироты не распознаются, но инструмент работает. */
  static void loadNames() {
    String path = envOr("NAMES_INDEX", "");
    if (path.isEmpty()) {
      path = envOr("LOGS_DIR", ".");
      path = path.isEmpty() ? "model_names.txt" : (path + File.separator + "model_names.txt");
    }
    File f = new File(path);
    if (!f.isFile()) { NAMES = null; System.out.println("индекс имён моделей: нет (сироты не распознаются)"); return; }
    try {
      java.util.Set<String> s = new java.util.HashSet<>();
      for (String ln : Files.readAllLines(f.toPath(), StandardCharsets.UTF_8)) {
        ln = ln.trim();
        if (!ln.isEmpty()) s.add(ln.toLowerCase());
      }
      NAMES = s;
      System.out.println("индекс имён моделей: " + s.size() + " (сироты распознаются)");
    } catch (Throwable t) { NAMES = null; System.out.println("индекс имён не прочитан: " + t); }
  }

  /** Чертёж-сирота: рядом нет X.prt/X.asm И имени X нет в индексе моделей дома.
   *  Creo такой чертёж НЕ откроет (проверено пробой 23.09.2026) — PDF сделать нельзя. */
  static boolean isOrphan(File dir, String base) {
    if (newestByExt(dir, base, "prt") != null || newestByExt(dir, base, "asm") != null) return false;
    if (NAMES == null || NAMES.isEmpty()) return false;   // без индекса не гадаем
    return !NAMES.contains(base.toLowerCase());
  }

  /** Кодировка имён внутри .drw. Проверено на живых файлах 02.10.2026: имена лежат в UTF-8
    *  («УИСВГД-401-040-00.PRT» читается только так; в windows-1251 получается мусор «РЈРИР…»). */
  static java.nio.charset.Charset drwCharset() {
    return StandardCharsets.UTF_8;
  }

  /** Какие модели реально записаны ВНУТРИ чертежа (02.10.2026). Файл .drw двоичный, но в нём
    *  есть читаемые имена вида "C5-028_102.PRT". Чертёж может ссылаться на НЕСКОЛЬКО моделей,
    *  поэтому возвращаем ВСЕ уникальные имена без расширения, в нижнем регистре.
    *  Нужно, чтобы отчёт говорил ПРАВДУ: чертёж X.drw ссылается на модель Y.prt, и тогда
    *  «нет PDF» — не беда, а расхождение имён, лечится переименованием. */
  static java.util.List<String> modelsInside(File drw) {
    java.util.LinkedHashSet<String> out = new java.util.LinkedHashSet<>();
    try {
      byte[] b = Files.readAllBytes(drw.toPath());
      // ВАЖНО: имена в .drw лежат в UTF-8 (проверено на живых файлах), при cp1251 кириллица
      // превращается в мусор «РЈРИР» — и диагностика врёт.
      String s = new String(b, drwCharset());
      java.util.regex.Matcher m = java.util.regex.Pattern
          .compile("(?i)([^\\x00-\\x1F\\x7F]{3,80}?)\\.(PRT|ASM)")
          .matcher(s);
      while (m.find()) {
        String cand = m.group(1).trim();
        while (cand.endsWith(".") || cand.endsWith("_") || cand.endsWith("-")) cand = cand.substring(0, cand.length() - 1).trim();
        // отсекаем хвосты мусора вида «тч‚ДУИСВГД-401-040-00» (служебные префиксы внутри)
        cand = cand.replaceAll("^[^\\p{L}\\p{N}]+", "");
        if (cand.length() < 3) continue;
        if (!cand.matches("[\\p{L}\\p{N}_\\- ]+")) continue;
        out.add(cand.toLowerCase().replace(" ", "_"));
      }
    } catch (Throwable t) {
      return new java.util.ArrayList<>();
    }
    return new java.util.ArrayList<>(out);
  }

  /** Диагностика неудачного открытия: на какую модель чертёж ссылается НА САМОМ ДЕЛЕ?
    *  Печатает правду вместо бессмысленного «не удалось открыть». */
  static void explainMismatch(File dir, String base) {
    File drw = newestByExt(dir, base, "drw");
    if (drw == null) { System.out.println("    причина: файла чертежа нет"); return; }
    java.util.List<String> inside = modelsInside(drw);
    if (inside.isEmpty()) {
      System.out.println("    причина: не удалось прочитать имена моделей из " + drw.getName());
      return;
    }
    String want = base.toLowerCase().replace(" ", "_");
    if (inside.contains(want)) {
      boolean here = newestByExt(dir, want, "prt") != null || newestByExt(dir, want, "asm") != null;
      System.out.println("    причина: чертёж ссылается на свою модель " + want
          + (here ? " и она рядом есть" : " — а её в папке НЕТ")
          + "; открыть не выходит (битая ссылка, версия файла или блокировка).");
      return;
    }
    // главный случай: имя чертежа ≠ именам моделей, на которые он ссылается
    StringBuilder have = new StringBuilder(), no = new StringBuilder();
    for (String nm : inside) {
      boolean ok = newestByExt(dir, nm, "prt") != null || newestByExt(dir, nm, "asm") != null;
      if (ok) { if (have.length() > 0) have.append(", "); have.append(nm); }
      else { if (no.length() > 0) no.append(", "); no.append(nm); }
    }
    System.out.println("    ПРИЧИНА: чертёж называется " + want + ", а ссылается на модель(и): "
        + String.join(", ", inside));
    if (have.length() > 0)
      System.out.println("    рядом в этой папке ЕСТЬ: " + have + " → чертёж, вероятно, переименован; "
          + "откройте модель " + inside.get(0) + " в Creo и переименуйте чертёж под неё.");
    if (no.length() > 0)
      System.out.println("    рядом НЕТ: " + no + " → верните эти модели в папку.");
  }

  /** Экспорт PDF одного чертежа: cd в папку -> retrieve -> Display -> Export -> уборка.
   *  Если по имени не нашлось — пробуем по ИМЕНИ ФАЙЛА (внутреннее имя модели могло разойтись с файлом). */
  static void doPdf(Session s, String dir, String name, String out, String dupDir) throws Exception {
    s.ChangeDirectory(dir);
    boolean wasInSession = false;
    try { wasInSession = (s.GetModel(name, ModelType.MDL_DRAWING) != null); } catch (Throwable t) { }
    Model m;
    try {
      m = s.RetrieveModel(pfcModel.ModelDescriptor_Create(ModelType.MDL_DRAWING, name, null));
    } catch (Throwable t1) {
      File src = newestDrw(new File(dir), name);
      if (src == null) throw t1;
      Model mm = null; Throwable last = t1;
      // 0) сборочный чертёж: сперва поднимаем сборку с тем же именем (Creo сам разберётся с исполнением)
      if (newestByExt(new File(dir), name, "asm") != null) {
        try {
          System.out.println("  пробую сперва поднять сборку " + name + ".asm"); System.out.flush();
          s.RetrieveModel(pfcModel.ModelDescriptor_Create(ModelType.MDL_ASSEMBLY, name, null));
          mm = s.RetrieveModel(pfcModel.ModelDescriptor_Create(ModelType.MDL_DRAWING, name, null));
          System.out.println("  чертёж открылся после подъёма сборки");
        } catch (Throwable t0) {
          System.out.println("    через сборку не вышло: " + t0); mm = null;
        }
      }
      // 1..4) варианты по имени файла
      if (mm == null) {
        String[] variants = {name + ".drw", new File(dir, name + ".drw").getPath(), name};
        for (String v : variants) {
          try {
            System.out.println("  по имени не нашлось — пробую открыть как «" + v + "»"); System.out.flush();
            mm = s.RetrieveModel(pfcModel.ModelDescriptor_CreateFromFileName(v));
            break;
          } catch (Throwable t2) {
            System.out.println("    не вышло: " + t2);
            last = t2;
          }
        }
      }
      if (mm == null) {
        // Не выбрасываем голый XToolkitNotFound: сначала читаем из .drw, на какую модель
        // он ссылается. Иначе отчёт говорит «нет модели», хотя модель рядом есть (02.10.2026).
        explainMismatch(new File(dir), name);
        throw new Exception("не удалось открыть чертёж ни по имени, ни по файлу: " + last);
      }
      m = mm;
    }
    m.Display();
    String path = out + File.separator + name + ".pdf";
    m.Export(path, pdfInstr(OPEN_PDF));
    File f = new File(path);
    boolean okf = f.exists() && f.length() > 0;
    System.out.println("  PDF " + (okf ? ("OK " + f.length() + " б  " + f.getName()) : ("НЕ СОЗДАН " + f.getName())));
    System.out.flush();
    // копия рядом с чертежом (когда вывод идёт в отдельную папку)
    if (okf && dupDir != null && !dupDir.equalsIgnoreCase(f.getParent())) {
      try {
        File near = new File(dupDir, f.getName());
        Files.copy(f.toPath(), near.toPath(), StandardCopyOption.REPLACE_EXISTING);
        System.out.println("  + копия рядом с чертежом: " + near.length() + " б  " + near.getName());
      } catch (Throwable t) {
        System.out.println("  (копию рядом сделать не удалось: " + t + ")");
      }
      System.out.flush();
    }
    if (okf && OPEN_PDF) {
      try { java.awt.Desktop.getDesktop().open(f); System.out.println("  (PDF открыт в просмотрщике)"); }
      catch (Throwable t) { System.out.println("  (открыть PDF не удалось: " + t + ")"); }
    }
    if (!wasInSession) {
      try { m.Erase(); System.out.println("  (чертёж убран из сессии Creo — окно закрыто)"); }
      catch (Throwable t) { System.out.println("  (убрать чертёж не удалось: " + t + ")"); }
    }
  }

  /** Инструкции PDF: с явным управлением «запускать просмотрщик». */
  static PDFExportInstructions pdfInstr(boolean launchViewer) throws Exception {
    PDFExportInstructions ins = pfcExport.PDFExportInstructions_Create();
    try {
      com.ptc.pfc.pfcExport.PDFOptions opts = com.ptc.pfc.pfcExport.PDFOptions.create();
      com.ptc.pfc.pfcExport.PDFOption o = pfcExport.PDFOption_Create();
      o.SetOptionType(com.ptc.pfc.pfcExport.PDFOptionType.PDFOPT_LAUNCH_VIEWER);
      o.SetOptionValue(com.ptc.pfc.pfcArgument.pfcArgument.CreateBoolArgValue(launchViewer));
      opts.append(o);
      ins.SetOptions(opts);
    } catch (Throwable t) {
      System.out.println("  (опция «просмотрщик PDF» не применилась: " + t + ")"); System.out.flush();
    }
    return ins;
  }

  /** Новейший файл чертежа в папке: <имя>.drw или <имя>.drw.N */
  static File newestDrw(File dir, String base) { return newestByExt(dir, base, "drw"); }

  /** Новейший файл <база>.<расширение>[.N] в папке (любое расширение: drw, asm, prt). */
  static File newestByExt(File dir, String base, String ext) {
    File[] fs = dir.listFiles();
    if (fs == null) return null;
    File best = null;
    String rx = "(?i)^" + java.util.regex.Pattern.quote(base) + "\\." + ext + "(\\.\\d+)?$";
    for (File f : fs)
      if (f.isFile() && f.getName().matches(rx))
        if (best == null || f.lastModified() > best.lastModified()) best = f;
    return best;
  }

  /** Папка назначения для чертежа из <dir>: зеркало пути относительно корня скана <root>.
    *  Отдельная папка сохраняет структуру подпапок, иначе одноимённые чертежи схлопываются в один. */
  static String outDirFor(String root, String dir, String outRoot) {
    if (outRoot == null) return dir;
    int k = Math.min(root.length(), dir.length());
    String rel = dir.substring(k);
    return new File(outRoot, rel).getPath();
  }

  /** Рекурсивный сбор .drw[.N] (drw) и .pdf (pdf) по дереву; папки без прав доступа пропускаем. */
  static void walkTree(Path start, final Map<String, File> drw, final Map<String, File> pdf) throws IOException {
    Files.walkFileTree(start, new SimpleFileVisitor<Path>() {
      @Override public FileVisitResult visitFile(Path p, BasicFileAttributes at) {
        String n = p.getFileName().toString().toLowerCase();
        String dir = p.getParent().toString();
        if (n.matches(".*\\.drw(\\.\\d+)?$")) {
          String base = n.replaceAll("\\.drw(\\.\\d+)?$", "");
          File cur = drw.get(dir + "|" + base);
          if (cur == null || p.toFile().lastModified() > cur.lastModified())
            drw.put(dir + "|" + base, p.toFile());
        } else if (n.endsWith(".pdf")) {
          File prev = pdf.get(dir + "|" + n.substring(0, n.length() - 4));
          if (prev == null || p.toFile().lastModified() > prev.lastModified())
            pdf.put(dir + "|" + n.substring(0, n.length() - 4), p.toFile());
        }
        return FileVisitResult.CONTINUE;
      }
      @Override public FileVisitResult visitFileFailed(Path p, IOException e) {
        System.out.println("  нет доступа: " + p); System.out.flush();
        return FileVisitResult.CONTINUE;
      }
    });
  }

  /** Обход папки: чертежи <имя>.drw[.N], PDF <имя>.pdf; устарел, если PDF старше чертежа.
    *  При outRoot != null «нужный» PDF лежит в папке вывода (а при dup — ещё и рядом с чертежом). */
  static List<String> scan(String root, boolean quiet, int limit) { return scan(root, quiet, limit, null, false); }

  static List<String> scan(String root, boolean quiet, int limit, String outRoot, boolean dup) {
    List<String> need = new ArrayList<>();
    Path start = Paths.get(root);
    if (!Files.isDirectory(start)) { System.out.println("нет папки: " + root); return need; }
    final Map<String, File> drw = new HashMap<>(), pdf = new HashMap<>();
    try {
      // Рекурсивный обход ВСЕХ подпапок; папки без прав доступа пропускаем, а не падаем.
      walkTree(start, drw, pdf);
      // ОТДЕЛЬНАЯ ПАПКА ВЫВОДА лежит вне сканируемой папки — её обходим отдельно,
      // иначе все чертежи отмечены «НЕТ PDF», хотя файлы там уже лежат.
      if (outRoot != null) {
        Path op = Paths.get(outRoot);
        if (Files.isDirectory(op)) walkTree(op, new HashMap<String, File>(), pdf);
      }
    } catch (IOException e) { System.out.println("обход: " + e); }
    int miss = 0, stale = 0, ok = 0, orphMiss = 0, orphStale = 0;
    if (NAMES == null) loadNames();
    for (Map.Entry<String, File> e : new TreeMap<>(drw).entrySet()) {
      File d = e.getValue();
      String dir = d.getParent();
      String base = d.getName().replaceAll("\\.drw(\\.\\d+)?$", "");
      boolean orph = isOrphan(new File(dir), base);
      // ГДЕ ИЩЕМ PDF: рядом с чертежом (обычный режим) либо в папке вывода (когда она задана).
      String nearDir = dir;
      String outDir = (outRoot == null) ? dir : outDirFor(root, dir, outRoot);
      boolean separate = outRoot != null && !outDir.equalsIgnoreCase(dir);
      File p = pdf.get(outDir + "|" + base);                     // PDF в целевой папке
      File pn = separate ? pdf.get(nearDir + "|" + base) : p;    // PDF рядом с чертежом
      String showDir = separate ? outDir : dir;
      if (p == null) {
        miss++;
        if (orph) orphMiss++;
        if (!quiet) { System.out.println("  НЕТ PDF    " + (orph ? "(СИРОТА) " : "") + showDir + File.separator + base + ".pdf"); System.out.flush(); }
        need.add(dir + File.separator + base);
      } else if (p.lastModified() < d.lastModified()) {
        stale++;
        if (orph) orphStale++;
        System.out.println("  УСТАРЕЛ    " + (orph ? "(СИРОТА) " : "") + showDir + File.separator + base + ".pdf (pdf " + p.lastModified() +
                           " < drw " + d.lastModified() + ")"); System.out.flush();
        need.add(dir + File.separator + base);
      } else if (dup && separate && pn == null) {
        // PDF в папке вывода свежий, но копии рядом с чертежом нет — тоже в работу
        miss++;
        if (!quiet) { System.out.println("  НЕТ PDF рядом с чертежом (галочка «копия рядом»)  " + nearDir + File.separator + base + ".pdf"); System.out.flush(); }
        need.add(dir + File.separator + base);
      } else if (dup && separate && pn.lastModified() < d.lastModified()) {
        stale++;
        System.out.println("  УСТАРЕЛ рядом с чертежом  " + nearDir + File.separator + base + ".pdf"); System.out.flush();
        need.add(dir + File.separator + base);
      } else ok++;
      if (need.size() >= limit) break;
    }
    System.out.println("чертежей: " + drw.size() + " | PDF в порядке: " + ok +
                       " | нет PDF: " + miss + " | устарели: " + stale +
                       " | из них СИРОТ (нет модели): " + (orphMiss + orphStale));
    return need;
  }
}