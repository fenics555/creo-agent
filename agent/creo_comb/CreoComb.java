import com.ptc.cipjava.*;
import com.ptc.pfc.pfcSession.*;
import com.ptc.pfc.pfcModel.*;
import com.ptc.pfc.pfcAsyncConnection.*;
import com.ptc.pfc.pfcModelItem.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/**
 * ЧЕСАЛКА (CreoComb) — JLINK, без CREOSON.
 * Причёсывает детали и сборки по ЭТАЛОНУ (шаблон из config.pro): уравнения и параметры.
 * ПРАВИЛО ДОМА: сначала только чтение (scan), запись — отдельным режимом add с бэкапом.
 *
 * Режимы:
 *   tpl-plan [config.pro]        - какие шаблоны прописаны в конфиге и какие файлы реально есть
 *   dump     <папка|файл> [имя]  - показать уравнения и параметры одной модели (Creo)
 *   scan     <папка> [config]    - чего не хватает моделям папки против шаблонов (ТОЛЬКО ЧТЕНИЕ)
 */
public class CreoComb {
  static final String CFG_DEFAULT = "Z:\\PTC\\CREO-START\\START-STD\\config.pro";
  static final String[] TPL_KEYS = {
    "template_solidpart", "template_designasm", "template_sheetmetalpart",
    "template_mfgmold", "template_mfgcast", "template_mfgnc", "template_mold_layout", "template_drawing"
  };
  static int LIMIT = 500;   // предохранитель: сколько моделей максимум трогаем за проход

  public static void main(String[] a) {
    try {
      for (int i = 0; i < a.length; i++) a[i] = a[i].replace("\"", "").trim();
      String mode = a.length > 0 ? a[0].toLowerCase() : "help";
      if (mode.equals("help")) { usage(); return; }
      if (mode.equals("tpl-plan")) { tplPlan(a.length > 1 ? a[1] : CFG_DEFAULT); return; }

      System.loadLibrary("pfcasyncmt");
      Session s = connect().GetSession();
      System.out.println("cwd сессии = " + s.GetCurrentDirectory());
      if (mode.equals("refs")) { refs(s, a.length > 1 ? a[1] : CFG_DEFAULT); return; }
      if (mode.equals("dump")) { dump(s, a.length > 1 ? a[1] : "", a.length > 2 ? a[2] : ""); return; }
      if (mode.equals("scan")) { scan(s, a.length > 1 ? a[1] : "", a.length > 2 ? a[2] : CFG_DEFAULT); return; }
      if (mode.equals("scan-here")) { scan(s, s.GetCurrentDirectory(), a.length > 1 ? a[1] : CFG_DEFAULT); return; }
      usage();
    } catch (Throwable t) {
      System.out.println("ОШИБКА: " + t);
      t.printStackTrace();
    }
  }

  /** Открыть модель по ФАЙЛУ (имя может быть с версией .N): три попытки, как делает дом.
   *  1) по имени модели (Creo сам возьмёт новейшую версию), 2) по файлу без версии, 3) как есть. */
  static Model openAny(Session s, File f) throws Exception {
    String n = f.getName();
    String low = n.toLowerCase();
    boolean asm = low.matches(".*\\.asm(\\.\\d+)?$");
    String base = n.replaceAll("\\.(prt|asm|drw|frm|sec|lay)(\\.\\d+)?$", "");
    s.ChangeDirectory(f.getParent());
    Throwable last = null;
    try { return s.RetrieveModel(pfcModel.ModelDescriptor_Create(
            asm ? ModelType.MDL_ASSEMBLY : ModelType.MDL_PART, base, null)); }
    catch (Throwable t) { last = t; }
    try { return s.RetrieveModel(pfcModel.ModelDescriptor_CreateFromFileName(
            new File(f.getParent(), base + (asm ? ".asm" : ".prt")).getPath())); }
    catch (Throwable t) { last = t; }
    try { return s.RetrieveModel(pfcModel.ModelDescriptor_CreateFromFileName(f.getPath())); }
    catch (Throwable t) { last = t; }
    throw new Exception("не открылась " + n + " (" + last + ")");
  }

  /** Подключение к Creo. Если сессий несколько, обычный Connect даёт XToolkitAmbiguous —
   *  поэтому сначала берём АКТИВНУЮ сессию (окно на переднем плане), и лишь потом общий Connect. */
  static AsyncConnection connect() throws Exception {
    try {
      AsyncConnection c = pfcAsyncConnection.AsyncConnection_GetActiveConnection();
      if (c != null) return c;
    } catch (Throwable t) {
      System.out.println("(активной сессии нет: " + t + ")");
    }
    return pfcAsyncConnection.AsyncConnection_Connect(null, null, null, 60);
  }

