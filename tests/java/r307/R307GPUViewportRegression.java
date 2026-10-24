import rs.Scene;
import rs.Client;
import rs.gpu.GpuRenderer;
import java.lang.reflect.Field;
public class R307GPUViewportRegression {
 static Field f(Class<?> c,String s)throws Exception{Field f=c.getDeclaredField(s);f.setAccessible(true);return f;}
 static long count(boolean[][][][] v){if(v==null)return 0;long n=0;for(boolean[][][] a:v)for(boolean[][] b:a)for(boolean[] row:b)for(boolean p:row)if(p)n++;return n;}
 public static void main(String[] a)throws Exception {
  Field active=f(GpuRenderer.class,"field1595");boolean old=active.getBoolean(null);
  Field vw=f(Client.class,"viewportWidth"),vh=f(Client.class,"viewportHeight");int w=vw.getInt(null),h=vh.getInt(null);
  Field vis=f(Scene.class,"tileVisibility");
  try{
   Scene.activeDrawDistance=25;vw.setInt(null,960);vh.setInt(null,540);
   active.setBoolean(null,true);
   Client client=new Client();
   long before=count((boolean[][][][])vis.get(null));
   client.alignViewport();
   long after=count((boolean[][][][])vis.get(null));
   System.out.println("R307_GPU_ALIGN_VIEWPORT before="+before+" after="+after);
   if(after==0)throw new AssertionError("R307_GPU_ALIGN_SKIPPED_SCENE_VISIBILITY");
  }finally{active.setBoolean(null,old);vw.setInt(null,w);vh.setInt(null,h);}
 }
}
