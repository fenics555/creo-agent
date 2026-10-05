import com.ptc.cipjava.*;
import com.ptc.pfc.pfcSession.*;
import com.ptc.pfc.pfcModel.*;
import com.ptc.pfc.pfcAsyncConnection.*;
import com.ptc.pfc.pfcSolid.*;
import com.ptc.pfc.pfcWDimension.*;
import com.ptc.pfc.pfcBase.*;
import com.ptc.pfc.pfcUI.*;
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
          // --- ГАБАРИТ через SimpRepBoundBox (единственный путь в этом API) ---
          try {
            com.ptc.pfc.pfcSimpRep.SimpRepBoundBox sbox =
                com.ptc.pfc.pfcSimpRep.pfcSimpRep.SimpRepBoundBox_Create();
            ((com.ptc.pfc.pfcBase.pfcModel)m).GetSimpRep(sbox);
            com.ptc.pfc.pfcBase.pfcItem it = (com.ptc.pfc.pfcBase.pfcItem) sbox;
            double[] mins = sbox.GetBoxMinXYZ();
            double[] maxs = sbox.GetBoxMaxXYZ();
            System.out.printf("#BBOX %.6f %.6f %.6f %.6f %.6f %.6f%n",
                mins[0], mins[1], mins[2], maxs[0], maxs[1], maxs[2]);
            System.out.printf("#SIZE %.6f %.6f %.6f%n",
                maxs[0] - mins[0], maxs[1] - mins[1], maxs[2] - mins[2]);
          } catch (Throwable t) {
            System.out.println("#BBOX ERR: " + t);
          }
          // --- РАЗМЕРЫ ---
          try {
            com.ptc.pfc.pfcDimension.pfcDimension[] ds = m.GetDimensionsOfType(null);
            System.out.println("#DIMCOUNT " + (ds == null ? 0 : ds.length));
          } catch (Throwable t) {
            System.out.println("#DIM ERR: " + t);
          }
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