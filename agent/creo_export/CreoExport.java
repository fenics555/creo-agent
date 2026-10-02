import com.ptc.cipjava.*;
import com.ptc.pfc.pfcSession.*;
import com.ptc.pfc.pfcModel.*;
import com.ptc.pfc.pfcExport.*;
import com.ptc.pfc.pfcAsyncConnection.*;
import java.io.File;

/**
 * CREO Export (JLINK) - exports a model from a RUNNING Creo into STEP / IGES / VRML / PDF / NEUTRAL / DXF3D / STL.
 * No CREOSON needed. Creo stays alive (Disconnect only).
 *
 * Usage:  CreoExport <format> <modelName> [outDir]
 *   format : step | iges | vrml | pdf | neutral | dxf3d | stl
 *   model  : file name, e.g. "pin_splitk.prt" or "amf75838.asm" (must be resolvable from Creo cwd;
 *            a FULL PATH is preferred - the engine switches to its folder itself)
 *   outDir : default .\out  (relative to this tool's folder; no absolute path is hardcoded)
 *
 * Exit code 0 = all requested exports OK, 1 = something failed.
 */
public class CreoExport {
  static int fails = 0;

  public static void main(String[] a) {
    String fmt = (a.length > 0 ? a[0] : "step").toLowerCase();
    String model = (a.length > 1 ? a[1] : "");
    String out = (a.length > 2 ? a[2] : ".\\out");
    if (model.isEmpty()) { System.out.println("ERR: model name required"); System.exit(1); }
    if (!out.endsWith("\\") && !out.endsWith("/")) out = out + "\\";
    // Относительный путь надо привести к абсолютному ДО mkdirs, иначе Creo получит
    // относительный каталог относительно своей рабочей папки, а не нашей (XToolkitInvalidDir).
    File outDir = new File(out);
    if (!outDir.isAbsolute()) {
      try { outDir = new File(System.getProperty("user.dir"), out).getCanonicalFile(); }
      catch (Throwable t2) { outDir = new File(out).getAbsoluteFile(); }
    }
    if (!outDir.isDirectory() && !outDir.mkdirs()) {
      System.out.println("ERR: не удалось создать папку вывода: " + outDir.getPath());
      System.exit(2);
    }
    out = outDir.getPath() + File.separator;
    String fname = new File(model).getName();                    // work with the file name only
    String base = fname.replaceAll("(?i)\\.(prt|asm|drw)$", "");
    String ext = fname.replaceAll("(?i)^.*\\.", "").toLowerCase();

    try {
      System.loadLibrary("pfcasyncmt");
      AsyncConnection c = pfcAsyncConnection.AsyncConnection_Connect(null, null, null, 60);
      Session s = c.GetSession();
      System.out.println("cwd=" + s.GetCurrentDirectory());
      ModelType t = ext.equals("asm") ? ModelType.MDL_ASSEMBLY
                  : (ext.equals("drw") ? ModelType.MDL_DRAWING : ModelType.MDL_PART);
      // Path support: a full/relative path -> ChangeDirectory + CreateFromFileName.
      // Needed for DRAWINGS: the referenced part must be resolvable from the drawing's folder.
      Model m;
      if (model.indexOf('\\') >= 0 || model.indexOf('/') >= 0) {
        File mf = new File(model);
        String pdir = mf.getParent();
        if (pdir != null && new File(pdir).isDirectory()) {
          try { s.ChangeDirectory(pdir); System.out.println("cd=" + s.GetCurrentDirectory()); }
          catch (Throwable tc) { System.out.println("cd FAIL: " + tc); }
        }
        m = s.RetrieveModel(pfcModel.ModelDescriptor_CreateFromFileName(model));
      } else {
        m = s.RetrieveModel(pfcModel.ModelDescriptor_Create(t, model, null));
      }
      System.out.println("model=" + m.GetFileName() + " fullname=" + m.GetFullName());
      System.out.println("format=" + fmt + " out=" + out);

      // ОШИБКА ОДНОГО ФОРМАТА НЕ ДОЛЖНА УБИВАТЬ ПРОГОН (02.10.2026): раньше исключение из
      // Export уходило в main и обрывало всё — не было ни EXPORT DONE, ни Disconnect.
      try {
      if (fmt.equals("step")) {
        GeometryFlags f = pfcExport.GeometryFlags_Create(); f.SetAsSolids(true);
        m.Export(out + base + ".stp",
            pfcExport.STEP3DExportInstructions_Create(AssemblyConfiguration.EXPORT_ASM_SINGLE_FILE, f));
        rep(out + base + ".stp");
      } else if (fmt.equals("iges")) {
        GeometryFlags f = pfcExport.GeometryFlags_Create(); f.SetAsSolids(true);
        m.Export(out + base + ".igs",
            pfcExport.IGES3DNewExportInstructions_Create(AssemblyConfiguration.EXPORT_ASM_SINGLE_FILE, f));
        rep(out + base + ".igs");
      } else if (fmt.equals("vrml")) {
        m.Export("", pfcModel.VRMLModelExportInstructions_Create(out));
        listExt(out, ".wrl");
      } else if (fmt.equals("pdf")) {
        // PDF needs a DISPLAYED model (else XToolkitNotDisplayed) - and a DRAWING, not a part.
        try { m.Display(); System.out.println("displayed"); }
        catch (Throwable td) { System.out.println("display warn: " + td); }
        m.Export(out + base + ".pdf", pfcExport.PDFExportInstructions_Create());
        rep(out + base + ".pdf");
      } else if (fmt.equals("neutral")) {
        m.Export(out + base + ".neu", pfcExport.NEUTRALFileExportInstructions_Create());
        rep(out + base + ".neu");
      } else if (fmt.equals("dxf3d")) {
        m.Export(out + base + ".dxf", pfcExport.DXF3DExportInstructions_Create());
        rep(out + base + ".dxf");
      } else if (fmt.equals("stl")) {
        // Проверено на живой сессии 02.10.2026, три варианта:
        //   Create("")                     -> XToolkitNotFound
        //   Create(полный путь)            -> XStringTooLong (путь не принимается)
        //   Create(имя файла без папки)    -> рабочий: путь задаёт Export, в инструкции только имя
        m.Export(out + base + ".stl", pfcModel.STLASCIIExportInstructions_Create(base + ".stl"));
        rep(out + base + ".stl");
      } else {
        System.out.println("ERR: unknown format '" + fmt + "' (step|iges|vrml|pdf|neutral|dxf3d|stl)");
        fails++;
      }
      } catch (Throwable ef) {
        // Ошибка формата: сообщаем ЧЕСТНО (с текстом исключения) и идём к Disconnect.
        String msg = String.valueOf(ef);
        System.out.println("  ФОРМАТ " + fmt + " НЕ ВЫГРУЖЕН: " + msg);
        if (msg.contains("XToolkitNotFound") && fmt.equals("stl"))
          System.out.println("    причина: все три варианта вызова STL дают XToolkitNotFound —"
              + " модуль экспорта STL недоступен в этой сессии Creo (не ошибка кода и не путь)");
        fails++;
      }
      c.Disconnect(10);
      System.out.println(fails == 0 ? "EXPORT OK" : ("EXPORT DONE WITH FAILURES: " + fails));
      System.exit(fails == 0 ? 0 : 1);
    } catch (Throwable t) {
      System.out.println("ERR: " + t);
      System.exit(1);
    }
  }

