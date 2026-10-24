import rs.io.Packet;
import rs.model.Player;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
/** Complete source-backed appearance parser smoke; equipment data intentionally absent. */
public final class R265CompleteAppearanceFrameRegression {
  private static int checks;
  private static void check(boolean ok,String why){if(!ok)throw new AssertionError(why);checks++;}
  private static void word(ByteArrayOutputStream b,int value){b.write((value>>>8)&255);b.write(value&255);}
  private static byte[] validBody(){
    ByteArrayOutputStream b=new ByteArrayOutputStream();
    for(int i=0;i<5;i++)b.write(0);
    word(b,0);
    for(int i=0;i<12;i++)b.write(0);
    b.write(0);
    for(int i=0;i<5;i++)b.write(0);
    for(int i=0;i<7;i++)word(b,65535);
    b.write(0);
    byte[] name="LocalTest\n".getBytes(StandardCharsets.ISO_8859_1);b.write(name,0,name.length);
    b.write(3);word(b,0);b.write(0);b.write(0);
    return b.toByteArray();
  }
  public static void main(String[] args) {
    byte[] body=validBody();check(body.length==55,"unexpected appearance body length");
    ByteArrayOutputStream encoded=new ByteArrayOutputStream();
    for(int n:new int[]{0x80,0x1f,0xfc,0x10,(-body.length)&255})encoded.write(n);
    encoded.write(body,0,body.length);
    Packet packet=new Packet(encoded.toByteArray()); packet.method3628();
    check(packet.getBits(1)==1,"self update bit");check(packet.getBits(2)==0,"self update type");
    check(packet.getBits(8)==0,"retained peer count");check(packet.getBits(11)==2047,"list sentinel");
    packet.method480();check(packet.caret==3,"bit/byte boundary");
    check(packet.readUnsignedByte()==0x10,"self appearance mask");
    int n=packet.method3095();check(n==body.length,"negated-byte appearance length");
    byte[] reconstructed=new byte[n];
    for(int i=0;i<n;i++)reconstructed[i]=(byte)packet.readUnsignedByte();
    check(packet.caret==encoded.size(),"packet not fully consumed");
    Player local=new Player();check(!local.hasAppearance,"fresh player has appearance");
    Packet appearance=new Packet(reconstructed);local.method3589(appearance);
    check(local.hasAppearance,"appearance flag not set");
    check("LocalTest".equals(local.username),"username mismatch");
    check(appearance.caret==n,"appearance decoder did not consume body");
    System.out.println("R265_COMPLETE_PLAYER_81_APPEARANCE_PARSE_PASS checks="+checks+" bytes="+encoded.size());
  }
}
