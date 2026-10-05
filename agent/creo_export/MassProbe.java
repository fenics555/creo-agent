import com.ptc.cipjava.*;
import com.ptc.pfc.pfcSession.*;
import com.ptc.pfc.pfcModel.*;
import com.ptc.pfc.pfcAsyncConnection.*;
import com.ptc.pfc.pfcSolid.*;
import java.io.File;

/**
 * MassProbe (JLINK) - reads MassProperty of a model from a RUNNING Creo. No CREOSON.
 * Usage: MassProbe <fullPathToPrt> [<fullPathToPrt> ...]
 * Prints one line per model: MASS / VOLUME / AREA with full double precision.
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
          Solid sol = (Solid) m;
          MassProperty mp = sol.GetMassProperty(null);
          // %.17g - полная точность double, иначе сравнение с байтами невозможно
          System.out.printf("%s\tMASS=%.17g\tVOLUME=%.17g\tAREA=%.17g%n",
              mf.getName(), mp.GetMass(), mp.GetVolume(), mp.GetSurfaceArea());
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