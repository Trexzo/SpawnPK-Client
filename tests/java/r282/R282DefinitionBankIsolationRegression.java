import java.nio.file.*;
import java.security.MessageDigest;
import java.util.Arrays;
import rs.definitions.ObjectDefinition;
import rs.definitions.Class41;
import rs.io.Archive;
/** Exact actual compiled R278 ObjectDefinition bank-sensitive object action regression. */
public final class R282DefinitionBankIsolationRegression {
 private static int checks;
 private static void ck(boolean value,String msg){if(!value)throw new AssertionError(msg); checks++;}
 private static String first(ObjectDefinition d){return d.actions==null||d.actions.length==0?null:d.actions[0];}
 private static void expect(String phase,Class41 expected,String action114,int model16641,String action16641){
  ck(ObjectDefinition.field1166==expected,phase+" unexpected active definition bank");
  ObjectDefinition d=ObjectDefinition.get(114);
  ObjectDefinition raw=ObjectDefinition.method2342(114);
  ck(d!=null&&raw!=null,phase+" missing object114");
  ck(d.id==114&&raw.id==114,phase+" wrong identity");
  ck("Cooking range".equals(d.name),phase+" name");
  ck(d.modelIds!=null&&d.modelIds.length==1&&d.modelIds[0]==5274,phase+" model");
  ck(d.sizeX==1&&d.sizeY==2,phase+" footprint");
  ck(java.util.Objects.equals(first(d),action114),phase+" action: "+Arrays.toString(d.actions));
  ck(java.util.Objects.equals(first(raw),action114),phase+" raw decoded action: "+Arrays.toString(raw.actions));
  ck(Arrays.equals(d.actions,raw.actions),phase+" runtime vs raw action drift");
  ck(ObjectDefinition.cache.b(114)==null,phase+" unexpected cached override");
  ck(!ObjectDefinition.field1163.method2602(114),phase+" unexpected override file");
  ObjectDefinition alt=ObjectDefinition.get(16641);
  ck(alt!=null&&alt.id==16641,phase+" secondary identity");
  ck(alt.modelIds!=null&&alt.modelIds.length==1&&alt.modelIds[0]==model16641,phase+" secondary model");
  ck(java.util.Objects.equals(first(alt),action16641),phase+" secondary action");
  ObjectDefinition cave=ObjectDefinition.get(2);
  ck(cave!=null&&"Enter".equals(first(cave)),phase+" cave behavior regression");
  System.out.println("R282_BANK_VERIFIED phase="+phase+" mode="+expected.name()+" id114_model=5274 action="+action114+
    " id16641_model="+model16641+" action="+action16641+" raw_agrees=true overrides=false");
 }
 public static void main(String[] args)throws Exception {
  ck(args.length==1,"expected original private config.bin");
  byte[] config=Files.readAllBytes(Paths.get(args[0]));
  ck(config.length==1432547,"unexpected config archive bytes");
  ObjectDefinition.load(new Archive(config,"config"));
  ck(ObjectDefinition.definitionCount==27283,"unexpected original legacy object count");
  // The override parser initializes an OSRS definition bank as a side effect.
  // This is what made the earlier R281 source-only test misleading about the live region.
  expect("R281_INITIAL_CONFIG_LOAD",Class41.field1136,"Cook",5274,"Cook");
  ObjectDefinition.method1991(Class41.field1133);
  expect("REAL_GUI_STANDARD_REGION",Class41.field1133,null,10464,"Climb-down");
  ObjectDefinition.method1991(Class41.field1134);
  expect("LEGACY_OSRS_REGION",Class41.field1134,"Cook",5274,"Cook");
  ObjectDefinition.method1991(Class41.field1136);
  expect("OSRS_CONFIG_REGION",Class41.field1136,"Cook",5274,"Cook");
  ObjectDefinition.method1991(Class41.field1133);
  expect("RESTORED_STANDARD_REGION",Class41.field1133,null,10464,"Climb-down");
  System.out.println("R282_ACTUAL_CLIENT_OBJECT_BANK_ISOLATION_PASS checks="+checks+" modes=3 transitions=4 object114_standard_action=none object114_osrs_action=Cook no_production_patch=true");
 }
}
