import java.lang.reflect.*;
import java.nio.file.*;
import rs.Client;
import rs.Scene;
import rs.NodeDeque;
import rs.io.Packet;
import rs.io.Archive;
import rs.definitions.ObjectDefinition;
import rs.model.Player;
import rs.eventbus.EventBus;
public final class R273ObjectSpawnDecodeRegression {
 static int checks;
 static void ck(boolean b,String w){if(!b)throw new AssertionError(w);checks++;}
 public static void main(String[] args)throws Exception{
  ck(args.length==1,"real owner config input required");
  byte[] rawconfig=Files.readAllBytes(Paths.get(args[0]));
  ck(rawconfig.length==1432547,"unexpected config size");
  ObjectDefinition.load(new Archive(rawconfig,"config"));
  ObjectDefinition d=ObjectDefinition.get(104);
  ck("Open chest".equals(d.name)&&"Search".equals(d.actions[0]),"real object 104 invalid");
  Client c=new Client();c.eventBus=new EventBus();Client.planeLevel=0;
  c.field761=new Scene(new int[4][105][105]);
  Field fx=Client.class.getDeclaredField("field996");fx.setAccessible(true);fx.setInt(c,48);
  Field fy=Client.class.getDeclaredField("field997");fy.setAccessible(true);fy.setInt(c,48);
  Field pending=Client.class.getDeclaredField("field923");pending.setAccessible(true);NodeDeque queue=new NodeDeque();pending.set(c,queue);
  Player p=new Player();p.method3089(48,48,true);Client.localPlayer=Client.players[2047]=p;
  // Actual incoming Client.method2310 subpacket151 shape: packed offset low+128, id LE, shape+rotation neg128.
  byte[] frame={(byte)0xa1,(byte)104,(byte)0,(byte)88};
  Packet packet=new Packet(frame);
  Method dec=Client.class.getDeclaredMethod("method2310",Packet.class,int.class);dec.setAccessible(true);
  dec.invoke(c,packet,151);
  ck(packet.caret==4,"source opcode151 not fully consumed");
  Object node=queue.peekFirst();ck(node!=null && node.getClass().getName().equals("rs.Class7"),"source didn't queue a world-object update");
  Class<?> type=node.getClass();
  int[][] fields={{0,104},{1,50},{2,49},{3,0}};
  String[] names={"field5215","field5221","field5222","field5219"};
  for(int i=0;i<4;i++){Field f=type.getDeclaredField(names[i]);f.setAccessible(true);ck(f.getInt(node)==fields[i][1],"queued object field mismatch "+names[i]);}
  Field shape=type.getDeclaredField("field5217");shape.setAccessible(true);ck(shape.getInt(node)==10,"model shape 10 changed");
  ck(queue.next()==null,"unexpected second queued object");
  ck(p.pathX[0]==48&&p.pathY[0]==48,"server sent object spawn not player movement");
  System.out.println("R273_INBOUND_REAL_OBJECT_SPAWN_PASS checks="+checks+" object=104 tile=50,49 shape=10 queued=true");
 }
}
