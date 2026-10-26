import rs.Scene;
import java.lang.reflect.Field;
import java.util.Arrays;

/** Actual compiled rs.Scene occluder-plane and slot-capacity regression. */
public final class R302OccluderCapacityRegression {
 static int checks = 0;
 static void check(boolean b,String msg){if(!b)throw new AssertionError(msg);checks++;}
 static void invoke(int plane){
  try {Scene.method345(plane,128,0,256,512,0,128,256);}
  catch(RuntimeException e){throw new AssertionError("R302_OCCLUDER_BOUNDS_CRASH plane="+plane+" cause="+e,e);}
 }
 public static void main(String[] args) throws Exception {
  Field counts=Scene.class.getDeclaredField("field5681");counts.setAccessible(true);
  Field slots=Scene.class.getDeclaredField("field5682");slots.setAccessible(true);
  int[] oldcounts=(int[])counts.get(null);
  Object[][] oldslots=(Object[][])slots.get(null);
  int[] isolated=new int[oldcounts.length];
  Object[][] arrays=(Object[][])java.lang.reflect.Array.newInstance(oldslots[0].getClass().getComponentType(),oldslots.length,oldslots[0].length);
  try {
   counts.set(null,isolated);slots.set(null,arrays);
   check(isolated.length==4,"unexpected plane count");
   check(arrays[0].length==500,"unexpected occluder capacity");
   for(int bad:new int[]{-1,4,Integer.MIN_VALUE,Integer.MAX_VALUE}) {
    invoke(bad);
    check(Arrays.equals(isolated,new int[4]),"invalid plane changed counters");
   }
   isolated[1]=-1;invoke(1);check(isolated[1]==-1,"negative counter advanced");
   isolated[1]=501;invoke(1);check(isolated[1]==501,"oversized counter advanced");
   isolated[1]=500;invoke(1);check(isolated[1]==500,"at-capacity counter advanced");
   for(int i=0;i<500;i++) {
    invoke(0);
    check(isolated[0]==i+1,"counter incorrect after slot "+i);
    check(arrays[0][i]!=null,"occluder missing from slot "+i);
   }
   check(isolated[0]==500,"500 valid occluders did not insert");
   check(arrays[0][0]!=null && arrays[0][499]!=null,"first/last valid occluder missing");
   invoke(0);check(isolated[0]==500,"overflow changed full capacity counter");
   isolated[2]=0;invoke(2);check(isolated[2]==1,"empty plane did not accept occluder");
   // The original arrays can be released during recovery. Late occluder events must be harmless.
   counts.set(null,null);invoke(0);check(counts.get(null)==null,"released counters unexpectedly restored");
   counts.set(null,isolated);slots.set(null,null);invoke(0);check(slots.get(null)==null,"released slot tables unexpectedly restored");
   slots.set(null,arrays);
   isolated[3]=499;invoke(3);check(isolated[3]==500 && arrays[3][499]!=null,"last slot not accepted");
   System.out.println("R302_OCCLUDER_CAPACITY_PASS checks="+checks);
  } finally {counts.set(null,oldcounts);slots.set(null,oldslots);}
 }
}
