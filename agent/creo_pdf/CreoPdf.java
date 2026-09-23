import com.ptc.cipjava.*;
import com.ptc.pfc.pfcSession.*;
import com.ptc.pfc.pfcModel.*;
import com.ptc.pfc.pfcExport.*;
import com.ptc.pfc.pfcAsyncConnection.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
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
      String mode = a.length > 0 ? a[0].toLowerCase() : "help";
      if (mode.equals("scan")) { scan(a.length > 1 ? a[1] : ".", false, Integer.MAX_VALUE); return; }
      if (mode.equals("help")) { usage(); return; }

      System.loadLibrary("pfcasyncmt");
      AsyncConnection c = pfcAsyncConnection.AsyncConnection_Connect(null, null, null, 60);
      Session s = c.GetSession();
      String cwd0 = s.GetCurrentDirectory();
      System.out.println("cwd=" + cwd0);

      if (mode.equals("config-read")) {
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
    System.out.println("creo_pdf scan <папка> | export <папка> [лимит] | pdf <папка> <имя> [out] |\n" +
                       "         config-read [config.pro] | config-load <config.pro>");
  }

  static String readOpt(Session s, String k) {
    try { return String.valueOf(s.GetConfigOption(k)); } catch (Throwable t) { return "(нет)"; }
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
  }

  /** Обход папки: чертежи <имя>.drw[.N], PDF <имя>.pdf; устарел, если PDF старше чертежа. */
  static List<String> scan(String root, boolean quiet, int limit) {
    List<String> need = new ArrayList<>();
    Path start = Paths.get(root);
    if (!Files.isDirectory(start)) { System.out.println("нет папки: " + root); return need; }
    final Map<String, File> drw = new HashMap<>(), pdf = new HashMap<>();
    try {
      Files.walk(start).filter(Files::isRegularFile).forEach(p -> {
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
        if (!quiet) System.out.println("  НЕТ PDF    " + dir + File.separator + base + ".pdf");
        need.add(dir + File.separator + base);
      } else if (p.lastModified() < d.lastModified()) {
        stale++;
        System.out.println("  УСТАРЕЛ    " + dir + File.separator + base + ".pdf (pdf " + p.lastModified() +
                           " < drw " + d.lastModified() + ")");
        need.add(dir + File.separator + base);
      } else ok++;
      if (need.size() >= limit) break;
    }
    System.out.println("чертежей: " + drw.size() + " | PDF в порядке: " + ok +
                       " | нет PDF: " + miss + " | устарели: " + stale);
    return need;
  }
}