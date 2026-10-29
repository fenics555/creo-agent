import com.ptc.cipjava.*;
import com.ptc.pfc.pfcSession.*;
import com.ptc.pfc.pfcModel.*;
import com.ptc.pfc.pfcModelItem.*;
import com.ptc.pfc.pfcFeature.*;
import com.ptc.pfc.pfcDimension.*;
import com.ptc.pfc.pfcAsyncConnection.*;
import java.io.File;

/**
 * TreeProbe (JLINK) — ЭТАЛОН ДЕРЕВА ПОСТРОЕНИЯ для расшифровки байтов PLM Reader.
 *
 * Зачем: блочный разбор файла даёт связи и роли, но НЕ даёт дерево построения —
 * какие элементы созданы, какие ПОДАВЛЕНЫ, какие размеры (dN) у элемента и их значения,
 * какие тела участвуют в булевых операциях. Creo знает это точно — он и есть эталон.
 *
 * Вывод построчный, машиночитаемый:
 *   #MODEL <имя>
 *   #FEAT <номер> <id> <ТИП> <имя> <подавлен:0|1>
 *   #DIM  <feat_id> <имя размера dN> <значение> <unit>
 *   #PARAM <имя> <тип> <значение>
 *   #ERR <что>
 *
 * Запуск: tree_probe.bat <MODEL.prt> [MODEL2 ...]
 * Creo поднимается сам (AsyncConnection_Start), после прогона Disconnect — Creo остаётся.
 */
