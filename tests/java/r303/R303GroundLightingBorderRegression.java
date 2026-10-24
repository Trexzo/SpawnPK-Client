import java.lang.reflect.*;
import rs.Scene;
import rs.model.Model;

/** Genuine private method1018 border lookup; no model mock or fake client classes. */
public final class R303GroundLightingBorderRegression {
    static int checks=0;
    static void query(Method m, Scene scene,int x,int plane,int y) throws Exception {
        try { m.invoke(scene,x,plane,(Model)null,y); checks++; }
        catch (InvocationTargetException e) { throw new AssertionError("R303_GROUND_LIGHTING_TILE_OOB plane="+plane+" x="+x+" y="+y+" cause="+e.getCause(),e.getCause()); }
    }
    public static void main(String[] args) throws Exception {
        Scene scene=new Scene(new int[4][105][105]);
        Method m=Scene.class.getDeclaredMethod("method1018",int.class,int.class,Model.class,int.class);
        m.setAccessible(true);
        for(int p=0;p<4;p++) {
            for(int n=0;n<104;n++) {
                query(m,scene,0,p,n);
                query(m,scene,103,p,n);
                query(m,scene,n,p,0);
                query(m,scene,n,p,103);
            }
            for(int[] xy:new int[][]{{1,1},{50,50},{102,102},{0,103},{103,0}})
                query(m,scene,xy[0],p,xy[1]);
            for(int[] xy:new int[][]{{-1,50},{104,50},{50,-1},{50,104},{Integer.MIN_VALUE,50},{Integer.MAX_VALUE,50}})
                query(m,scene,xy[0],p,xy[1]);
        }
        System.out.println("R303_GROUND_LIGHTING_BORDER_PASS checks="+checks);
    }
}
