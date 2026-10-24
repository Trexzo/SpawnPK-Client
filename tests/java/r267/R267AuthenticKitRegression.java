import java.io.*;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.zip.GZIPInputStream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import rs.Client;
import rs.ModelHeader;
import rs.definitions.IdentityKit;
import rs.definitions.SequenceDefinition;
import rs.io.Archive;
import rs.io.Packet;
import rs.model.Model;
import rs.model.Player;

/**
 * R267: use actual bundled .spawnpk cache sectors, config and IdentityKit model bytes.
 * No socket, synthetic models, production source edits, or files written to user's game.
 * The enclosing original assets/private JAR have to be checksum-verified by the runner.
 */
public final class R267AuthenticKitRegression {
    private static int checks;
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
        checks++;
    }
    private static int u24(byte[] b, int offset) {
        return (b[offset] & 255) << 16 | (b[offset+1] & 255) << 8 | (b[offset+2] & 255);
    }
    private static int u16(byte[] b, int offset) {
        return (b[offset] & 255) << 8 | (b[offset+1] & 255);
    }
    /** Match rs.cache.IndexStore: 6-byte index records and 520-byte sectors. */
    private static byte[] indexFile(byte[] dat, byte[] idx, int indexNumber, int fileId) throws IOException {
        long pos = (long)fileId * 6;
        if (pos+6 > idx.length || fileId < 0) throw new IOException("missing index record " + fileId);
        int size=u24(idx,(int)pos), sector=u24(idx,(int)pos+3);
        if (size<=0 || size>20_000_000) throw new IOException("invalid cache entry size " + size);
        ByteArrayOutputStream out=new ByteArrayOutputStream(size);
        Set<Integer> visited=new HashSet<>();
        int sequence=0;
        while (out.size()<size) {
            if (sector<=0 || !visited.add(sector)) throw new IOException("missing/cyclic sector");
            long offset=(long)sector * 520;
            int take=Math.min(512,size-out.size());
            if (offset+8+take>dat.length) throw new IOException("sector exceeds cache data");
            int at=(int)offset;
            int observedId=u16(dat,at), observedChunk=u16(dat,at+2);
            int next=u24(dat,at+4), observedIndex=dat[at+7]&255;
            if (observedId!=fileId || observedChunk!=sequence || observedIndex!=indexNumber+1)
                throw new IOException("sector mismatch file="+fileId+" sequence="+sequence);
            out.write(dat,at+8,take);
            sector=next;
            sequence++;
        }
        check(out.size()==size,"cache extracted length mismatch");
        return out.toByteArray();
    }
    private static byte[] zipFile(ZipFile z, String name, int limit) throws IOException {
        ZipEntry entry=z.getEntry(name);
        if (entry==null || entry.getSize()<0 || entry.getSize()>limit) throw new IOException("bad asset entry: "+name);
        try(InputStream stream=z.getInputStream(entry)) {
            byte[] bytes=stream.readAllBytes();
            if(bytes.length!=entry.getSize())throw new IOException("asset size mismatch: "+name);
            return bytes;
        }
    }
    private static byte[] gunzipModel(byte[] compressed) throws IOException {
        try(GZIPInputStream in=new GZIPInputStream(new ByteArrayInputStream(compressed))) {
            ByteArrayOutputStream out=new ByteArrayOutputStream();
            byte[] chunk=new byte[4096]; int n;
            while((n=in.read(chunk))!=-1) {
                if(out.size()+n>5_000_000)throw new IOException("oversized model payload");
                out.write(chunk,0,n);
            }
            return out.toByteArray();
        }
    }
    private static void word(ByteArrayOutputStream b,int value) { b.write(value>>>8);b.write(value&255); }
    private static byte[] appearance(int[] equip, String username) {
        ByteArrayOutputStream b=new ByteArrayOutputStream();
        for(int i=0;i<5;i++)b.write(0);
        word(b,0);
        for(int i=0;i<12;i++) {
            int id=equip[i];
            if(id==0)b.write(0);
            else {b.write(id>>>8);b.write(id&255);}
        }
        b.write(0);
        for(int i=0;i<5;i++)b.write(0);
        for(int i=0;i<7;i++)word(b,65535);
        b.write(0);
        byte[] name=(username+"\n").getBytes(StandardCharsets.ISO_8859_1);
        b.write(name,0,name.length);
        b.write(3);word(b,0);b.write(0);b.write(0);
        return b.toByteArray();
    }
    private static byte[] maskedFrame(byte[] body) {
        check(body.length < 256, "single-byte appearance body length exceeded");
        ByteArrayOutputStream b=new ByteArrayOutputStream();
        for(int x:new int[]{0x80,0x1f,0xfc,0x10,(-body.length)&255})b.write(x);
        b.write(body,0,body.length);
        return b.toByteArray();
    }
    public static void main(String[] args) throws Exception {
        check(args.length==1,"expected private original .spawnpk ZIP argument");
        check(!Boolean.getBoolean("java.awt.headless"),"X display needed for legacy Client Applet");
        byte[] data,idx0,idx1;
        try(ZipFile assets=new ZipFile(Paths.get(args[0]).toFile())) {
            data=zipFile(assets,".spawnpk/main_file_cache.dat",100_000_000);
            idx0=zipFile(assets,".spawnpk/main_file_cache.idx0",500_000);
            idx1=zipFile(assets,".spawnpk/main_file_cache.idx1",5_000_000);
        }
        check(data.length==81_438_266,"unexpected source cache DAT size");
        byte[] config=indexFile(data,idx0,0,2);
        check(config.length==1_432_547,"unexpected config archive length");
        IdentityKit.load(new Archive(config,"config"));
        check(IdentityKit.count==84,"unexpected idk.dat IdentityKit count");

        Model.field139=new ModelHeader[80_000];
        Model.field140=new boolean[100_000];
        int[] expectedKitIds={0,10,18,26,33,36,42};
        int[] expectedModelIds={230,249,292,151,176,254,181};
        int[] appearance=new int[12];
        for(int i=0;i<expectedKitIds.length;i++) {
            int kitId=expectedKitIds[i],modelId=expectedModelIds[i];
            IdentityKit kit=IdentityKit.cache[kitId];
            check(kit.bodyPartId==i && !kit.notSelectable,"unexpected kit part/selection " + kitId);
            check(kit.models.length==1 && kit.models[0]==modelId,"unexpected model mapping for kit " + kitId);
            byte[] compressed=indexFile(data,idx1,1,modelId);
            check(compressed.length>=18,"empty compressed model " + modelId);
            byte[] modelBytes=gunzipModel(compressed);
            check(modelBytes.length>=18,"empty actual model " + modelId);
            Model.method1700(modelBytes,modelId,false);
            check(Model.method1145(modelId),"model loader cache header missing for model="+modelId);
            Model mesh=Model.method3293(modelId);
            check(mesh!=null && mesh.vertexCount>0 && mesh.faceCount>0,"model has no geometry: "+modelId);
            appearance[i]=256+kitId;
            System.out.println("R267_KIT_MODEL id="+modelId+" vertices="+mesh.vertexCount+" faces="+mesh.faceCount);
        }
        SequenceDefinition.cache=new SequenceDefinition[20_000];
        Client client=new Client();
        Player player=new Player();
        Client.localPlayer=Client.players[2047]=player;
        Method handler=Client.class.getDeclaredMethod("method1850",int.class,Packet.class);
        handler.setAccessible(true);
        byte[] wire=maskedFrame(appearance(appearance,"LocalKit"));
        check(wire.length==66,"appearance frame size mismatch");
        handler.invoke(client,wire.length,new Packet(wire));
        check(Client.localPlayer==player && player.hasAppearance,"opcode 81 did not initialize local player");
        check("LocalKit".equals(player.username),"appearance username mismatch");
        for(int i=0;i<7;i++)check(player.equipment[i]==appearance[i],"kit equipment lost slot="+i);
        Model full=player.method279(true);
        check(full!=null,"actual identity-kit model returned null");
        check(full.vertexCount==264,"player geometry vertex-count drift");
        check(full.faceCount==472,"player geometry face-count drift");

        // Verify model remains usable across ordinary player-sync ticks.
        byte[] noMask={0,0x7f,(byte)0xf0};
        handler.invoke(client,noMask.length,new Packet(noMask));
        check(Client.localPlayer==player,"unmasked sync replaced local player");
        Model afterTick=player.method279(true);
        check(afterTick!=null && afterTick.vertexCount>0 && afterTick.faceCount>0,"model disappeared after unmasked tick");

        // A second complete appearance mask must retain the authentic mesh.
        byte[] replacement=maskedFrame(appearance(appearance,"LocalKit2"));
        handler.invoke(client,replacement.length,new Packet(replacement));
        check("LocalKit2".equals(player.username),"appearance re-sync lost username");
        Model afterReplace=player.method279(true);
        check(afterReplace!=null && afterReplace.vertexCount==264 && afterReplace.faceCount==472,"appearance replacement lost mesh");

        boolean rejectedTruncation=false;
        byte[] truncated=Arrays.copyOf(replacement,7);
        try {handler.invoke(client,truncated.length,new Packet(truncated));}
        catch(InvocationTargetException ex) { rejectedTruncation=ex.getCause() instanceof RuntimeException || ex.getCause() instanceof Error; }
        check(rejectedTruncation,"truncated wire frame was accepted");
        System.out.println("R267_AUTHENTIC_KIT_ACTOR_PASS checks="+checks+
            " player_vertices="+full.vertexCount+" player_faces="+full.faceCount+
            " appearance_bytes="+wire.length+" kits=7");
    }
}