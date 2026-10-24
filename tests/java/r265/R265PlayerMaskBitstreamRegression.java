import rs.io.Packet;
/** Checks reconstructed v309 player-sync bit/byte boundaries; not an appearance-body fixture. */
public final class R265PlayerMaskBitstreamRegression {
  private static int checks;
  private static void check(boolean ok,String msg){if(!ok)throw new AssertionError(msg);checks++;}
  public static void main(String[] args) {
    // self update=1, type=0, other-player-count=0, added-player sentinel=2047.
    // 0x10 appearance mask, negated appearance length=2, opaque two-byte stub.
    byte[] payload={(byte)0x80,(byte)0x1f,(byte)0xfc,(byte)0x10,(byte)0xfe,(byte)0x11,(byte)0x22};
    Packet p=new Packet(payload); p.method3628();
    check(p.getBits(1)==1,"local player update bit");
    check(p.getBits(2)==0,"local player type0 mask pending");
    check(p.getBits(8)==0,"other retained players count");
    check(p.getBits(11)==2047,"end of added-player list");
    p.method480();check(p.caret==3,"byte alignment after 22 bits");
    check(p.readUnsignedByte()==0x10,"appearance update bit");
    check(p.method3095()==2,"negative byte appearance length transform");
    check(p.readUnsignedByte()==0x11,"first opaque appearance byte");
    check(p.readUnsignedByte()==0x22,"second opaque appearance byte");
    check(p.caret==payload.length,"full test frame consumed");
    System.out.println("R265_PLAYER_APPEARANCE_MASK_BITSTREAM_PASS checks="+checks);
  }
}
