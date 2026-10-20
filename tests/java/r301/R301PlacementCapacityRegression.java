import java.lang.reflect.*;
import rs.Scene;
import rs.model.Class11;

/** Real compiled Scene: tracked-object capacity must reject before tile changes. */
public class R301PlacementCapacityRegression {
 static int checks=0;
 static final int[] BAD={-1,5000,5001,Integer.MAX_VALUE};
 static Field capacityField;
 static Method builder(String method)throws Exception {
  Method m;
  if(method.equals("method3408")){
   m=Scene.class.getDeclaredMethod(method,int.class,int.class,int.class,int.class,int.class,int.class,int.class,int.class,Class11.class,int.class,boolean.class,int.class,byte.class,int.class);
  }else{
   m=Scene.class.getDeclaredMethod(method,int.class,int.class,int.class,int.class,int.class,int.class,int.class,int.class,Class11.class,int.class,boolean.class,int.class,byte.class);
  }
  m.setAccessible(true);return m;
 }
 static boolean place(Method m,Scene scene,boolean tracked) throws Exception {
  try {
   Object x=m.getName().equals("method3408")
    ?m.invoke(scene,1,50,50,1,1,0,0,0,null,0,tracked,999,(byte)0,0)
    :m.invoke(scene,1,50,50,1,1,0,0,0,null,0,tracked,999,(byte)0);
   return Boolean.TRUE.equals(x);
  }catch(InvocationTargetException e){throw new AssertionError("R301_SCENE_OBJECT_CAPACITY_CRASH method="+m.getName()+" tracked="+tracked+" cause="+e.getCause(),e.getCause());}
 }
 static void check(boolean v,String msg){if(!v)throw new AssertionError(msg);checks++;}
 public static void main(String[] ignored)throws Exception{
  capacityField=Scene.class.getDeclaredField("field5665");capacityField.setAccessible(true);
  for(String name:new String[]{"method3408","method2959"}){
   Method method=builder(name);
   for(int invalid:BAD){
    Scene scene=new Scene(new int[4][105][105]);capacityField.setInt(scene,invalid);
    check(!place(method,scene,true),"R301_CAPACITY_INVALID_TRACKED_WAS_ACCEPTED "+name+" "+invalid);
    check(scene.tiles[1][50][50]==null,"R301_PARTIALLY_COMMITTED_BAD_CAPACITY "+name+" "+invalid);
    check(capacityField.getInt(scene)==invalid,"R301_INVALID_CAPACITY_MUTATED_COUNTER "+name+" "+invalid);
   }
   for(int valid:new int[]{0,4999}){
    Scene scene=new Scene(new int[4][105][105]);capacityField.setInt(scene,valid);
    check(place(method,scene,true),"R301_VALID_TRACKED_PLACEMENT_REJECTED "+name+" "+valid);
    check(capacityField.getInt(scene)==valid+1,"R301_VALID_COUNTER_NOT_ADVANCED "+name+" "+valid);
    check(scene.tiles[1][50][50]!=null && scene.tiles[1][50][50].field5057==1,"R301_VALID_OBJECT_NOT_INSERTED "+name+" "+valid);
   }
   Scene untracked=new Scene(new int[4][105][105]);capacityField.setInt(untracked,5000);
   check(place(method,untracked,false),"R301_UNTRACKED_PLACEMENT_REJECTED "+name);
   check(capacityField.getInt(untracked)==5000,"R301_UNTRACKED_CHANGED_COUNTER "+name);
   check(untracked.tiles[1][50][50]!=null && untracked.tiles[1][50][50].field5057==1,"R301_UNTRACKED_LOST_OBJECT "+name);
  }
  System.out.println("R301_TRACKED_OBJECT_CAPACITY_PASS checks="+checks);
 }
}
