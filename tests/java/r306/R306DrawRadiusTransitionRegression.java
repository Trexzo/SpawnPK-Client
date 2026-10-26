import rs.Scene;
import rs.Tile;
import rs.Configuration;
import java.lang.reflect.Field;
import java.lang.reflect.Method;

/** A real Scene.drawScene render after switching the radius must rebuild its visibility grid. */
public final class R306DrawRadiusTransitionRegression {
 static int checks=0;
 static Field get(String name)throws Exception{Field f=Scene.class.getDeclaredField(name);f.setAccessible(true);return f;}
 static void verify(boolean ok,String why){if(!ok)throw new AssertionError(why);checks++;}
 static boolean[][][][] visibility()throws Exception{return (boolean[][][][])get("tileVisibility").get(null);}
 static void draw(Scene scene,int radius)throws Exception{
  Scene.activeDrawDistance=radius;
  try{scene.drawScene(6400,6400,0,0,0,128);}
  catch(Throwable e){throw new AssertionError("R306_STALE_RENDER_VISIBILITY_CRASH radius="+radius+" cause="+e,e);}
  verify(Scene.activeDrawDistance==radius,"active radius changed");
  verify(visibility()[0][0].length==2*radius+1,"stale grid at radius "+radius);
  verify(get("viewportMaxX").getInt(null)==960 && get("viewportMaxY").getInt(null)==540,"viewport dimensions not retained");
 }
 public static void main(String[] args)throws Exception{
  Configuration.extendedZoom=false;
  Scene.activeDrawDistance=25;
  Scene.setViewport(500,800,960,540);
  Scene scene=new Scene(new int[4][105][105]);
  // A visible actual Tile lies inside the legacy software traversal (25), but
  // outside the old 51-cell grid when its center is remapped to radius 50.
  scene.tiles[0][74][50]=new Tile(0,74,50);
  verify(visibility()[0][0].length==51,"bad initial radius25 visibility grid");
  for(int d:new int[]{50,10,1,25,50,25,5,30}){
   draw(scene,d);
   boolean[][][][] stable=visibility();
   draw(scene,d);
   verify(stable==visibility(),"radius "+d+" rebuilt unnecessarily on unchanged next frame");
  }
  draw(scene,10);
  Method visible=Scene.class.getDeclaredMethod("isVisibleSceneTile",int.class,int.class); visible.setAccessible(true);
  boolean[][] band=(boolean[][])get("tileVisibilityBand").get(null);
  band[10][10]=true;
  verify(Boolean.TRUE.equals(visible.invoke(null,50,50)),"center visible cell unexpectedly culled");
  verify(Boolean.FALSE.equals(visible.invoke(null,74,50)),"off-radius tile unexpectedly visible");
  verify(Boolean.FALSE.equals(visible.invoke(null,-100,50)),"negative tile unexpectedly visible");
  verify(Boolean.FALSE.equals(visible.invoke(null,50,999)),"far tile unexpectedly visible");
  System.out.println("R306_DYNAMIC_DRAW_RADIUS_TRANSITIONS_PASS checks="+checks+" transitions=9");
 }
}