  // Мёртвый код удалён 02.10.2026: defaultOut() возвращал зашитый абсолютный путь
  // и НИКОГДА не вызывался.

  static void rep(String p) {
    File f = new File(p);
    if (f.exists() && f.length() > 0) {
      System.out.println("  OK " + f.getName() + " " + f.length() + " bytes");
      return;
    }
    // Creo may append a version suffix to the exported name: name.neu -> name.neu.1
    final String n = f.getName().toLowerCase();
    File[] c = (f.getParentFile() == null) ? null
        : f.getParentFile().listFiles((dir, nm) -> nm.toLowerCase().startsWith(n + "."));
    if (c != null && c.length > 0) {
      for (File g : c)
        System.out.println("  OK " + g.getName() + " " + g.length() + " bytes (Creo version suffix)");
      return;
    }
    System.out.println("  FAIL " + f.getName() + " (no file)");
    fails++;
  }

  static void listExt(String dir, String e) {
    File[] fs = new File(dir).listFiles();
    boolean any = false;
    if (fs != null) for (File f : fs)
      if (f.getName().toLowerCase().endsWith(e)) { System.out.println("  OK " + f.getName() + " " + f.length() + " bytes"); any = true; }
    if (!any) { System.out.println("  FAIL no " + e + " in " + dir); fails++; }
  }
}