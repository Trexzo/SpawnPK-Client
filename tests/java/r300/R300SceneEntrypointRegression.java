import java.lang.reflect.*;
import rs.Scene;
import rs.Tile;
import rs.model.Class11;
/** Actual-class regression: invalid scene planes, bridge shifts, object footprints. */
public final class R300SceneEntrypointRegression {
  static int checks;
  static void yes(boolean good, String why) { if (!good) throw new AssertionError(why); checks++; }
  static void noThrow(String label, Runnable task) {
    try { task.run(); checks++; }
    catch (RuntimeException e) { throw new AssertionError("R300_SCENE_BOUNDARY_CRASH "+label,e); }
  }
  static Object call(Method m, Scene scene, Object...args) {
    try { return m.invoke(scene,args); }
    catch (InvocationTargetException e) { throw new AssertionError("R300_SCENE_PLACEMENT_CRASH "+m.getName()+" cause="+e.getCause(),e.getCause()); }
    catch (Exception e) { throw new AssertionError(e); }
  }
  public static void main(String[] ignored) throws Exception {
    int[] bad={-1,4,Integer.MIN_VALUE,Integer.MAX_VALUE};
    for(int plane:bad) {
      Scene s=new Scene(new int[4][105][105]);
      noThrow("setPlane("+plane+")", ()->s.setPlane(plane));
      yes(s.tiles[0][50][50]==null,"invalid plane allocated map tile");
    }
    Scene goodPlane=new Scene(new int[4][105][105]);
    goodPlane.setPlane(2);
    yes(goodPlane.tiles[2][0][0]!=null && goodPlane.tiles[2][103][103]!=null,"valid plane fill lost");
    for(int x:new int[]{-1,104,Integer.MIN_VALUE,Integer.MAX_VALUE}) {
      Scene s=new Scene(new int[4][105][105]);
      noThrow("method3365 x="+x, ()->s.method3365(50,x));
      yes(s.tiles[0][50][50]==null,"invalid x changed unrelated tile");
    }
    for(int y:new int[]{-1,104,Integer.MIN_VALUE,Integer.MAX_VALUE}) {
      Scene s=new Scene(new int[4][105][105]);
      noThrow("method3365 y="+y, ()->s.method3365(y,50));
      yes(s.tiles[0][50][50]==null,"invalid y changed unrelated tile");
    }
    Scene bridge=new Scene(new int[4][105][105]);
    Tile lower=new Tile(0,50,50),upper=new Tile(1,50,50);
    bridge.tiles[0][50][50]=lower;bridge.tiles[1][50][50]=upper;
    bridge.method3365(50,50);
    yes(bridge.tiles[0][50][50]==upper,"valid bridge plane shift lost");
    yes(bridge.tiles[0][50][50].field5070==lower,"valid bridge lower tile reference lost");
    yes(bridge.tiles[3][50][50]==null,"valid bridge upper plane not cleared");
    Method a=Scene.class.getDeclaredMethod("method3408",int.class,int.class,int.class,int.class,int.class,int.class,int.class,int.class,Class11.class,int.class,boolean.class,int.class,byte.class,int.class);
    Method b=Scene.class.getDeclaredMethod("method2959",int.class,int.class,int.class,int.class,int.class,int.class,int.class,int.class,Class11.class,int.class,boolean.class,int.class,byte.class);
    a.setAccessible(true);b.setAccessible(true);
    for(Method method:new Method[]{a,b}) {
      for(int plane:bad) {
        Scene s=new Scene(new int[4][105][105]);
        Object result=placement(method,s,plane,50,50,1,1);
        yes(Boolean.FALSE.equals(result),"invalid plane allowed: "+method.getName()+" plane="+plane);
        yes(s.tiles[0][50][50]==null,"invalid plane allocated tile");
      }
      for(int[] shape:new int[][]{{0,1},{1,0},{-1,1},{1,-1}}) {
        Scene s=new Scene(new int[4][105][105]);
        yes(Boolean.FALSE.equals(placement(method,s,1,50,50,shape[0],shape[1])),"nonpositive placement footprint allowed");
        yes(s.tiles[1][50][50]==null,"invalid footprint inserted object");
      }
      for(int[] point:new int[][]{{-1,50},{104,50},{50,-1},{50,104}}) {
        Scene s=new Scene(new int[4][105][105]);
        yes(Boolean.FALSE.equals(placement(method,s,1,point[0],point[1],1,1)),"off-tile object placement succeeded");
        yes(s.tiles[1][50][50]==null,"invalid tile changed in-range object");
      }
      Scene valid=new Scene(new int[4][105][105]);
      yes(Boolean.TRUE.equals(placement(method,valid,1,50,50,1,1)),"valid object placement refused");
      yes(valid.tiles[1][50][50]!=null,"valid object tile not allocated");
      yes(valid.tiles[1][50][50].field5057==1,"valid object occupancy not recorded");
    }
    System.out.println("R300_SCENE_PLANE_TILESHIFT_OBJECT_PLACEMENT_PASS checks="+checks);
  }
  static Object placement(Method method,Scene s,int p,int x,int y,int w,int h){
    if(method.getName().equals("method3408"))return call(method,s,p,x,y,w,h,0,0,0,null,0,false,123,(byte)0,0);
    return call(method,s,p,x,y,w,h,0,0,0,null,0,false,123,(byte)0);
  }
}
