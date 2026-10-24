import rs.Scene;
import java.lang.reflect.Field;
import java.lang.reflect.Method;

/** Actual Scene renderer: adjustable visibility radius and occluder indexing. */
public final class R304VisibilityDistanceRegression {
 static int checks=0;
 static Field field(String name) throws Exception {
   Field f=Scene.class.getDeclaredField(name);f.setAccessible(true);return f;
 }
 static void eq(boolean pass,String label) {if(!pass)throw new AssertionError(label);checks++;}
 static void prepare(int requested) throws Exception {
   Scene.activeDrawDistance=requested;
   try {Scene.setViewport(500,500,800,600);}
   catch(Throwable t){throw new AssertionError("R304_VIEWPORT_RADIUS_CRASH distance="+requested+" cause="+t,t);}
   int effective=(requested>=1 && requested<=50)?requested:25;
   eq(Scene.activeDrawDistance==effective,"R304_RADIUS_NOT_ADMITTED distance="+requested);
   boolean[][][][] vis=(boolean[][][][])field("tileVisibility").get(null);
   eq(vis.length==8 && vis[0].length==32,"wrong plane/pitch visibility bands");
   for(int pitch:new int[]{0,3,7})for(int yaw:new int[]{0,15,31}){
    eq(vis[pitch][yaw].length==2*effective+1,"R304_VISIBILITY_X_SHAPE_BAD radius="+requested);
    eq(vis[pitch][yaw][0].length==2*effective+1,"R304_VISIBILITY_Y_SHAPE_BAD radius="+requested);
   }
 }
 static void occluder(int distance,int targetTile) throws Exception {
   prepare(distance);
   Scene scene=new Scene(new int[4][105][105]);
   eq(targetTile<Scene.activeDrawDistance,"invalid test target");
   int oldCount=((int[])field("field5681").get(null))[0];
   Scene.method345(0,targetTile*128,0,targetTile*128,0,0,0,1);
   eq(((int[])field("field5681").get(null))[0]==oldCount+1,"occluder not inserted");
   field("field5670").setInt(null,0);
   field("cameraTileX").setInt(null,0);
   field("cameraTileY").setInt(null,0);
   Scene.cameraX=0;Scene.cameraY=0;Scene.cameraZ=0;
   boolean[][][][] all=(boolean[][][][])field("tileVisibility").get(null);
   boolean[][] current=all[0][0];
   int row=targetTile+Scene.activeDrawDistance;
   current[row][Scene.activeDrawDistance]=true;
   field("tileVisibilityBand").set(null,current);
   Method m=Scene.class.getDeclaredMethod("method56");m.setAccessible(true);
   try {m.invoke(scene);}
   catch(java.lang.reflect.InvocationTargetException e){throw new AssertionError("R304_OCCLUDER_RADIUS_CRASH d="+distance+" tile="+targetTile+" cause="+e.getCause(),e.getCause());}
   eq(field("field5683").getInt(null)==1,"R304_OCCLUDER_LOST d="+distance+" tile="+targetTile);
 }
 public static void main(String[] args) throws Exception {
   int prev=Scene.activeDrawDistance;
   try{
    for(int d:new int[]{1,2,5,10,15,24,25,26,30,40,50,-1,0,51,Integer.MAX_VALUE,Integer.MIN_VALUE})prepare(d);
    occluder(10,9);
    occluder(15,14);
    occluder(24,23);
    occluder(25,24);
    occluder(30,29);
    occluder(40,39);
    occluder(50,40);
    for(int d:new int[]{50,25,10,50,1,24,25})prepare(d); // no stale static visibility array
    System.out.println("R304_DYNAMIC_SCENE_VISIBILITY_PASS checks="+checks);
   } finally {Scene.activeDrawDistance=prev;}
 }
}
