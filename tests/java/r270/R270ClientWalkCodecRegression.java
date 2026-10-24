import java.lang.reflect.*;
import java.util.*;
import java.io.ByteArrayOutputStream;
import rs.Client;
import rs.CollisionMap;
import rs.io.Packet;
import rs.model.Player;
import rs.network.Class257;

/** Check the ACTUAL compiled RS pathfinder and outgoing opcode-164 byte layout. */
public final class R270ClientWalkCodecRegression {
 private static int checks;
 private static void ck(boolean ok,String why){if(!ok)throw new AssertionError(why);checks++;}
 private static int u8(byte b){return b&255;}
 private static byte[] ack(int x,int y){
   int[] value={1,3,0,0,0,y,x,0,2047};int[] width={1,2,2,1,1,7,7,8,11};
   ByteArrayOutputStream b=new ByteArrayOutputStream();int accum=0,n=0;
   for(int i=0;i<value.length;i++)for(int j=width[i]-1;j>=0;j--){accum=(accum<<1)|((value[i]>>>j)&1);if(++n==8){b.write(accum);accum=n=0;}}
   if(n!=0||b.size()!=5)throw new AssertionError("invalid acknowledgement frame");
   return b.toByteArray();
 }
 private static boolean walk(Client client,int targetX,int targetY,boolean fallback)throws Exception{
   Method method=Client.class.getDeclaredMethod("method3573",int.class,int.class,int.class,int.class,int.class,int.class,int.class,int.class,int.class,boolean.class,int.class);
   method.setAccessible(true);
   return (boolean)method.invoke(client,0,0,0,0,Client.localPlayer.pathY[0],0,0,targetY,Client.localPlayer.pathX[0],fallback,targetX);
 }
 public static void main(String[] args)throws Exception {
   Client client=new Client();
   Client.baseX=3152;Client.baseY=3152;Client.planeLevel=0;
   client.field960=new CollisionMap[4];
   for(int i=0;i<4;i++){client.field960[i]=new CollisionMap(); for(int x=1;x<103;x++)for(int y=1;y<103;y++)client.field960[i].clipData[x][y]=0;}
   Player local=new Player();
   local.method3089(48,48,true);
   Client.localPlayer=Client.players[2047]=local;
   ck(local.pathX[0]==48&&local.pathY[0]==48,"start tile mismatch");
   int[] seed={13,22,37,41};
   Client.outgoingPacket=Packet.newInstance();
   Client.outgoingPacket.isaacRandom=new Class257(seed.clone());
   ck(Client.outgoingPacket.caret==0,"nonempty outbound before route");
   boolean reached=walk(client,50,49,false);
   ck(reached,"route finder refused nearby tile");
   byte[] payload=Arrays.copyOf(Client.outgoingPacket.payload,Client.outgoingPacket.caret);
   ck(payload.length>=7,"outbound packet too short");
   Class257 cipher=new Class257(seed.clone());
   ck((u8(payload[0])-cipher.method0()&255)==164,"actual outgoing opcode is not 164");
   int declared=u8(payload[1]);
   ck(declared==payload.length-2,"byte-count framing does not match payload length");
   ck(declared>=5 && declared%2==1,"unexpected walk packet length");
   int chunks=(declared-3)/2;
   ck(chunks>=1&&chunks<=25,"route waypoint count invalid");
   int baseX=((u8(payload[2])-128)&255)|(u8(payload[3])<<8);
   ck(baseX>=3152&&baseX<3256,"world X beyond region");
   int yoffset=4+(chunks-1)*2;
   ck(yoffset+3==payload.length,"coordinate framing offset invalid");
   int baseY=u8(payload[yoffset])|(u8(payload[yoffset+1])<<8);
   ck(baseY>=3152&&baseY<3256,"world Y beyond region");
   int running=(256-u8(payload[yoffset+2]))&255;
   ck(running==0,"run flag changed without keypress");
   System.out.println("R270_OBSERVED_ROUTE world_first_waypoint="+baseX+","+baseY+" waypoint_count="+chunks+" bytes="+java.util.Arrays.toString(payload));
   ck(Math.abs(baseX-3200)<=3&&Math.abs(baseY-3200)<=3,"first waypoint not near start/destination");
   int endX=baseX,endY=baseY;
   for(int j=0;j<chunks-1;j++){
     endX+=(byte)payload[4+2*j];endY+=(byte)payload[5+2*j];
   }
   ck(endX==3202 && endY==3201,"outbound waypoint destination drift");
   ck(local.pathX[0]==48 && local.pathY[0]==48,"outbound walk cannot silently be server acknowledgement");
   byte[] serverAck=ack(50,49);
   java.lang.reflect.Method sync=Client.class.getDeclaredMethod("method1850",int.class,Packet.class);
   sync.setAccessible(true);
   sync.invoke(client,serverAck.length,new Packet(serverAck));
   ck(local.pathX[0]==50&&local.pathY[0]==49,"real player sync rejected authoritative server acknowledgement");
   ck(local.x==50*128+local.scale*64 && local.y==49*128+local.scale*64,"acknowledged world coordinates wrong");
   ck(Client.localPlayer==local,"server acknowledgement replaced local player");
   // Second movement pathway is the action-walk opcode 98 (n=2).
   Client.outgoingPacket=Packet.newInstance();
   Client.outgoingPacket.isaacRandom=new Class257(seed.clone());
   Method mode=Client.class.getDeclaredMethod("method3573",int.class,int.class,int.class,int.class,int.class,int.class,int.class,int.class,int.class,boolean.class,int.class);
   mode.setAccessible(true);
   ck((boolean)mode.invoke(client,2,0,0,0,local.pathY[0],0,0,49,local.pathX[0],false,51),"action walking refused adjacent tile");
   byte[] action=Arrays.copyOf(Client.outgoingPacket.payload,Client.outgoingPacket.caret);
   ck((u8(action[0])-(new Class257(seed.clone())).method0()&255)==98,"action walking did not use opcode 98");
   ck(u8(action[1])==action.length-2,"action movement length inconsistent");
   // Restore first movement to test blocked paths without disturbing original evidence.
   Client.outgoingPacket=Packet.newInstance();
   Client.outgoingPacket.isaacRandom=new Class257(seed.clone());
   // Check no outgoing source packet mutation following a failed route.
   int caret=Client.outgoingPacket.caret;
   for(int x=1;x<103;x++)for(int y=1;y<103;y++)client.field960[0].clipData[x][y]=0xFFFFFF;
   boolean blocked=walk(client,54,54,false);
   ck(!blocked,"blocked route was accepted without fallback");
   ck(Client.outgoingPacket.caret==caret,"blocked path produced an outbound packet");
   System.out.println("R270_CLIENT_REAL_WALK_PACKET_PASS checks="+checks+" opcode=164 bytes="+payload.length+" world_first_waypoint="+baseX+","+baseY+" endpoint="+endX+","+endY+" waypoints="+chunks+" server_ack_tile="+local.pathX[0]+","+local.pathY[0]+" alternate_op=98 blocked_refused=true");
 }
}
