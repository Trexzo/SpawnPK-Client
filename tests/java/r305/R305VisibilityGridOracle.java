import rs.Scene;
import rs.model.Model;
import rs.graphics.Rasterizer3D;
import java.lang.reflect.Field;

public final class R305VisibilityGridOracle {
 static int checks, mismatches, yawMismatches, edgeMismatches, edgeExpectedVisible;
 static Field visibility;
 static boolean project(int height,int north,int east,int pitch,int yaw) {
  int vs=Model.field231[pitch],vc=Model.field232[pitch], ys=Model.field231[yaw],yc=Model.field232[yaw];
  int screenX=north*ys+east*yc>>16;
  int depthProjection=north*yc-east*ys>>16;
  int depth=height*vs+depthProjection*vc>>16;
  int screenY=height*vc-depthProjection*vs>>16;
  if(depth<50||depth>3500)return false;
  int col=400+(screenX<<9)/depth;
  int row=300+(screenY<<9)/depth;
  return col>=0&&col<=800&&row>=0&&row<=600;
 }
 static boolean unfiltered(int pitch,int yaw,int x,int y) {
  int p=128+pitch*32;
  int height=(600+(p+15)*3)*Rasterizer3D.field2869[p+15]>>16;
  for(int z=-500;z<=500;z+=128){
   if(project(height+z,y*128,x*128,p,yaw*64))return true;
  }
  return false;
 }
 static boolean expected(int pitch,int yaw,int x,int y) {
  for(int dx=-1;dx<=1;dx++)for(int dy=-1;dy<=1;dy++){
   for(int pp=pitch;pp<=pitch+1;pp++) {
    if(unfiltered(pp,yaw,x+dx,y+dy) || unfiltered(pp,(yaw+1)&31,x+dx,y+dy)) return true;
   }
  }
  return false;
 }
 public static void main(String[] args)throws Exception {
  visibility=Scene.class.getDeclaredField("tileVisibility");visibility.setAccessible(true);
  for(int radius:new int[]{5,10,25,30,50}){
   Scene.activeDrawDistance=radius;
   Scene.setViewport(500,500,800,600);
   boolean[][][][] v=(boolean[][][][])visibility.get(null);
   int oldWrong=0, expectedEdge=0, badYaw=0;
   for(int pitch:new int[]{0,3,7})for(int yaw:new int[]{30,31}){
    for(int x=-radius;x<=radius;x++)for(int y=-radius;y<=radius;y++){
     boolean want=expected(pitch,yaw,x,y);
     boolean have=v[pitch][yaw][x+radius][y+radius];
     checks++;
     if(want!=have){mismatches++;oldWrong++;if(x==radius||y==radius){edgeMismatches++;expectedEdge++;} else {yawMismatches++;badYaw++;}}
    }
   }
   System.out.printf("RADIUS=%d samples=%d mismatches=%d edge=%d inner_yaw=%d%n",radius,3*2*(2*radius+1)*(2*radius+1),oldWrong,expectedEdge,badYaw);
  }
  System.out.printf("R305_VISIBILITY_REFERENCE_ORACLE total=%d mismatches=%d border=%d interiorYaw=%d%n",checks,mismatches,edgeMismatches,yawMismatches);
  if(mismatches>0)throw new AssertionError("R305_RENDER_VISIBILITY_GRID_MISMATCH total="+mismatches+" border="+edgeMismatches+" yaw="+yawMismatches);
 }
}
