import java.io.*;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;
import rs.*;
import rs.cache.osrs.OsrsModelCache;
import rs.definitions.ObjectDefinition;
import rs.io.Archive;
import rs.io.Packet;
import rs.model.Model;
import rs.eventbus.EventBus;

/** Exercises real Client.method2310 -> pending queue -> Client.method1808 -> Scene. */
public final class R278ObjectActionAuthorityRegression {
 static int checks;
 static void ck(boolean ok,String why){if(!ok)throw new AssertionError(why);checks++;}
 static int u16(byte[] b,int i){return (b[i]&255)<<8 | (b[i+1]&255);}
 static boolean outgoingIncludesAction(Packet output,int expected) {
  byte[] bytes=Arrays.copyOf(output.payload,output.caret);
  rs.network.Class257 cipher=new rs.network.Class257(new int[]{13,22,37,41});
  int at=0,seen=0,objects=0;
  while(at<bytes.length && seen++<8) {
   int opcode=((bytes[at++]&255)-cipher.method0())&255;
   int dataSize;
   if(opcode==98 || opcode==164 || opcode==248) {
    if(at>=bytes.length)return false;
    dataSize=1+(bytes[at]&255);
   } else if(opcode==183) dataSize=3;
   else if(opcode==228 || opcode==252 || opcode==70 || opcode==234 || opcode==132) {
    dataSize=6;
    if(opcode!=expected)return false;
    objects++;
   } else return false;
   if(at+dataSize>bytes.length)return false;
   at+=dataSize;
  }
  return objects==1 && at==bytes.length;
 }

 static int u24(byte[] b,int i){return (b[i]&255)<<16 | (b[i+1]&255)<<8 | b[i+2]&255;}
 static byte[] read(ZipFile z,String n)throws Exception{ZipEntry e=z.getEntry(n);if(e==null)throw new IOException("missing "+n);try(InputStream in=z.getInputStream(e)){return in.readAllBytes();}}
 static byte[] indexed(byte[] dat,byte[] idx,int id,int index)throws Exception{
  int at=id*6;ck(at+6<=idx.length,"idx bounds");int size=u24(idx,at),sector=u24(idx,at+3);ck(size>0&&size<2_000_000,"idx size");
  ByteArrayOutputStream out=new ByteArrayOutputStream();int seq=0;Set<Integer>seen=new HashSet<>();
  while(out.size()<size){ck(sector>0&&seen.add(sector),"sector loop");int off=sector*520;ck(off+8<=dat.length,"sector bounds");
   ck(u16(dat,off)==id&&u16(dat,off+2)==seq&&(dat[off+7]&255)==index+1,"sector ID");
   int n=Math.min(size-out.size(),512);ck(off+8+n<=dat.length,"payload bounds");out.write(dat,off+8,n);sector=u24(dat,off+4);seq++;
  }return out.toByteArray();
 }
 static void setInt(Object o,String field,int value)throws Exception{Field f=o.getClass().getDeclaredField(field);f.setAccessible(true);f.setInt(o,value);}
 static Object get(Object o,String field)throws Exception{Field f=o.getClass().getDeclaredField(field);f.setAccessible(true);return f.get(o);}
 static Method hidden(String name,Class<?>...sig)throws Exception{Method m=Client.class.getDeclaredMethod(name,sig);m.setAccessible(true);return m;}
 static void tick(Client c)throws Exception{hidden("method1808").invoke(c);}
 static int queueCount(NodeDeque q){int n=0;for(Node x=q.peekFirst();x!=null;x=q.next())n++;return n;}
 static int sceneHash(Client c,int x,int y){return c.field761.method2829(0,x,y);}

