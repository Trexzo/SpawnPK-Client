import java.lang.reflect.Method;
import java.lang.reflect.InvocationTargetException;
import rs.Scene;
import rs.Tile;
import java.lang.reflect.Field;
/** Authentic Scene mutations must ignore stale scene coordinates without throwing. */
public class R299SceneMutationBoundsRegression {
  static int checks = 0;
  static final String[] METHODS = {"method251", "method3478", "method93", "method1252", "method1390", "method1152", "method1627"};
  static Object[] args(String name, int plane, int x, int y) {
    switch(name) {
      case "method251": return new Object[]{plane,x,y,1};
      case "method3478": return new Object[]{y,8,x,plane};
      case "method93": return new Object[]{x,plane,y,(byte)-119};
      case "method1252": return new Object[]{y,plane,x};
      case "method1390": return new Object[]{plane,x,y};
      case "method1152": return new Object[]{plane,y,x};
      case "method1627": return new Object[]{plane,x,y};
      default: throw new IllegalArgumentException(name);
    }
  }
  static void call(Scene scene, String name,int p,int x,int y) throws Exception {
    Method m;
    switch(name) {
      case "method251": case "method3478": m=Scene.class.getMethod(name,int.class,int.class,int.class,int.class);break;
      case "method93": m=Scene.class.getMethod(name,int.class,int.class,int.class,byte.class);break;
      default:m=Scene.class.getMethod(name,int.class,int.class,int.class);
    }
    try {
      m.invoke(scene,args(name,p,x,y));
    } catch (InvocationTargetException e) {
      throw new AssertionError("R299_SCENE_MUTATION_BOUNDARY_CRASH method="+name+" scene="+p+","+x+","+y+" cause="+e.getCause(),e.getCause());
    }
    checks++;
  }
  public static void main(String[] ignored) throws Exception {
    Scene scene = new Scene(new int[4][105][105]);
    int[] bad={-1,104,105,Integer.MIN_VALUE,Integer.MAX_VALUE};
    for(String name:METHODS) {
      for(int dimension=0;dimension<3;dimension++)for(int v:bad) {
        int[] loc={1,50,50}; loc[dimension]=v;
        call(scene,name,loc[0],loc[1],loc[2]);
      }
      for(int[] loc:new int[][]{{0,0,0},{3,103,103},{1,50,50},{2,0,103}})
        call(scene,name,loc[0],loc[1],loc[2]);
    }
    // In-bounds updates must still operate on their real Tile, not be discarded.
    Tile valid = new Tile(1,50,50);
    scene.tiles[1][50][50] = valid;
    Method setLevel = Scene.class.getMethod("method251",int.class,int.class,int.class,int.class);
    setLevel.invoke(scene,1,50,50,37);
    Field level=Tile.class.getDeclaredField("field5061");level.setAccessible(true);
    if(level.getInt(valid)!=37)throw new AssertionError("R299_VALID_SCENE_TILE_MUTATION_LOST");checks++;
    // method93's legacy byte-dependent side effect must remain valid only for real tiles.
    Field toggle=Scene.class.getDeclaredField("field5661");toggle.setAccessible(true);
    Method removal=Scene.class.getMethod("method93",int.class,int.class,int.class,byte.class);
    boolean before=toggle.getBoolean(scene);
    removal.invoke(scene,50,-1,50,(byte)3);
    if(toggle.getBoolean(scene)!=before)throw new AssertionError("R299_INVALID_SCENE_MUTATION_SIDE_EFFECT");checks++;
    removal.invoke(scene,50,1,50,(byte)3);
    if(toggle.getBoolean(scene)==before)throw new AssertionError("R299_VALID_SCENE_MUTATION_SIDE_EFFECT_LOST");checks++;
    System.out.println("R299_SCENE_MUTATION_BOUNDS_PASS checks="+checks+" methods="+METHODS.length);
  }
}
