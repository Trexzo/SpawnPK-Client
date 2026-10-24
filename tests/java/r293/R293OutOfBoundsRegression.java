import java.lang.reflect.*;
import rs.*;
import rs.io.Packet;
public class R293OutOfBoundsRegression {
 static int checks=0;
 static void ck(boolean ok,String m){if(!ok)throw new AssertionError(m);checks++;}
 public static void main(String[]args) throws Exception {
  Client client=new Client();client.eventBus=new rs.eventbus.EventBus();Client.planeLevel=0;
  client.field761=new Scene(new int[4][105][105]);
  Method handle=Client.class.getDeclaredMethod("handleObjectClick",int.class,int.class,int.class,int.class);
  handle.setAccessible(true);
  int[] bad={-1,104,105,Integer.MIN_VALUE,Integer.MAX_VALUE};
  for(int x:bad)for(int y:new int[]{50,0,103}) {
    try{
      Object ok=handle.invoke(client,104<<14,x,y,104);
      ck(Boolean.FALSE.equals(ok),"out-of-range X should be refused x="+x+", y="+y);
    }catch(InvocationTargetException ex){throw new AssertionError("R293_OFF_SCENE_X_CRASH x="+x+" y="+y+" cause="+ex.getCause(),ex);}
  }
  for(int y:bad)for(int x:new int[]{50,0,103}){
    try{
      Object ok=handle.invoke(client,104<<14,x,y,104);
      ck(Boolean.FALSE.equals(ok),"out-of-range Y should be refused y="+y+", x="+x);
    }catch(InvocationTargetException ex){throw new AssertionError("R293_OFF_SCENE_Y_CRASH y="+y+" x="+x+" cause="+ex.getCause(),ex);}
  }
  for(int x:new int[]{0,50,103})for(int y:new int[]{0,50,103}){
      Object ok=handle.invoke(client,104<<14,x,y,104);
      ck(Boolean.FALSE.equals(ok),"empty in-bounds scene must not be interactable");
  }
  for(int plane : new int[]{-1,4,Integer.MIN_VALUE,Integer.MAX_VALUE}) {
    Client.planeLevel=plane;
    try{
      Object allowed=handle.invoke(client,104<<14,50,50,104);
      ck(Boolean.FALSE.equals(allowed),"invalid plane accepted "+plane);
    }catch(InvocationTargetException ex){throw new AssertionError("R293_OFF_SCENE_PLANE_CRASH "+plane+" cause="+ex.getCause(),ex);}
  }
  Client.planeLevel=0;
  Method menu=Client.class.getDeclaredMethod("handleMenuAction",int.class,int.class,int.class,int.class,int.class,String.class);
  menu.setAccessible(true);
  for(int action : new int[]{1062,900,113,872,502,62,956}) {
    for(int[] tile : new int[][]{{-1,50},{104,50},{50,-1},{50,104}}) {
      Client.outgoingPacket=Packet.newInstance();
      Client.outgoingPacket.isaacRandom=new rs.network.Class257(new int[]{13,22,37,41});
      try{
        menu.invoke(client,action,104<<14,tile[0],tile[1],104,"out of bounds");
        ck(Client.outgoingPacket.caret==0,"invalid menu action emitted packet action="+action+" x="+tile[0]+" y="+tile[1]);
      }catch(InvocationTargetException ex){throw new AssertionError("R293_OFF_SCENE_MENU_CRASH action="+action+" x="+tile[0]+" y="+tile[1]+" cause="+ex.getCause(),ex);}
    }
  }
  System.out.println("R293_OFF_SCENE_GUARD_PASS checks="+checks);
 }
}
