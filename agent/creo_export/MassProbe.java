import com.ptc.cipjava.*;
import com.ptc.pfc.pfcSession.*;
import com.ptc.pfc.pfcModel.*;
import com.ptc.pfc.pfcAsyncConnection.*;
import com.ptc.pfc.pfcSolid.*;
import java.io.File;

/**
 * ProbeAll (JLINK) — ЭТАЛОН из запущенного Creo: масса/объём/площадь + ГАБАРИТ + РАЗМЕРЫ.
 *
 * Зачем: габарит и размеры не читаются из байтов (05.10.2026), а эталон нужен, чтобы
 * понять формат. МассProbe их не давал.
 *
 * Вывод построчный: #MASS / #BBOX / #DIM <имя> <значение>
 */
public class MassProbe {
  public static void main(String[] a) {
    if (a.length == 0) { System.out.println("ERR: model path required"); System.exit(1); }
    try {
      System.loadLibrary("pfcasyncmt");
      AsyncConnection c = pfcAsyncConnection.AsyncConnection_Connect(null, null, null, 60);
      Session s = c.GetSession();
      System.out.println("# cwd=" + s.GetCurrentDirectory());
      int bad = 0;
      for (String model : a) {
        try {
          File mf = new File(model);
          String pdir = mf.getParent();
          if (pdir != null && new File(pdir).isDirectory()) s.ChangeDirectory(pdir);
          Model m = s.RetrieveModel(pfcModel.ModelDescriptor_CreateFromFileName(model));
          System.out.println("#MODEL " + mf.getName());
          try {
            Solid sol = (Solid) m;
            MassProperty mp = sol.GetMassProperty(null);
            System.out.printf("#MASS MASS=%.17g VOLUME=%.17g AREA=%.17g%n",
                mp.GetMass(), mp.GetVolume(), mp.GetSurfaceArea());
          } catch (Throwable t) {
            System.out.println("#MASS ERR: " + t);
          }
          // --- ГАБАРИТ: НЕ ДОСТУПЕН через этот API (проверено 05.10.2026) ---
          // Перебрано: pfcModel.GetBBox / pfcSolid.GetBBox / GetBoundingBox /
          // Session.CreateBBox / Solid.GetBodyBBox / SimpRepBoundBox_Create+GetSimpRep.
          // В pfcasync.jar (Creo 12.4.2) класса pfcBBox НЕТ вовсе, а SimpRepBoundBox
          // имеет только GetType(). Вывод: габарит из Creo программно не достаётся —
          // нужен либо Web.Link (creojs), либо ручной замер.
          System.out.println("#BBOX N/A — в этом API габарит не отдаётся");
        } catch (Throwable t) {
          System.out.println(new File(model).getName() + "\tERR: " + t);
          bad++;
        }
      }
      c.Disconnect(10);
      System.out.println("# done, failures=" + bad);
      System.exit(bad == 0 ? 0 : 1);
    } catch (Throwable t) {
      System.out.println("ERR: " + t);
      System.exit(2);
    }
  }
}