  static void usage() {
    System.out.println("ЧЕСАЛКА (JLINK, без CREOSON):");
    System.out.println("  creo_comb.bat tpl-plan [config.pro]       - шаблоны из конфига: путь, файл, версия");
    System.out.println("  creo_comb.bat refs                        - уравнения и параметры ЭТАЛОНОВ (нужен Creo)");
    System.out.println("  creo_comb.bat dump <папка|файл> [имя]     - уравнения+параметры модели (нужен Creo)");
    System.out.println("  creo_comb.bat scan <папка> [config.pro]   - чего не хватает против шаблонов (только чтение)");
    System.out.println("  creo_comb.bat scan-here [config.pro]      - то же, но по ТЕКУЩЕЙ папке сессии (пути без кириллицы в аргументах)");
  }

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

  /** Новейшая версия Creo-файла: <база>.<расширение>[.N] в папке. */
  static File newest(File dir, String base, String ext) {
    if (dir == null || !dir.isDirectory()) return null;
    File[] fs = dir.listFiles();
    if (fs == null) return null;
    File best = null;
    String rx = "(?i)^" + java.util.regex.Pattern.quote(base) + "\\." + ext + "(\\.\\d+)?$";
    for (File f : fs)
      if (f.isFile() && f.getName().matches(rx))
        if (best == null || f.lastModified() > best.lastModified()) best = f;
    return best;
  }

  /** Путь из config.pro -> существующий файл Creo (с учётом версий .N и смешанных слэшей). */
  static File resolveTpl(String value) {
    if (value == null || value.isEmpty()) return null;
    String v = value.replace('/', File.separatorChar).replace('\\', File.separatorChar);
    if (v.contains("$PRO_DIRECTORY")) return null;   // подстановка каталога Creo — проверить в сессии
    File f = new File(v);
    File dir = f.getParentFile();
    String name = f.getName();
    int dot = name.lastIndexOf('.');
    if (dot < 0) return null;
    return newest(dir, name.substring(0, dot), name.substring(dot + 1));
  }

  static void tplPlan(String cfgPath) {
    System.out.println("ЧЕСАЛКА: план шаблонов (эталонов)");
    File cfg = new File(cfgPath);
    System.out.println("config.pro: " + (cfg.isFile() ? ("ЕСТЬ " + cfg.length() + " б  ") : "НЕТ  ") + cfgPath);
    if (!cfg.isFile()) return;
    Map<String, String> m;
    try { m = parseConfig(cfgPath); } catch (Exception e) { System.out.println("не прочитать: " + e); return; }
    System.out.println();
    for (String k : TPL_KEYS) {
      String v = m.get(k);
      if (v == null) { System.out.println(String.format("  %-24s — в конфиге не задан", k)); continue; }
      File f = resolveTpl(v);
      String st;
      if (v.contains("$PRO_DIRECTORY")) st = "ПЕРЕМЕННАЯ $PRO_DIRECTORY (каталог Creo) — проверить в сессии";
      else if (f == null) st = "ФАЙЛА НЕТ (битая настройка!)";
      else st = "ЕСТЬ " + f.length() + " б   " + f.getName();
      System.out.println(String.format("  %-24s %s", k, st));
      System.out.println(String.format("  %-24s   прописано: %s", "", v));
    }
  }

  /** Открыть модель по файлу или по имени+папке (только чтение, без сохранения). */
  static Model openModel(Session s, String dir, String name) throws Exception {
    if (name == null || name.isEmpty()) {
      File any = new File(dir);
      if (any.isFile()) return s.RetrieveModel(pfcModel.ModelDescriptor_CreateFromFileName(any.getPath()));
      throw new Exception("укажите папку и имя модели, или путь к файлу");
    }
    s.ChangeDirectory(dir);
    boolean asm = newest(new File(dir), name, "asm") != null && newest(new File(dir), name, "prt") == null;
    ModelType t = asm ? ModelType.MDL_ASSEMBLY : ModelType.MDL_PART;
    try {
      return s.RetrieveModel(pfcModel.ModelDescriptor_Create(t, name, null));
    } catch (Throwable e1) {
      File f = asm ? newest(new File(dir), name, "asm") : newest(new File(dir), name, "prt");
      if (f == null) throw new Exception("нет файла " + name + " в " + dir + " (" + e1 + ")");
      return s.RetrieveModel(pfcModel.ModelDescriptor_CreateFromFileName(f.getPath()));
    }
  }

  static List<String> toList(stringseq seq) throws Exception {
    List<String> out = new ArrayList<>();
    if (seq == null) return out;
    for (int i = 0; i < seq.getarraysize(); i++) out.add(seq.get(i));
    return out;
  }