 static byte[] spawnBody(int id,int x,int y,int rot){
  int packed=((x-56)<<4)|(y-52);
  if(x<56||x>63||y<52||y>59||id<0||id>65535||rot<0||rot>3)throw new IllegalArgumentException("invalid region delta");
  return new byte[]{(byte)((packed+128)&255),(byte)(id&255),(byte)(id>>>8),(byte)(128-(10*4+rot))};
 }
 static byte[] removeBody(int x,int y,int rot){
  int packed=((x-56)<<4)|(y-52);
  return new byte[]{(byte)(-(10*4+rot)),(byte)packed};
 }
 static void spawn(Client c,Method decoder,int id,int x,int y,int rot)throws Exception {
  Packet p=new Packet(spawnBody(id,x,y,rot));decoder.invoke(c,p,151);ck(p.caret==4,"spawn packet incomplete ID="+id);
 }
 static void remove(Client c,Method decoder,int x,int y,int rot)throws Exception {
  Packet p=new Packet(removeBody(x,y,rot));decoder.invoke(c,p,101);ck(p.caret==2,"remove packet incomplete at "+x+","+y);
 }
 static void occupancy(Client c,int x,int y,boolean present,String why){
  boolean hit=(c.field960[0].clipData[x][y]&256)!=0;ck(hit==present,why+" tile="+x+","+y+" actual="+Integer.toHexString(c.field960[0].clipData[x][y]));
 }
 static void footprint(Client c,int x,int y,int w,int h,boolean present,String why){
  for(int dx=0;dx<w;dx++)for(int dy=0;dy<h;dy++)occupancy(c,x+dx,y+dy,present,why);
 }
 static boolean route(Client c,int startX,int startY,int targetX,int targetY)throws Exception {
  rs.model.Player p=Client.localPlayer;p.method3089(startX,startY,true);
  Method route=hidden("method3573",int.class,int.class,int.class,int.class,int.class,int.class,int.class,int.class,int.class,boolean.class,int.class);
  return (boolean)route.invoke(c,0,0,0,0,startY,0,0,targetY,startX,false,targetX);
 }
 public static void main(String[]args)throws Exception{
  ck(args.length==2,"args config.bin private asset ZIP");
  byte[] conf=Files.readAllBytes(Paths.get(args[0]));ck(conf.length==1432547,"config pin");
  Model.field139=new ModelHeader[80000];Model.field140=new boolean[100000];OsrsModelCache.setOsrsModelHeaders(new ModelHeader[15000]);
  Constructor<?> ml=Class.forName("rs.cache.ModelLoader").getDeclaredConstructor();ml.setAccessible(true);
  Field loader=Model.class.getDeclaredField("field199");loader.setAccessible(true);loader.set(null,ml.newInstance());
  ObjectDefinition.load(new Archive(conf,"config"));ObjectDefinition chest=ObjectDefinition.get(104);
  // Test-only overlay singleton required by the actual io_.addObject. Avoid the
  // GUI's constructor side effects; use the real overlay implementation.
  Class<?> uc=Class.forName("sun.misc.Unsafe");Field uf=uc.getDeclaredField("theUnsafe");uf.setAccessible(true);Object unsafe=uf.get(null);
  Class<?> mgr=Class.forName("rs.graphics.overlay.core.OverlayManager");
  Object manager=uc.getMethod("allocateInstance",Class.class).invoke(unsafe,mgr);
  Field instance=mgr.getDeclaredField("field2400");instance.setAccessible(true);instance.set(null,manager);
  Field inspector=mgr.getDeclaredField("field2394");inspector.setAccessible(true);
  inspector.set(manager,Class.forName("rs.graphics.overlay.recolor.ObjectRecolorOverlay").getDeclaredConstructor().newInstance());
  ck(chest!=null&&"Open chest".equals(chest.name)&&chest.method2285(),"real OSRS chest definition");
  ck(chest.modelIds.length==1&&chest.modelIds[0]==1226,"authentic model ID");
  Client c=new Client();c.eventBus=new EventBus();Client.planeLevel=0;
  c.field945=new int[4][105][105];c.field986=new byte[4][104][104];c.field960=new CollisionMap[4];
  for(int p=0;p<4;p++){c.field960[p]=new CollisionMap();for(int x=1;x<103;x++)for(int y=1;y<103;y++)c.field960[p].clipData[x][y]=0;}
  c.field761=new Scene(c.field945);NodeDeque queue=new NodeDeque();Field fq=Client.class.getDeclaredField("field923");fq.setAccessible(true);fq.set(c,queue);
  setInt(c,"field996",48);setInt(c,"field997",48);
  Method decoder=hidden("method2310",Packet.class,int.class);
  Packet packet=new Packet(new byte[]{(byte)0xa1,(byte)104,0,(byte)88});
  decoder.invoke(c,packet,151);
  ck(packet.caret==4,"incoming object spawn frame not consumed");ck(queueCount(queue)==1,"pending update not queued");
  Object pending=queue.peekFirst();ck(pending!=null&&((Number)get(pending,"field5215")).intValue()==104,"wrong queued id");
  ck(sceneHash(c,50,49)==0,"object already in scene before graphics promotion");
  Client.graphicsMode=1;tick(c);ck(queueCount(queue)==1&&sceneHash(c,50,49)==0,"graphics mode1 incorrectly promoted object");
  Client.graphicsMode=2;tick(c);ck(queueCount(queue)==1&&sceneHash(c,50,49)==0,"model-unready object promoted unexpectedly");
  System.out.println("R275_SCENE_GATE_BEFORE ready="+chest.method197(10)+" queue="+queueCount(queue));
  byte[] dat,idx;try(ZipFile assets=new ZipFile(args[1])){dat=read(assets,".spawnpk/main_file_osrs.dat");idx=read(assets,".spawnpk/main_file_osrs.idx1");}
  byte[] gz=indexed(dat,idx,1226,1);ByteArrayOutputStream raw=new ByteArrayOutputStream();
  try(GZIPInputStream unzip=new GZIPInputStream(new ByteArrayInputStream(gz))){byte[] b=new byte[4096];int n;while((n=unzip.read(b))>=0){raw.write(b,0,n);ck(raw.size()<2_000_000,"OSRS model inflate cap");}}
  ck(raw.size()>18,"empty OSRS chest model");Model.method1700(raw.toByteArray(),1226,true);OsrsModelCache.setOsrsEnabled(true);
  ck(chest.method197(10),"OSRS chest model readiness still false");
  Model mesh=chest.method2125(10,0,0,0,0,0,-1,-1);ck(mesh!=null&&mesh.vertexCount==152&&mesh.faceCount==286,"real cached geometry wrong");
  try { tick(c); }
  catch(InvocationTargetException ex){ System.err.println("R275_PENDING_TICK_EXCEPTION="+ex.getCause()); throw ex; }
  int hash=sceneHash(c,50,49);
  ck(hash!=0,"client pending object was not promoted after model readiness");
  ck((hash>>14&32767)==104,"promoted object ID incorrect");
  ck(c.field761.getHashAtTile(0,50,49,hash)>=0,"scene picker lookup cannot resolve promoted object");
  ck(queueCount(queue)==1,"pending scene replacement state disappeared prematurely");
  ck(((Number)get(queue.peekFirst(),"field5226")).intValue()==-1,"pending replacement not marked promoted");
  tick(c);ck(sceneHash(c,50,49)==hash,"scene object not stable on next tick");
  // Real matching in-world object removal subpacket 101, shape 10 + local (50,49).
  Packet remove=new Packet(new byte[]{(byte)0xd8,(byte)0x21});
  decoder.invoke(c,remove,101);
  ck(remove.caret==2,"object removal packet not consumed");
  ck(queueCount(queue)==1,"removal should update the same pending object record");
  ck(sceneHash(c,50,49)==hash,"removal advanced scene before processing tick");
  tick(c);
  ck(sceneHash(c,50,49)==0,"actual source didn't remove chest from scene");
  ck(c.field761.getHashAtTile(0,50,49,hash)==-1,"stale scene hash accepted after removal");
  tick(c);ck(sceneHash(c,50,49)==0,"removed object reappeared without spawn");

  // R277: actual multi-model and rotated-footprint lifecycle.
  // Existing chest R275 setup has been restored to empty at this point.
  ck(queueCount(queue)==0,"prior R275 queue must be empty");
  setInt(c,"field996",56);setInt(c,"field997",52);
  int[][] defs={{2,731,4,2},{114,5274,1,2},{152,1428,2,2},{104,1226,1,1}};
  byte[] osrsData,osrsIdx;
  try(ZipFile assets=new ZipFile(args[1])){
   osrsData=read(assets,".spawnpk/main_file_osrs.dat");
   osrsIdx=read(assets,".spawnpk/main_file_osrs.idx1");
  }
  for(int[] spec:defs){
   int id=spec[0],modelId=spec[1];ObjectDefinition d=ObjectDefinition.get(id);
   ck(d!=null,"missing definition "+id);
   ck(d.method2285()&&d.modelIds.length==1&&d.modelIds[0]==modelId,"model mapping "+id);
   ck(d.sizeX==spec[2]&&d.sizeY==spec[3],"real definition footprint "+id);
   ck(d.field1186,"expected solid-object definition "+id);
   byte[] gzip=indexed(osrsData,osrsIdx,modelId,1);
   try(GZIPInputStream zin=new GZIPInputStream(new ByteArrayInputStream(gzip))){
    ByteArrayOutputStream o=new ByteArrayOutputStream();byte[] buf=new byte[4096];int n;
    while((n=zin.read(buf))!=-1){o.write(buf,0,n);ck(o.size()<1_000_000,"decompression cap");}
    ck(o.size()>18,"real geometry file empty "+id);Model.method1700(o.toByteArray(),modelId,true);
   }
   ck(d.method197(10),"model not ready after authentic cache load "+id);
   Model candidateMesh=d.method2125(10,0,0,0,0,0,-1,-1);
   ck(candidateMesh!=null&&candidateMesh.vertexCount>0&&candidateMesh.faceCount>0,"no genuine mesh "+id);
   System.out.println("R277_REAL_MODEL id="+id+" name="+d.name+" model="+modelId+" footprint="+d.sizeX+"x"+d.sizeY+" vertices="+candidateMesh.vertexCount+" faces="+candidateMesh.faceCount);
  }
  int[][] instances={{2,56,52,0},{114,60,52,1},{152,59,56,0},{104,63,59,0}};
  for(int[] e:instances){spawn(c,decoder,e[0],e[1],e[2],e[3]);ck(sceneHash(c,e[1],e[2])==0,"premature mixed object "+e[0]);}
  ck(queueCount(queue)==4,"mixed objects not independently queued");
  tick(c);
  int[] hashes=new int[instances.length];
  for(int i=0;i<instances.length;i++){
   int[] e=instances[i];hashes[i]=sceneHash(c,e[1],e[2]);
   ck(hashes[i]!=0,"mixed object scene promotion missing id="+e[0]);
   ck(((hashes[i]>>14)&32767)==e[0],"wrong promoted ID at "+e[1]+","+e[2]);
   ck(c.field761.getHashAtTile(0,e[1],e[2],hashes[i])>=0,"scene picking not authoritative id="+e[0]);
  }
  Client.baseX=3152;Client.baseY=3152;
  rs.model.Player initialActionPlayer=new rs.model.Player();initialActionPlayer.method3089(54,55,true);
  Client.localPlayer=Client.players[2047]=initialActionPlayer;
  // R278 source-backed present-object behavior: all 5 standard world-object
  // options must preserve their real outbound encoder while Scene authority holds.
  Method objectMenu=hidden("handleMenuAction",int.class,int.class,int.class,int.class,int.class,String.class);
  int[] menuOptions={1062,900,113,872,502};
  int[] wireActions={228,252,70,234,132};
  for(int i=0;i<instances.length;i++) {
   int[] e=instances[i];
   for(int j=0;j<menuOptions.length;j++) {
    Client.outgoingPacket=Packet.newInstance();
    Client.outgoingPacket.isaacRandom=new rs.network.Class257(new int[]{13,22,37,41});
    objectMenu.invoke(c,menuOptions[j],hashes[i],e[1],e[2],e[0],"present object");
    ck(Client.outgoingPacket.caret>=7,"valid object action suppressed id="+e[0]+" action="+menuOptions[j]);
    ck(outgoingIncludesAction(Client.outgoingPacket,wireActions[j]),"valid action opcode/framing changed id="+e[0]+" expected="+wireActions[j]);
    ck(sceneHash(c,e[1],e[2])==hashes[i],"menu action mutated live scene object");
   }
  }
  System.out.println("R278_PRESENT_OBJECT_OPTIONS_PASS objects=4 menuOptions=5 preserved=20");
  footprint(c,56,52,4,2,true,"cave4x2");
  footprint(c,60,52,2,1,true,"range rotated orientation1 2x1");
  footprint(c,59,56,2,2,true,"compost2x2");
  occupancy(c,63,59,true,"chest1x1");
  // Rotating 1x2 range from east/west to north/south must swap blocked footprint.
  remove(c,decoder,60,52,1);tick(c);
  ck(sceneHash(c,60,52)==0,"rotated range scene was not removed");
  occupancy(c,60,52,false,"range anchor cleaned");
  occupancy(c,61,52,false,"range former rotated extension cleaned");
  ck(sceneHash(c,56,52)==hashes[0]&&sceneHash(c,59,56)==hashes[2],"range removal corrupted neighbors");
  spawn(c,decoder,114,60,52,0);tick(c);
  ck(sceneHash(c,60,52)!=0,"range rotation0 not promoted");
  occupancy(c,60,52,true,"range anchor restored");
  occupancy(c,60,53,true,"range rotation0 extension on Y");
  occupancy(c,61,52,false,"stale rotation1 collision leaked on X");
  // The 4x2 and 2x2 solid objects should block exact-target click routing.
  Client.baseX=3152;Client.baseY=3152;
  rs.model.Player player=new rs.model.Player();player.method3089(54,55,true);
  Client.localPlayer=Client.players[2047]=player;
  Client.outgoingPacket=Packet.newInstance();Client.outgoingPacket.isaacRandom=new rs.network.Class257(new int[]{13,22,37,41});
  int before=Client.outgoingPacket.caret;
  boolean throughCave=route(c,54,54,57,52);
  ck(!throughCave,"pathfinding allowed target inside solid 4x2 cave footprint");
  ck(Client.outgoingPacket.caret==before,"pathfinder emitted packet through a blocked cave tile");
  boolean throughHeap=route(c,54,56,59,56);
  ck(!throughHeap,"pathfinding allowed target inside solid 2x2 compost footprint");
  ck(Client.outgoingPacket.caret==before,"pathfinder emitted packet into blocked heap");
  boolean around=route(c,54,54,55,54);
  ck(around,"nearby empty tile became unreachable");
  ck(Client.outgoingPacket.caret>before,"empty path produced no walk packet");
  // Removal of cave must release its full 4x2 footprint and permit former tile.
  remove(c,decoder,56,52,0);tick(c);
  ck(sceneHash(c,56,52)==0,"cave still in scene after removal");
  footprint(c,56,52,4,2,false,"cave4x2 cleared");
  ck(c.field761.getHashAtTile(0,56,52,hashes[0])==-1,"stale cave scene lookup accepted");
  // All ordinary object options must be scene-authoritative, not just the
  // already-fixed item-on-object and spell-on-object branches.
  for(int actionId:menuOptions) {
   Client.outgoingPacket=Packet.newInstance();
   Client.outgoingPacket.isaacRandom=new rs.network.Class257(new int[]{13,22,37,41});
   objectMenu.invoke(c,actionId,hashes[0],56,52,2,"removed cave");
   ck(Client.outgoingPacket.caret==0,"STALE_SCENE_OBJECT_OPTION_EMITTED_PACKET action="+actionId);
  }
  System.out.println("R278_STALE_OBJECT_MENU_OPTIONS_PASS removed_cave=5 rejected=5");

  Client.outgoingPacket=Packet.newInstance();Client.outgoingPacket.isaacRandom=new rs.network.Class257(new int[]{13,22,37,41});
  ck(route(c,54,54,57,52),"former cave tile not traversable after removal");
  ck(Client.outgoingPacket.caret>0,"open cave tile failed to produce walk packet");
  // Guard for item-on-object after different-ID 4x2 removal must also apply.
  Client.outgoingPacket=Packet.newInstance();Client.outgoingPacket.isaacRandom=new rs.network.Class257(new int[]{13,22,37,41});
  Method action=hidden("handleMenuAction",int.class,int.class,int.class,int.class,int.class,String.class);
  action.invoke(c,62,hashes[0],56,52,2,"Use -> removed cave");
  ck(Client.outgoingPacket.caret==0,"R274 stale scene guard regressed for cave ID2");
  for(int[] e:new int[][]{{104,63,59,0},{152,59,56,0},{114,60,52,0}}){
   remove(c,decoder,e[1],e[2],e[3]);tick(c);
   ck(sceneHash(c,e[1],e[2])==0,"multi-ID removal failed id="+e[0]);
  }
  footprint(c,60,52,1,2,false,"range removed full1x2");
  footprint(c,59,56,2,2,false,"compost removed full2x2");
  occupancy(c,63,59,false,"chest removed");
  ck(sceneHash(c,55,59)==0,"unrelated scene position polluted");
  System.out.println("R278_AUTHORITY_FULL_REAL_CLIENT_PASS checks="+checks+" ids=2,114,152,104 model_banks=osrs rotations=0,1 " +
     "cave=4x2 compost=2x2 range=1x2 rotated=2x1 blocked_target_refused=true collision_cleared=true");
 }
}
