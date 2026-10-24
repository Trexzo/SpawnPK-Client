import rs.Client;
import rs.io.Packet;
import rs.model.Player;
import java.io.ByteArrayOutputStream;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

/** Offline direct exercise of original client opcode-81 teleport+appearance logic. */
public final class R268TeleportAppearanceRegression {
    private static int checks;
    private static void ck(boolean ok,String msg){if(!ok)throw new AssertionError(msg);checks++;}
    private static void word(ByteArrayOutputStream b,int x){b.write((x>>>8)&255);b.write(x&255);}
    private static byte[] body(String name){
        ByteArrayOutputStream b=new ByteArrayOutputStream();
        for(int i=0;i<5;i++)b.write(0);
        word(b,0);
        for(int i=0;i<12;i++){
            int equipment=i<7?256+new int[]{0,10,18,26,33,36,42}[i]:0;
            if(equipment==0)b.write(0);
            else word(b,equipment);
        }
        b.write(0);
        for(int i=0;i<5;i++)b.write(0);
        for(int i=0;i<7;i++)word(b,65535);
        b.write(0);
        byte[] str=(name+"\n").getBytes(StandardCharsets.ISO_8859_1);
        b.write(str,0,str.length);b.write(3);word(b,0);b.write(0);b.write(0);
        return b.toByteArray();
    }
    private static byte[] movement(int localX,int localY,boolean appearance){
        ck(localX>=0&&localX<104&&localY>=0&&localY<104,"local coords outside scene");
        int[] value={1,3,0,0,appearance?1:0,localY,localX,0,2047};
        int[] width={1,2,2,1,1,7,7,8,11};
        int count=0,packed=0;
        ByteArrayOutputStream b=new ByteArrayOutputStream();
        for(int i=0;i<value.length;i++){
            ck(value[i]>=0&&value[i]<(1<<width[i]),"invalid bit field "+i);
            for(int j=width[i]-1;j>=0;j--){
                packed=(packed<<1)|((value[i]>>>j)&1);count++;
                if(count==8){b.write(packed);packed=count=0;}
            }
        }
        ck(count==0&&b.size()==5,"expected five-byte teleport header");
        return b.toByteArray();
    }
    private static byte[] wire(int x,int y,String name) {
        byte[] a=body(name),m=movement(x,y,true);
        ck(a.length==61 || a.length==62,"unexpected appearance length " + a.length);
        ByteArrayOutputStream b=new ByteArrayOutputStream();
        b.write(m,0,m.length);b.write(0x10);b.write((-a.length)&255);b.write(a,0,a.length);
        ck(b.size()==7+a.length,"teleport+appearance packet length mismatch");
        return b.toByteArray();
    }
    public static void main(String[] args) throws Exception {
        byte[] initial=wire(48,48,"LocalKit");
        Packet probe=new Packet(initial);probe.method3628();
        ck(probe.getBits(1)==1,"update bit");
        ck(probe.getBits(2)==3,"teleport movement type");
        ck(probe.getBits(2)==0,"plane 0");
        ck(probe.getBits(1)==0,"teleport flag");
        ck(probe.getBits(1)==1,"appearance follows");
        ck(probe.getBits(7)==48,"Y local coordinate");
        ck(probe.getBits(7)==48,"X local coordinate");
        ck(probe.getBits(8)==0,"retained players");
        ck(probe.getBits(11)==2047,"new players sentinel");
        probe.method480();ck(probe.caret==5,"byte boundary");
        ck(probe.readUnsignedByte()==0x10,"appearance mask");
        ck(probe.method3095()==61,"negated appearance length");
        Client client=new Client();Player player=new Player();
        Client.localPlayer=Client.players[2047]=player;
        Method handler=Client.class.getDeclaredMethod("method1850",int.class,Packet.class);
        handler.setAccessible(true);
        handler.invoke(client,initial.length,new Packet(initial));
        ck(Client.localPlayer==player,"player replaced during movement");
        ck(player.pathX[0]==48&&player.pathY[0]==48,"initial position not populated");
        ck(player.x==48*128+player.scale*64,"world X");
        ck(player.y==48*128+player.scale*64,"world Y");
        ck(player.hasAppearance,"appearance not marked");
        ck("LocalKit".equals(player.username),"username");
        ck(Client.planeLevel==0,"plane mismatch");
        byte[] keepalive={0,0x7f,(byte)0xf0};
        handler.invoke(client,keepalive.length,new Packet(keepalive));
        ck(player.pathX[0]==48&&player.pathY[0]==48&&player.hasAppearance,"unmasked tick");
        byte[] further=movement(50,49,false);
        handler.invoke(client,further.length,new Packet(further));
        ck(player.pathX[0]==50&&player.pathY[0]==49,"second teleport");
        ck(player.hasAppearance,"second teleport lost appearance");
        ck("LocalKit".equals(player.username),"second teleport lost identity");
        byte[] update=wire(50,49,"LocalKit2");
        handler.invoke(client,update.length,new Packet(update));
        ck("LocalKit2".equals(player.username),"repeat appearance");
        ck(player.pathX[0]==50&&player.pathY[0]==49,"repeat movement");
        byte[] truncated=Arrays.copyOf(update,8);
        boolean rejected=false;
        try{handler.invoke(client,truncated.length,new Packet(truncated));}
        catch(InvocationTargetException e){rejected=e.getCause() instanceof RuntimeException||e.getCause() instanceof Error;}
        ck(rejected,"truncated appearance not rejected");
        System.out.println("R268_TELEPORT_APPEARANCE_CLIENT_DISPATCH_PASS checks="+checks+
            " start_tile=48,48 final_tile="+player.pathX[0]+","+player.pathY[0]+
            " initial_bytes="+initial.length);
    }
}