public class TreeProbe {
  public static void main(String[] a) {
    if (a.length == 0) { System.out.println("#ERR model path required"); System.exit(1); }
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
          // 🔴 грабля (28.10.2026): Creo ждёт имя БЕЗ номера версии — `x.prt`, а не `x.prt.1`
          // (иначе XUnknownModelExtension). Номер версии отрезаем, сам файл читается по папке.
          String fname = mf.getName();
          if (fname.matches("(?i).+\\.(prt|asm|drw)\\.\\d+$")) {
            fname = fname.replaceFirst("(?i)(\\.(?:prt|asm|drw))\\.\\d+$", "$1");
          }
          Model m = s.RetrieveModel(pfcModel.ModelDescriptor_CreateFromFileName(fname));
          System.out.println("#MODEL " + mf.getName());
          dumpTree(s, m);
        } catch (Throwable t) {
          bad++;
          System.out.println("#ERR " + model + " : " + t);
        }
      }
      c.Disconnect(null);
      System.exit(bad == 0 ? 0 : 1);
    } catch (Throwable t) {
      System.out.println("#ERR fatal: " + t);
      System.exit(2);
    }
  }

  /** Тип элемента ЧИТАЕМО: enum -> имя константы (FEAT_PROTRUSION, FEAT_REVOLVE, FEAT_CUT ...). */
  static String featTypeName(Feature f) {
    try {
      Object t = f.GetFeatType();
      if (t == null) return "null";
      // ФАКТ API (из pfcasync.jar): enum FeatureType хранит номер в поле `__Value`,
      // а наверх отдаётся через метод `getValue()`. Ни toString, ни name() не помогают.
      for (String meth : new String[]{"getValue", "__Value", "name"}) {
        try {
          java.lang.reflect.Method m = t.getClass().getMethod(meth);
          Object v = m.invoke(t);
          if (v != null) return "TYPE_" + v;
        } catch (Throwable ignored) {}
      }
      try {
        java.lang.reflect.Field fl = t.getClass().getDeclaredField("__Value");
        fl.setAccessible(true);
        return "TYPE_" + fl.get(t);
      } catch (Throwable ignored) {}
      String s = t.toString();
      int at = s.indexOf('@');
      return at > 0 ? s.substring(0, at) : s;
    } catch (Throwable e) {
      return "?";
    }
  }

  /** Дерево построения: элементы модели (факт API из pfcasync.jar: ITEM_FEATURE / ITEM_DIMENSION). */
  static void dumpTree(Session s, Model m) {
    ModelItems feats;
    int n;
    try {
      feats = ModelItemOwner_cast(m).ListItems(ModelItemType.ITEM_FEATURE);
      n = feats.getarraysize();
    } catch (Exception t) {
      System.out.println("#ERR no feature list: " + t);
      return;
    }
    System.out.println("#FEAT-COUNT " + n);
    // ВСЕ размеры модели одним заходом: у Feature нет списка размеров (ClassCastException),
    // поэтому берём ITEM_DIMENSION у модели и фильтруем по feat_id владельца.
    ModelItems modelDims = null;
    try {
      modelDims = ModelItemOwner_cast(m).ListItems(ModelItemType.ITEM_DIMENSION);
      System.out.println("#DIM-COUNT " + modelDims.getarraysize());
    } catch (Exception t) {
      System.out.println("#DIMERR model list: " + t);
    }
    for (int i = 0; i < n; i++) {
      try {
        Feature f = (Feature) feats.get(i);
        int id = f.GetId();
        String fname = "";
        try { fname = f.GetName(); } catch (Throwable ignored) {}
        // 🔴 ТИП: у Feature есть ГОТОВОЕ ИМЯ ТИПА (GetFeatTypeName) и ПОДТИП (GetFeatSubType).
        // Числовой GetFeatType — НЕ печатать как основу: вид берётся строкой от Creo.
        String ftypeNum = featTypeName(f);          // числовой код (справочно)
        String ftypeName = "";
        try { ftypeName = String.valueOf(f.GetFeatTypeName()); } catch (Throwable ignored) {}
        String fsub = "";
        try { fsub = String.valueOf(f.GetFeatSubType()); } catch (Throwable ignored) {}   // GetFeatSubType
        // СТАТУС: FeatureStatus — FEAT_SUPPRESSED / FEAT_FAMILY_TABLE_SUPPRESSED /
        // FEAT_SIMP_REP_SUPPRESSED / FEAT_PROGRAM_SUPPRESSED (точные имена из pfcasync.jar).
        // Плюс GetIsVisible/GetIsReadonly и статусы группы (GetGroupStatus).
        String fstat = "";
        try {
          Object st = f.GetStatus();
          if (st != null) {
            String sv = String.valueOf(st);
            int at = sv.indexOf('@');
            fstat = at > 0 ? sv.substring(0, at) : sv;
            try { Object v = st.getClass().getMethod("getValue").invoke(st);
                  if (v != null) fstat = fstat + "(" + v + ")"; } catch (Throwable ignored) {}
          }
        } catch (Throwable ignored) {}
        String vis = "";
        try { vis = String.valueOf(f.GetIsVisible()); } catch (Throwable ignored) {}
        System.out.println("#FEAT " + i + " " + id + " TYPENAME=" + ftypeName + " SUB=" + fsub
                           + " TYPENUM=" + ftypeNum + " NAME=" + fname
                           + " status=" + fstat + " visible=" + vis);
        // РАЗМЕРЫ: у Feature НЕТ ModelItemOwner (проверено: ClassCastException), поэтому
        // берём размеры МОДЕЛИ и фильтруем по владельцу — `GetOwner()`/`GetFeatId`.
        if (modelDims != null) {
          for (int k = 0; k < modelDims.getarraysize(); k++) {
            try {
              Dimension d = (Dimension) modelDims.get(k);
              // ФАКТ API (из pfcasync.jar): ModelItem -> GetId()/GetName(), BaseDimension -> GetSymbol()
              String dname = "";
              String sym = "";
              int did = -1;
              double val = 0.0;
              try { dname = d.GetName(); } catch (Throwable ignored) {}
              try { sym = d.GetSymbol(); } catch (Throwable ignored) {}   // "d12" — имя размера в Creo
              try { did = ((com.ptc.pfc.pfcModelItem.ModelItem) d).GetId(); } catch (Throwable ignored) {}
              try { val = d.GetDimValue(); } catch (Throwable ignored) {}
              // ДОПУСК/КВАЛИТЕТ: класс DimTolISODIN (ISO-квалитет). Берём имя таблицы и колонку —
              // это и есть обозначение посадки (H7, 6g, f7). В файле оно лежит ТЕКСТОМ.
              String tol = "";
              try {
                Object tv = d.GetTolerance();
                if (tv != null) {
                  String tn = "", tc = "";
                  try { Object r = tv.getClass().getMethod("GetTableName").invoke(tv);
                        if (r != null) tn = String.valueOf(r); } catch (Throwable ignored) {}
                  try { Object r = tv.getClass().getMethod("GetTableColumn").invoke(tv);
                        if (r != null) tc = String.valueOf(r); } catch (Throwable ignored) {}
                  tol = ("table=" + tn + " col=" + tc).trim();
                  if (tol.equals("table= col=")) tol = tv.getClass().getSimpleName();
                }
              } catch (Throwable ignored) {}
              // ТИП размера: линейный / радиус / диаметр / угол / дуга.
              // ФАКТ: у enum DimensionType нет toString -> номер берём reflective (как у FeatureType).
              String dtype = "";
              try {
                Object dt = d.GetDimType();
                if (dt != null) {
                  for (String meth : new String[]{"getValue", "__Value", "name"}) {
                    try {
                      Object v = dt.getClass().getMethod(meth).invoke(dt);
                      if (v != null) { dtype = "TYPE_" + v; break; }
                    } catch (Throwable ignored) {}
                  }
                  if (dtype.isEmpty()) {
                    String sdt = dt.toString();
                    int at = sdt.indexOf('@');
                    dtype = at > 0 ? sdt.substring(0, at) : sdt;
                  }
                }
              } catch (Throwable ignored) {}
              System.out.println("#DIM feat=" + id + " sym=" + sym + " dimid=" + did
                                 + " dtype=" + dtype + " val=" + val + " tol=" + tol);
            } catch (Throwable t) {
              System.out.println("#DIMERR feat=" + id + " : " + t);
            }
          }
        }
      } catch (Throwable t) {
        System.out.println("#ERR feat " + i + ": " + t);
      }
    }
    // параметры модели — сверка с тем, что читает скан из байтов
    try {
      ParameterOwner po = ParameterOwner_cast(m);
      Parameters ps = po.ListParams();
      for (int i = 0; i < ps.getarraysize(); i++) {
        Parameter p = (Parameter) ps.get(i);
        String pn = "";
        try { pn = p.GetName(); } catch (Throwable ignored) {}
        String pv = "";
        try {
          ParamValue v = p.GetValue();
          // факт API: у ParamValue берём строковое/числовое значение тем геттером, что есть в jar
          try { pv = v.GetStringValue(); }
          catch (Throwable e1) {
            try { pv = String.valueOf(v.GetDoubleValue()); }
            catch (Throwable e2) { pv = String.valueOf(v); }
          }
        } catch (Throwable ignored) {}
        System.out.println("#PARAM " + pn + " " + pv);
      }
    } catch (Throwable t) {
      System.out.println("#ERR params: " + t);
    }
  }

  static ModelItemOwner ModelItemOwner_cast(Object o) { return (ModelItemOwner) o; }
  static ParameterOwner ParameterOwner_cast(Object o) { return (ParameterOwner) o; }
}
