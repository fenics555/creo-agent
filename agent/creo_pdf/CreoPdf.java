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

  public static void main(String[] a) {
    try {
      for (int i = 0; i < a.length; i++) a[i] = a[i].replace("\"", "").trim();   // терпим кавычки в путях
      String mode = a.length > 0 ? a[0].toLowerCase() : "help";
      if (mode.equals("scan")) { scan(a.length > 1 ? a[1] : ".", false, Integer.MAX_VALUE); return; }
      if (mode.equals("config-scan")) { configScan(); return; }
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
              a.length > 3 ? a[3] : (a.length > 1 ? a[1] : "."));
      } else if (mode.equals("export")) {
        String dir = a.length > 1 ? a[1] : ".";
        int limit = a.length > 2 ? Integer.parseInt(a[2]) : 100;
        if (limit <= 0) limit = Integer.MAX_VALUE;      // 0 = без ограничения
        List<String> need = scan(dir, false, limit);
        System.out.println("к обработке: " + need.size());
        int ok = 0, bad = 0;
        for (String base : need) {
          File f = new File(base);
          try { doPdf(s, f.getParent(), f.getName(), f.getParent()); ok++; }
          catch (Throwable t) { System.out.println("  ОШИБКА " + f.getName() + ": " + t); bad++; }
        }
        System.out.println("ИТОГО: сделано " + ok + ", ошибок " + bad);
      } else usage();
      try { s.ChangeDirectory(cwd0); System.out.println("cwd восстановлена: " + cwd0); } catch (Throwable t) {}
      c.Disconnect(10);
      System.out.println("готово");
    } catch (Throwable t) { System.out.println("ERR: " + t); }
  }

  static void usage() {
    System.out.println("creo_pdf scan <папка> | export <папка> [лимит, 0=без ограничения] | pdf <папка> <имя> [out] |\n" +
                       "         config-scan | config-find | config-read [config.pro] | config-load <config.pro>");
  }

  static String readOpt(Session s, String k) {
    try { return String.valueOf(s.GetConfigOption(k)); } catch (Throwable t) { return "(нет)"; }
  }

  /** Поиск config.pro БЕЗ сессии Creo: известные места дома + профиль + loadpoint Creo. */
  static void configScan() {
    java.util.List<String> cand = new java.util.ArrayList<>();
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

  /** Каталоги Creo (loadpoint): выводим из x86e_win64 внутри java.library.path. */
  static java.util.List<String> loadPoints() {
    java.util.LinkedHashSet<String> out = new java.util.LinkedHashSet<>();
    String p = System.getProperty("java.library.path", "");
    for (String part : p.split(";")) {
      File f = new File(part);
      if (!f.getName().equalsIgnoreCase("x86e_win64")) continue;
      File arch = f, common = arch.getParentFile(), lp = (common == null ? null : common.getParentFile());
      if (lp != null) out.add(lp.getPath());
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

  /** Экспорт PDF одного чертежа: cd в папку -> retrieve -> Display -> Export. */
  static void doPdf(Session s, String dir, String name, String out) throws Exception {
    s.ChangeDirectory(dir);
    Model m = s.RetrieveModel(pfcModel.ModelDescriptor_Create(ModelType.MDL_DRAWING, name, null));
    try { m.Display(); } catch (Throwable t) { System.out.println("  display warn: " + t); }
    String path = out + File.separator + name + ".pdf";
    m.Export(path, pfcExport.PDFExportInstructions_Create());
    File f = new File(path);
    System.out.println("  PDF " + (f.exists() && f.length() > 0
        ? ("OK " + f.length() + " б  " + f.getName()) : ("НЕ СОЗДАН " + f.getName())));
    System.out.flush();
  }

  /** Обход папки: чертежи <имя>.drw[.N], PDF <имя>.pdf; устарел, если PDF старше чертежа. */
  static List<String> scan(String root, boolean quiet, int limit) {
    List<String> need = new ArrayList<>();
    Path start = Paths.get(root);
    if (!Files.isDirectory(start)) { System.out.println("нет папки: " + root); return need; }
    final Map<String, File> drw = new HashMap<>(), pdf = new HashMap<>();
    try {
      // Рекурсивный обход ВСЕХ подпапок; папки без прав доступа пропускаем, а не падаем.
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
            pdf.put(dir + "|" + n.substring(0, n.length() - 4), p.toFile());
          }
          return FileVisitResult.CONTINUE;
        }
        @Override public FileVisitResult visitFileFailed(Path p, IOException e) {
          System.out.println("  нет доступа: " + p); System.out.flush();
          return FileVisitResult.CONTINUE;
        }
      });
    } catch (IOException e) { System.out.println("обход: " + e); }
    int miss = 0, stale = 0, ok = 0;
    for (Map.Entry<String, File> e : new TreeMap<>(drw).entrySet()) {
      File p = pdf.get(e.getKey());
      File d = e.getValue();
      String dir = d.getParent();
      String base = d.getName().replaceAll("\\.drw(\\.\\d+)?$", "");
      if (p == null) {
        miss++;
        if (!quiet) { System.out.println("  НЕТ PDF    " + dir + File.separator + base + ".pdf"); System.out.flush(); }
        need.add(dir + File.separator + base);
      } else if (p.lastModified() < d.lastModified()) {
        stale++;
        System.out.println("  УСТАРЕЛ    " + dir + File.separator + base + ".pdf (pdf " + p.lastModified() +
                           " < drw " + d.lastModified() + ")"); System.out.flush();
        need.add(dir + File.separator + base);
      } else ok++;
      if (need.size() >= limit) break;
    }
    System.out.println("чертежей: " + drw.size() + " | PDF в порядке: " + ok +
                       " | нет PDF: " + miss + " | устарели: " + stale);
    return need;
  }
}