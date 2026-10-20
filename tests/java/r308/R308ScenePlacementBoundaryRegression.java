import rs.Scene;
import rs.Tile;
import rs.model.Class11;
import java.lang.reflect.Method;

/** Actual compiled Scene: all public packet/cache-backed placement writers ignore off-map coordinates. */
public final class R308ScenePlacementBoundaryRegression {
 static int checks=0;
 static void require(boolean yes,String why){if(!yes)throw new AssertionError(why);checks++;}
 static void place(Scene s,int which,int plane,int x,int y,Class11 model){
  switch(which){
   case 0: s.method1909(plane,x,y,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0);break;
   case 1: s.method1890(plane,0,y,model,(byte)0,123,x,0);break;
   case 2: s.method2219(0,model,123,y,(byte)0,x,model,0,0,plane,0);break;
   case 3: s.method3074(123,y,0,plane,0,0,model,x,(byte)0,0,0,0);break;
   case 4: s.addGroundDecoration(plane,0,y,model,(byte)0,123,x);break;
   case 5: s.method1657(x,0,model,0,model,model,plane,y);break;
   case 6: s.method1680(0,model,123,y,(byte)0,x,model,0,0,plane);break;
   case 7: s.method3442(123,y,0,plane,0,0,model,x,(byte)0,0,0);break;
   default: throw new AssertionError("invalid method index");
  }
 }
 static void safe(Scene s,int which,int plane,int x,int y,Class11 model){
  try {place(s,which,plane,x,y,model); checks++;}
  catch(Throwable e){throw new AssertionError("R308_SCENE_PLACEMENT_BOUNDARY_CRASH method="+which+" plane="+plane+" x="+x+" y="+y,e);}
 }
 static boolean stored(Tile t,int index){
  switch(index){
   case 0:return t.field5051!=null;
   case 1:case 4:return t.field5055!=null;
   case 2:case 6:return t.field5053!=null;
   case 3:case 7:return t.field5054!=null;
   case 5:return t.field5056!=null;
   default:throw new AssertionError(index);
  }
 }
 public static void main(String[] args){
  Class11 model;
  try { java.lang.reflect.Constructor<Class11> ctor=Class11.class.getDeclaredConstructor(); ctor.setAccessible(true); model=ctor.newInstance(); }
  catch (ReflectiveOperationException e) { throw new RuntimeException(e); }
  int[] outside={-1,104,Integer.MIN_VALUE,Integer.MAX_VALUE};
  for(int method=0;method<8;method++){
   for(int axis=0;axis<3;axis++)for(int bad:outside){
    Scene s=new Scene(new int[4][105][105]);
    int p=1,x=50,y=50;
    if(axis==0)p=bad;else if(axis==1)x=bad;else y=bad;
    safe(s,method,p,x,y,model);
    require(s.tiles[1][50][50]==null,"R308_INVALID_PLACEMENT_MUTATED_SCENE method="+method+" axis="+axis+" value="+bad);
   }
   for(int[] valid:new int[][]{{0,0,0},{1,50,50},{3,103,103},{2,0,103}}){
    Scene s=new Scene(new int[4][105][105]);
    safe(s,method,valid[0],valid[1],valid[2],model);
    Tile t=s.tiles[valid[0]][valid[1]][valid[2]];
    require(t!=null && stored(t,method),"R308_VALID_SCENE_OBJECT_NOT_STORED method="+method);
   }
  }
  System.out.println("R308_SCENE_PLACEMENT_BOUNDS_PASS checks="+checks+" methods=8");
 }
}