  /** Нормализация уравнения для сравнения: без пробелов/регистра/точек с запятой. */
  static String norm(String rel) {
    return (rel == null ? "" : rel).replaceAll("\\s+", "").replace(";", "").toLowerCase();
  }

  static List<String> relations(Model m, boolean post) {
    try { return toList(post ? m.GetPostRegenerationRelations() : m.GetRelations()); }
    catch (Throwable t) { return new ArrayList<>(); }
  }

  static String paramValue(Parameter p) {
    try {
      ParamValue v = p.GetValue();
      switch (v.Getdiscr().getValue()) {
        case ParamValueType._PARAM_STRING: return v.GetStringValue();
        case ParamValueType._PARAM_INTEGER: return String.valueOf(v.GetIntValue());
        case ParamValueType._PARAM_DOUBLE: return String.valueOf(v.GetDoubleValue());
        case ParamValueType._PARAM_BOOLEAN: return String.valueOf(v.GetBoolValue());
        default: return v.GetStringValue();
      }
    } catch (Throwable t) { return "?"; }
  }

  static Map<String, String> params(Model m) {
    Map<String, String> out = new LinkedHashMap<>();
    try {
      Parameters ps = m.ListParams();
      for (int i = 0; i < ps.getarraysize(); i++) {
        Parameter p = ps.get(i);
        String val = paramValue(p);
        boolean rel = false;
        try { rel = p.GetIsRelationDriven(); } catch (Throwable t) { }
        out.put(p.GetName(), val + (rel ? "  (из уравнения)" : ""));
      }
    } catch (Throwable t) { }
    return out;
  }

  static void dump(Session s, String dir, String name) throws Exception {
    Model m = openModel(s, dir, name);
    System.out.println("модель: " + m.GetFileName() + "   тип: " + m.GetType());
    List<String> rel = relations(m, false), post = relations(m, true);
    System.out.println("\nУРАВНЕНИЯ (" + rel.size() + "):");
    for (int i = 0; i < rel.size(); i++) System.out.println("  " + (i + 1) + ") " + rel.get(i));
    System.out.println("\nУРАВНЕНИЯ ПОСТРЕГЕНЕРАЦИИ (" + post.size() + "):");
    for (int i = 0; i < post.size(); i++) System.out.println("  " + (i + 1) + ") " + post.get(i));
    Map<String, String> p = params(m);
    System.out.println("\nПАРАМЕТРЫ (" + p.size() + "):");
    for (Map.Entry<String, String> e : p.entrySet())
      System.out.println("  " + e.getKey() + " = " + e.getValue());
  }

  /** Показать ЭТАЛОНЫ: уравнения и параметры шаблонов из config.pro (без аргументов-путей). */
  static void refs(Session s, String cfgPath) throws Exception {
    Map<String, String> cfg = parseConfig(cfgPath);
    String[] keys = {"template_solidpart", "template_designasm", "template_sheetmetalpart"};
    for (String k : keys) {
      File f = resolveTpl(cfg.get(k));
      System.out.println("\n=== " + k + " -> " + (f == null ? "НЕ НАЙДЕН (" + cfg.get(k) + ")" : f.getPath()));
      if (f == null) continue;
      Ref r = readRef(s, f);
      System.out.println("уравнения (" + r.rel.size() + "):");
      for (String x : r.rel) System.out.println("   " + x.trim());
      System.out.println("уравнения пострегенерации (" + r.post.size() + "):");
      for (String x : r.post) System.out.println("   " + x.trim());
      System.out.println("параметры (" + r.par.size() + "):");
      for (Map.Entry<String, String> e : r.par.entrySet())
        System.out.println("   " + e.getKey() + " = " + e.getValue());
    }
  }

