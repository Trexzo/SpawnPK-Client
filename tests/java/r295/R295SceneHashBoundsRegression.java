import rs.*;
public class R295SceneHashBoundsRegression {
  static int checks=0;
  static void verify(boolean condition,String message){if(!condition)throw new AssertionError(message);checks++;}
  static void expectAbsent(Scene scene,int plane,int x,int y){
    try {
      int result=scene.getHashAtTile(plane,x,y,114<<14);
      verify(result==-1,"R295_SCENE_INVALID_QUERY_NOT_ABSENT plane="+plane+" x="+x+" y="+y+" result="+result);
    }catch(ArrayIndexOutOfBoundsException e){throw new AssertionError("R295_SCENE_HASH_DIRECT_OOB_CRASH plane="+plane+" x="+x+" y="+y,e);}
  }
  public static void main(String[] args){
    Scene scene=new Scene(new int[4][105][105]);
    int[] extremes={-1,104,105,Integer.MIN_VALUE,Integer.MAX_VALUE};
    for(int x:extremes)for(int y:new int[]{0,50,103})expectAbsent(scene,0,x,y);
    for(int y:extremes)for(int x:new int[]{0,50,103})expectAbsent(scene,0,x,y);
    for(int p:new int[]{-1,4,5,Integer.MIN_VALUE,Integer.MAX_VALUE})
      for(int[] point:new int[][]{{0,0},{50,50},{103,103}})expectAbsent(scene,p,point[0],point[1]);
    for(int plane=0;plane<4;plane++)for(int[] point:new int[][]{{0,0},{50,50},{103,103}})
      expectAbsent(scene,plane,point[0],point[1]);
    for(int plane=0;plane<4;plane++)for(int[] point:new int[][]{{0,103},{103,0},{52,0}})
      expectAbsent(scene,plane,point[0],point[1]);
    System.out.println("R295_SCENE_HASH_BOUNDARY_PASS checks="+checks);
  }
}
