import rs.Scene;
import rs.Configuration;
import java.lang.reflect.Field;
public final class R307ColdViewportRegression {
  static Field f(String s)throws Exception {Field f=Scene.class.getDeclaredField(s);f.setAccessible(true);return f;}
  static long count(boolean[][][][] t){long n=0;for(boolean[][][] p:t)for(boolean[][] a:p)for(boolean[] row:a)for(boolean v:row)if(v)n++;return n;}
  public static void main(String[] unused)throws Exception{
    Configuration.extendedZoom=false;
    Scene.activeDrawDistance=25;
    Field v=f("tileVisibility");
    boolean[][][][] initial=(boolean[][][][])v.get(null);
    if(initial!=null && initial[0][0].length!=51)throw new AssertionError("unexpected cold shape");
    long before=initial==null ? 0 : count(initial);
    if(before!=0)throw new AssertionError("not a cold viewport; initial populated="+before);
    rs.Client.viewportWidth=960;rs.Client.viewportHeight=540;
    Scene scene=new Scene(new int[4][105][105]);
    scene.drawScene(6400,6400,0,0,0,128);
    long after=count((boolean[][][][])v.get(null));
    System.out.println("R307_COLD_VIEWPORT before="+before+" after="+after+" width="+f("viewportMaxX").getInt(null));
    if(after==0)throw new AssertionError("R307_COLD_VIEWPORT_GRID_NEVER_INITIALIZED");
  }
}
