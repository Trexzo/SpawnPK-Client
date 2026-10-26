import rs.definitions.ObjectDefinition;
import rs.io.Archive;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.Arrays;
/** Source-built v309 actual cached names, action labels, model IDs and footprints. */
public final class R281RealObjectIdentityRegression {
 private static int checks;
 private static void ck(boolean ok,String why){ if(!ok)throw new AssertionError(why);checks++; }
 private static boolean action(ObjectDefinition d,String a){ return d.actions!=null&&a.equals(d.actions[0]); }
 private static boolean noActions(ObjectDefinition d){return d.actions==null||Arrays.stream(d.actions).allMatch(x->x==null);}
 private static void expect(int id,String name,int model,int x,int y,String first){
  ObjectDefinition d=ObjectDefinition.get(id);
  ck(d!=null,"definition absent ID"+id);ck(name.equals(d.name),"name ID"+id);
  ck(d.modelIds!=null&&d.modelIds.length==1&&d.modelIds[0]==model,"model ID"+id);
  ck(d.sizeX==x&&d.sizeY==y,"collision footprint ID"+id);
  ck(first==null?noActions(d):action(d,first),"menu actions ID"+id);
  System.out.println("R281_DEFINITION id="+id+" name="+d.name+" model="+model+" footprint="+x+"x"+y+" actions="+Arrays.toString(d.actions));
 }
 public static void main(String[] args)throws Exception{
  ck(args.length==1,"expected original private config.bin");
  byte[] conf=Files.readAllBytes(Paths.get(args[0]));ck(conf.length==1432547,"original config pin");
  ObjectDefinition.load(new Archive(conf,"config"));ck(ObjectDefinition.definitionCount==27283,"expected complete definition set");
  expect(2,"Cave Entrance",731,4,2,"Enter");
  expect(114,"Cooking range",5274,1,2,"Cook");
  expect(4172,"Cooking range",1219,1,2,null);
  expect(16641,"Cooking range",5274,1,2,"Cook");
  expect(22154,"Cooking range",22943,2,1,null);
  System.out.println("R281_REAL_OBJECT_ACTION_VARIANTS_PASS checks="+checks+" IDs=2,114,4172,16641,22154 duplicate_names=true");
 }
}
