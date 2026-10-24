import java.nio.file.*;
import java.lang.reflect.*;
import java.util.*;
import rs.Client;
import rs.definitions.ObjectDefinition;
import rs.definitions.Class41;
import rs.io.Archive;
public final class R283RegionBankSelectionRegression {
  static int checks;
  static void ck(boolean b,String why){if(!b)throw new AssertionError(why);checks++;}
  static String action(ObjectDefinition d){return d.actions==null?null:d.actions[0];}
  static void expect(int id,int model,String name,String opt){
    ObjectDefinition x=ObjectDefinition.get(id),raw=ObjectDefinition.method2342(id);
    ck(x!=null && raw!=null,"missing definition "+id);
    ck(name.equals(x.name),"wrong definition name "+id);
    ck(x.modelIds!=null&&x.modelIds.length==1&&x.modelIds[0]==model,"bad model "+id);
    ck(Objects.equals(action(x),opt),"wrong option "+id+":"+action(x));
    ck(Objects.equals(action(x),action(raw)),"runtime/raw disagreement "+id);
  }
  public static void main(String[] args)throws Exception {
    ck(args.length==1,"config.bin argument");
    byte[] config=Files.readAllBytes(Paths.get(args[0]));
    ck(config.length==1432547,"authentic config length");
    ObjectDefinition.load(new Archive(config,"config"));
    Client c=new Client();
    Field legacy=Client.class.getDeclaredField("field407");legacy.setAccessible(true);
    Field osrs=Client.class.getDeclaredField("field408");osrs.setAccessible(true);
    Integer[] regions=(Integer[])legacy.get(c),osrsRegions=(Integer[])osrs.get(c);
    ck(regions.length>40,"legacy region mapping incomplete");
    ck(Arrays.asList(regions).contains(13129),"real listed legacy OSRS region missing");
    ck(!Arrays.asList(regions).contains(12593),"standard region wrongly legacy OSRS");
    ck(osrsRegions.length==0,"unexpected OSRS-config region list populated");
    ObjectDefinition.method1991(Class41.field1133);
    ck(ObjectDefinition.field1166==Class41.field1133,"standard bank not selected");
    expect(114,5274,"Cooking range",null);
    ck(!"Cooking range".equals(ObjectDefinition.get(16641).name),"standard ID16641 must not masquerade as cooking range");
    expect(16641,10464,ObjectDefinition.get(16641).name,"Climb-down");
    ObjectDefinition.method1991(Class41.field1134);
    ck(ObjectDefinition.field1166==Class41.field1134,"legacy OSRS bank not selected");
    expect(114,5274,"Cooking range","Cook");
    expect(16641,5274,"Cooking range","Cook");
    ObjectDefinition.method1991(Class41.field1133);
    expect(114,5274,"Cooking range",null);
    ck(ObjectDefinition.field1166==Class41.field1133,"standard restored");
    System.out.println("R283_AUTHENTIC_REGION_BANK_SELECTOR_PASS checks="+checks+" legacy_region=13129 standard_region=12593 osrs_config_region_list=0 cook_in_legacy=true cook_in_standard=false");
  }
}