  static void scan(Session s, String root, String cfgPath) throws Exception {
    File dir = new File(root);
    if (!dir.isDirectory()) { System.out.println("нет папки: " + root); return; }
    Map<String, String> cfg = parseConfig(cfgPath);
    String cwd0 = null;
    try { cwd0 = s.GetCurrentDirectory(); } catch (Throwable t) { }

    File tplPart = resolveTpl(cfg.get("template_solidpart"));
    File tplAsm = resolveTpl(cfg.get("template_designasm"));
    System.out.println("ЭТАЛОН детали  : " + (tplPart == null ? "не найден" : tplPart.getPath()));
    System.out.println("ЭТАЛОН сборки  : " + (tplAsm == null ? "не найден" : tplAsm.getPath()));
    if (tplPart == null && tplAsm == null) { System.out.println("нет эталонов — нечего сравнивать"); return; }

    Ref refPart = tplPart == null ? null : readRef(s, tplPart);
    Ref refAsm = tplAsm == null ? null : readRef(s, tplAsm);
    if (refPart != null) System.out.println("в эталоне детали : уравнений " + refPart.rel.size() + ", пострег. " +
                                           refPart.post.size() + ", параметров " + refPart.par.size());
    if (refAsm != null) System.out.println("в эталоне сборки : уравнений " + refAsm.rel.size() + ", пострег. " +
                                          refAsm.post.size() + ", параметров " + refAsm.par.size());

    List<File> models = new ArrayList<>();
    try {
      Files.walk(dir.toPath(), 6).forEach(p -> {
        String n = p.getFileName().toString().toLowerCase();
        if (n.matches(".*\\.(prt|asm)(\\.\\d+)?$")) {
          String base = n.replaceAll("\\.(prt|asm)(\\.\\d+)?$", "");
          File f = p.getParent().toFile();
          File best = newest(f, base, n.contains(".asm") ? "asm" : "prt");
          if (best != null && best.equals(p.toFile()) && !models.contains(best)) models.add(best);
        }
      });
    } catch (Exception e) { System.out.println("обход: " + e); }
    System.out.println("\nмоделей к проверке: " + models.size() + " (лимит " + LIMIT + ")\n");

    int checked = 0, clean = 0;
    List<String> report = new ArrayList<>();
    for (File f : models) {
      if (checked >= LIMIT) { System.out.println("…лимит достигнут"); break; }
      boolean isAsm = f.getName().toLowerCase().matches(".*\\.asm(\\.\\d+)?$");
      Ref ref = isAsm ? refAsm : refPart;
      if (ref == null) continue;
      if (tplPart != null && f.equals(tplPart)) continue;
      if (tplAsm != null && f.equals(tplAsm)) continue;
      Model m = null;
      try {
        m = openAny(s, f);
        checked++;
        List<String> rel = relations(m, false), post = relations(m, true);
        Map<String, String> par = params(m);
        List<String> missRel = missing(ref.rel, rel), missPost = missing(ref.post, post);
        List<String> missPar = new ArrayList<>(), emptyPar = new ArrayList<>();
        for (String k : ref.par.keySet()) {
          if (!par.containsKey(k)) missPar.add(k);
          else if (par.get(k).startsWith("?")) emptyPar.add(k);
        }
        if (missRel.isEmpty() && missPost.isEmpty() && missPar.isEmpty() && emptyPar.isEmpty()) {
          clean++;
        } else {
          report.add(String.format("%-46s нет уравнений: %-3d пострег: %-3d нет параметров: %-3d пустые: %d",
                     f.getName(), missRel.size(), missPost.size(), missPar.size(), emptyPar.size()));
          if (!missRel.isEmpty()) report.add("        уравнения:  " + missRel);
          if (!missPost.isEmpty()) report.add("        постреген.: " + missPost);
          if (!missPar.isEmpty()) report.add("        параметры:  " + missPar);
          if (!emptyPar.isEmpty()) report.add("        пустые:     " + emptyPar);
        }
      } catch (Throwable t) {
        report.add(String.format("%-46s ОШИБКА открытия: %s", f.getName(), t));
      } finally {
        if (m != null) { try { m.Erase(); } catch (Throwable t) { } }
      }
    }
    System.out.println("ОТЧЁТ (проверено " + checked + ", в порядке " + clean + "):");
    for (String l : report) System.out.println("  " + l);
    if (report.isEmpty()) System.out.println("  — расхождений нет");
    try { if (cwd0 != null) s.ChangeDirectory(cwd0); } catch (Throwable t) { }
  }

  static List<String> missing(List<String> ref, List<String> have) {
    Set<String> h = new HashSet<>();
    for (String x : have) h.add(norm(x));
    List<String> out = new ArrayList<>();
    for (String r : ref) {
      String t = r == null ? "" : r.trim();
      if (t.isEmpty() || t.startsWith("/*") || t.startsWith("!")) continue;   // служебные строки — не требование
      if (!h.contains(norm(t))) out.add(t);
    }
    return out;
  }

  static class Ref {
    List<String> rel = new ArrayList<>(), post = new ArrayList<>();
    Map<String, String> par = new LinkedHashMap<>();
  }

  static Ref readRef(Session s, File f) {
    Ref r = new Ref();
    Model m = null;
    String cwd0 = null;
    try { cwd0 = s.GetCurrentDirectory(); } catch (Throwable t) { }
    try {
      m = openAny(s, f);
      r.rel = relations(m, false);
      r.post = relations(m, true);
      r.par = params(m);
    } catch (Throwable t) {
      System.out.println("  эталон не открылся: " + f.getName() + " — " + t);
    } finally {
      if (m != null) { try { m.Erase(); } catch (Throwable t) { } }
      try { if (cwd0 != null) s.ChangeDirectory(cwd0); } catch (Throwable t) { }
    }
    return r;
  }
}
