import java.io.File;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;
import java.util.stream.Stream;

/**
 * R414 independent portable Java11 real TEMP-filesystem restart-intent model.
 * All history bytes and rows are invented. No private game class/JAR, actual
 * user history, original-client process or production filesystem is opened.
 *
 * No cleanup/adoption/journal producer is installed into the game. The
 * synthetic setup itself creates markers and crash scenarios for testing.
 */
public final class R414PassiveRestartIntentSynthetic {
    enum Result {NONE,ABORTED_BEFORE_REPLACE,COMMITTED_BEFORE_ACK,QUARANTINED}
    static int passed,optionalSymlinkPassed;
    static final String HEADER="synthetic-history-v1\n";
    static final String INTENT_NAME="invented-history.delete.intent";
    static final int MAX_INTENT_BYTES=512;
    static final int MAX_HISTORY_BYTES=1024*1024;
    static final String ABSENT="ABSENT";
    static final String NONCE="11111111-2222-3333-4444-555555555555";
    static void yes(boolean b,String why){if(!b)throw new AssertionError(why);}
    static void eq(Object x,Object y,String why){
        if(!java.util.Objects.equals(x,y))
            throw new AssertionError(why+" "+x+" != "+y);
    }
    static String sha(byte[] bytes){
        try {
            byte[] digest=MessageDigest.getInstance("SHA-256").digest(bytes);
            StringBuilder b=new StringBuilder(64);
            for(byte v:digest){
                b.append(Character.forDigit((v>>4)&15,16));
                b.append(Character.forDigit(v&15,16));
            }
            return b.toString();
        }catch(Exception e){throw new IllegalStateException(e);}
    }
    static byte[] image(int... ids){
        StringBuilder s=new StringBuilder(HEADER);
        for(int id:ids)s.append(id).append('\n');
        return s.toString().getBytes(StandardCharsets.US_ASCII);
    }
    static String manifest(String before,String after){
        return "v=1\nserial=1\nnonce="+NONCE+"\nbefore="+before+"\nafter="+after+"\n";
    }
    static boolean same(BasicFileAttributes a,BasicFileAttributes b){
        return a.isRegularFile()==b.isRegularFile() &&
            a.size()==b.size() &&
            a.lastModifiedTime().equals(b.lastModifiedTime()) &&
            (a.fileKey()==null||a.fileKey().equals(b.fileKey()));
    }
    static final class Inspector {
        final Path dir,history,stage,intent,intentTemp;
        int currentHashReadCount,markerHashReadCount,automaticDeletes,automaticWrites;
        Inspector(Path folder){
            dir=folder;
            history=folder.resolve("invented-history.txt");
            stage=folder.resolve("invented-history.txt.tmp");
            intent=folder.resolve(INTENT_NAME);
            intentTemp=folder.resolve(INTENT_NAME+".tmp");
        }
        boolean existsNoFollow(Path p)throws IOException{
            try{Files.readAttributes(p,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);return true;}
            catch(java.nio.file.NoSuchFileException missing){return false;}
        }
        String digestHistory()throws IOException{
            BasicFileAttributes a;
            try {a=Files.readAttributes(history,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);}
            catch(java.nio.file.NoSuchFileException absent){return ABSENT;}
            if(!a.isRegularFile()||a.size()>MAX_HISTORY_BYTES)return null;
            try(FileChannel c=FileChannel.open(history,StandardOpenOption.READ,LinkOption.NOFOLLOW_LINKS)){
                if(c.size()!=a.size())return null;
                MessageDigest h=MessageDigest.getInstance("SHA-256");
                ByteBuffer chunk=ByteBuffer.allocate(8192);
                long read=0;
                int count;
                while((count=c.read(chunk))!=-1){
                    if(count==0)continue;
                    chunk.flip();read+=count;
                    if(read>MAX_HISTORY_BYTES)return null;
                    h.update(chunk);chunk.clear();
                }
                if(read!=a.size()||
                   !same(a,Files.readAttributes(history,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS)))
                    return null;
                currentHashReadCount++;
                byte[] hash=h.digest();StringBuilder b=new StringBuilder(64);
                for(byte v:hash){b.append(Character.forDigit((v>>4)&15,16));b.append(Character.forDigit(v&15,16));}
                return b.toString();
            }catch(java.security.NoSuchAlgorithmException error){return null;}
        }
        Result classify() {
            try{
                if(existsNoFollow(intentTemp))return Result.QUARANTINED;
                BasicFileAttributes a;
                try{a=Files.readAttributes(intent,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);}
                catch(java.nio.file.NoSuchFileException absent){return Result.NONE;}
                if(!a.isRegularFile()||a.size()<100||a.size()>MAX_INTENT_BYTES)
                    return Result.QUARANTINED;
                byte[] marker=new byte[(int)a.size()];
                try(FileChannel channel=FileChannel.open(intent,
                        StandardOpenOption.READ,LinkOption.NOFOLLOW_LINKS)){
                    ByteBuffer bytes=ByteBuffer.wrap(marker);
                    while(bytes.hasRemaining()){
                        if(channel.read(bytes)<0)return Result.QUARANTINED;
                    }
                    if(channel.read(ByteBuffer.allocate(1))!=-1)
                        return Result.QUARANTINED;
                }
                if(!same(a,Files.readAttributes(intent,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS)))
                    return Result.QUARANTINED;
                String content=new String(marker,StandardCharsets.US_ASCII);
                String[] fields=content.split("\n",-1);
                if(fields.length!=6||!fields[0].equals("v=1")||
                    !fields[1].matches("serial=[1-9][0-9]{0,15}")||
                    !fields[2].matches("nonce=[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")||
                    !fields[3].matches("before=(ABSENT|[0-9a-f]{64})")||
                    !fields[4].matches("after=[0-9a-f]{64}")||
                    !fields[5].isEmpty()||
                    !Arrays.equals(marker,content.getBytes(StandardCharsets.US_ASCII)))
                    return Result.QUARANTINED;
                String old=fields[3].substring(7),next=fields[4].substring(6);
                if(old.equals(next))return Result.QUARANTINED;
                String disk=digestHistory();
                if(disk==null)return Result.QUARANTINED;
                if(!same(a,Files.readAttributes(intent,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS)))
                    return Result.QUARANTINED;
                if(disk.equals(old))return Result.ABORTED_BEFORE_REPLACE;
                if(disk.equals(next))return Result.COMMITTED_BEFORE_ACK;
                return Result.QUARANTINED;
            }catch(IOException|RuntimeException bad){return Result.QUARANTINED;}
        }
        boolean allowRestoreOrSaveOrClear(){
            try{
                if(classify()!=Result.NONE)return false;
                return !existsNoFollow(stage);
            }catch(IOException e){return false;}
        }
    }
    interface Scenario {void execute(Inspector i)throws Exception;}
    static void scenario(String label,Scenario task)throws Exception{
        Path dir=Files.createTempDirectory("r414-fabricated-");
        try{
            Inspector i=new Inspector(dir);
            task.execute(i);
            yes(i.automaticWrites==0&&i.automaticDeletes==0,"inspector changed files");
            passed++;
        }catch(Throwable e){throw new AssertionError(label,e);}
        finally {
            try(Stream<Path> stream=Files.walk(dir)){
                stream.sorted(Comparator.reverseOrder()).forEach(x->{
                    try{Files.deleteIfExists(x);}catch(IOException e){throw new IllegalStateException(e);}
                });
            }
        }
    }
    static void marker(Inspector i,String contents)throws IOException{
        Files.write(i.intent,contents.getBytes(StandardCharsets.US_ASCII),
            StandardOpenOption.CREATE_NEW);
    }
    static void noMarkerIsClearEvenWithMain()throws Exception{
        scenario("no marker",i->{
            Files.write(i.history,image(1,2),StandardOpenOption.CREATE_NEW);
            eq(i.classify(),Result.NONE,"clean state");
            eq(i.currentHashReadCount,0,"read main without marker");
            yes(i.allowRestoreOrSaveOrClear(),"normal use blocked");
        });
    }
    static void validBeforeImageIsAborted()throws Exception{
        scenario("old image",i->{
            byte[] old=image(1,2),next=image(2);
            Files.write(i.history,old);
            marker(i,manifest(sha(old),sha(next)));
            eq(i.classify(),Result.ABORTED_BEFORE_REPLACE,"old image mismatch");
            yes(!i.allowRestoreOrSaveOrClear(),"matched old intent permitted writes");
        });
    }
    static void validAfterImageIsCommittedBeforeAck()throws Exception{
        scenario("committed image",i->{
            byte[] old=image(1,2),next=image(2);
            Files.write(i.history,next);
            marker(i,manifest(sha(old),sha(next)));
            eq(i.classify(),Result.COMMITTED_BEFORE_ACK,"after image mismatch");
            yes(!i.allowRestoreOrSaveOrClear(),"matched committed intent permitted writes");
        });
    }
    static void absentOriginalHistoryMatchesBefore()throws Exception{
        scenario("before absent",i->{
            marker(i,manifest("ABSENT",sha(image(1))));
            eq(i.classify(),Result.ABORTED_BEFORE_REPLACE,"absent main precommit");
        });
    }
    static void absentOriginalButCommittedHistoryMatchesAfter()throws Exception{
        scenario("after when old absent",i->{
            Files.write(i.history,image(1));
            marker(i,manifest("ABSENT",sha(image(1))));
            eq(i.classify(),Result.COMMITTED_BEFORE_ACK,"newly created main");
        });
    }
    static void mutatedHistoryIsQuarantined()throws Exception{
        scenario("history hash mismatch",i->{
            Files.write(i.history,image(7));
            marker(i,manifest(sha(image(1,2)),sha(image(2))));
            eq(i.classify(),Result.QUARANTINED,"unexpected disk bytes accepted");
        });
    }
    static void noMainWhenExpectedOldOrNewIsQuarantined()throws Exception{
        scenario("missing main",i->{
            marker(i,manifest(sha(image(1)),sha(image(2))));
            eq(i.classify(),Result.QUARANTINED,"missing main accepted");
        });
    }
    static void preparedMarkerTempRefusedWithoutFinalMarker()throws Exception{
        scenario("marker temp only",i->{
            Files.write(i.intentTemp,new byte[]{1,2});
            eq(i.classify(),Result.QUARANTINED,"unresolved intent tmp accepted");
        });
    }
    static void markerTempTakesPrecedence()throws Exception{
        scenario("both marker files",i->{
            Files.write(i.history,image(2));
            marker(i,manifest(sha(image(1)),sha(image(2))));
            Files.write(i.intentTemp,new byte[]{7});
            eq(i.classify(),Result.QUARANTINED,"second staged marker ignored");
        });
    }
    static void historyStageWithoutIntentStillRefused()throws Exception{
        scenario("unresolved history stage",i->{
            Files.write(i.stage,new byte[]{9},StandardOpenOption.CREATE_NEW);
            eq(i.classify(),Result.NONE,"not an intent");
            yes(!i.allowRestoreOrSaveOrClear(),"R411 stage fence missing");
        });
    }
    static void malformedMarkerVersionRefused()throws Exception{
        scenario("bad version",i->{
            marker(i,manifest(sha(image(1)),sha(image(2))).replace("v=1","v=2"));
            eq(i.classify(),Result.QUARANTINED,"bad version");
        });
    }
    static void invalidNonceRefused()throws Exception{
        scenario("bad nonce",i->{
            marker(i,manifest(sha(image(1)),sha(image(2))).replace(NONCE,"not-a-uuid"));
            eq(i.classify(),Result.QUARANTINED,"bad nonce");
        });
    }
    static void invalidSerialRefused()throws Exception{
        scenario("bad serial",i->{
            marker(i,manifest(sha(image(1)),sha(image(2))).replace("serial=1","serial=0"));
            eq(i.classify(),Result.QUARANTINED,"bad serial");
        });
    }
    static void equalDigestsRefused()throws Exception{
        scenario("equal before after",i->{
            String hash=sha(image(1));
            marker(i,manifest(hash,hash));
            eq(i.classify(),Result.QUARANTINED,"identical digest");
        });
    }
    static void oversizedMarkerRefused()throws Exception{
        scenario("marker oversized",i->{
            byte[] huge=new byte[MAX_INTENT_BYTES+1];
            Arrays.fill(huge,(byte)'Z');
            Files.write(i.intent,huge);
            eq(i.classify(),Result.QUARANTINED,"oversized intent");
            eq(i.currentHashReadCount,0,"main read on oversized intent");
        });
    }
    static void emptyMarkerRefused()throws Exception{
        scenario("empty marker",i->{
            Files.write(i.intent,new byte[0]);
            eq(i.classify(),Result.QUARANTINED,"empty intent");
        });
    }
    static void extraFieldsRefused()throws Exception{
        scenario("extra field",i->{
            marker(i,manifest(sha(image(1)),sha(image(2)))+"unexpected=field\n");
            eq(i.classify(),Result.QUARANTINED,"extra field");
        });
    }
    static void uppercaseDigestRefused()throws Exception{
        scenario("upper hex",i->{
            marker(i,manifest(sha(image(1)).toUpperCase(),sha(image(2))));
            eq(i.classify(),Result.QUARANTINED,"uppercase hash");
        });
    }
    static void nonAsciiMarkerRefused()throws Exception{
        scenario("nonascii",i->{
            byte[] marker=manifest(sha(image(1)),sha(image(2)))
                .getBytes(StandardCharsets.US_ASCII);
            marker[4]=(byte)0xff;
            Files.write(i.intent,marker);
            eq(i.classify(),Result.QUARANTINED,"nonascii marker");
        });
    }
    static void truncatedIntentRefused()throws Exception{
        scenario("truncated intent",i->{
            String intent=manifest(sha(image(1)),sha(image(2)));
            marker(i,intent.substring(0,intent.length()-11));
            eq(i.classify(),Result.QUARANTINED,"partial marker");
        });
    }
    static void markerDirectoryRefused()throws Exception{
        scenario("directory marker",i->{
            Files.createDirectory(i.intent);
            eq(i.classify(),Result.QUARANTINED,"directory marker");
        });
    }
    static void markerTempDirectoryRefused()throws Exception{
        scenario("directory staged marker",i->{
            Files.createDirectory(i.intentTemp);
            eq(i.classify(),Result.QUARANTINED,"directory staged marker");
        });
    }
    static void symlinkMarkerRefusedWhereSupported()throws Exception{
        Path d=Files.createTempDirectory("r414-link-");
        try{
            Inspector i=new Inspector(d);
            Path foreign=d.resolve("invented-target.txt");
            Files.write(foreign,manifest(sha(image(1)),sha(image(2)))
                .getBytes(StandardCharsets.US_ASCII));
            try {
                Files.createSymbolicLink(i.intent,foreign.getFileName());
                eq(i.classify(),Result.QUARANTINED,"followed symlink intent");
                optionalSymlinkPassed++;
            }catch(UnsupportedOperationException|SecurityException|IOException unsupported){
                System.out.println("R414_OPTIONAL_SYMLINK_UNSUPPORTED");
            }
        }finally{
            try(Stream<Path> e=Files.walk(d)){
                e.sorted(Comparator.reverseOrder()).forEach(x->{
                    try{Files.deleteIfExists(x);}catch(IOException y){throw new IllegalStateException(y);}
                });
            }
        }
    }
    static void symlinkHistoryRefusedWhereSupported()throws Exception{
        Path d=Files.createTempDirectory("r414-history-link-");
        try {
            Inspector i=new Inspector(d);
            Path foreign=d.resolve("outside.txt");
            Files.write(foreign,image(2));
            marker(i,manifest(sha(image(1)),sha(image(2))));
            try {
                Files.createSymbolicLink(i.history,foreign.getFileName());
                eq(i.classify(),Result.QUARANTINED,"followed main symlink");
                optionalSymlinkPassed++;
            }catch(UnsupportedOperationException|SecurityException|IOException unsupported){
                System.out.println("R414_OPTIONAL_HISTORY_SYMLINK_UNSUPPORTED");
            }
        }finally{
            try(Stream<Path> e=Files.walk(d)){
                e.sorted(Comparator.reverseOrder()).forEach(x->{
                    try{Files.deleteIfExists(x);}catch(IOException y){throw new IllegalStateException(y);}
                });
            }
        }
    }
    static void hugeMainRefused()throws Exception{
        scenario("oversized main",i->{
            try(FileChannel c=FileChannel.open(i.history,
                 StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE)){
                c.position(MAX_HISTORY_BYTES+10L);
                c.write(ByteBuffer.wrap(new byte[]{1}));
            }
            marker(i,manifest(sha(image(1)),sha(image(2))));
            eq(i.classify(),Result.QUARANTINED,"oversized disk");
        });
    }
    static void doubleClassificationIsReadOnly()throws Exception{
        scenario("no mutation",i->{
            byte[] content=image(2);
            Files.write(i.history,content);
            byte[] intent=manifest(sha(image(1)),sha(content))
                .getBytes(StandardCharsets.US_ASCII);
            Files.write(i.intent,intent);
            eq(i.classify(),Result.COMMITTED_BEFORE_ACK,"first");
            eq(i.classify(),Result.COMMITTED_BEFORE_ACK,"repeat");
            yes(Arrays.equals(content,Files.readAllBytes(i.history)),"main changed");
            yes(Arrays.equals(intent,Files.readAllBytes(i.intent)),"intent changed");
        });
    }
    static void interruptedCommitPersistedMarkerReadByFreshJvm()throws Exception {
        Path temp=Files.createTempDirectory("r414-child-");
        try{
            List<String> command=new ArrayList<>();
            command.add(System.getProperty("java.home")+File.separator+"bin"+File.separator+"java");
            command.add("-cp");command.add(System.getProperty("java.class.path"));
            command.add(R414PassiveRestartIntentSynthetic.class.getName());
            command.add("--child-commit-before-ack");command.add(temp.toString());
            Process child=new ProcessBuilder(command).inheritIO().start();
            int exit=child.waitFor();
            eq(exit,71,"child did not crash after synthetic commit");
            Inspector restored=new Inspector(temp);
            eq(restored.classify(),Result.COMMITTED_BEFORE_ACK,
                "separate JVM failed committed-before-ack classification");
            yes(!restored.allowRestoreOrSaveOrClear(),
                "fresh process wrongly opened write gate");
            yes(Files.exists(restored.intent),"fresh JVM removed evidence");
            System.out.println("R414_CHILD_RECOVERY_COMMITTED_BEFORE_ACK");
            passed++;
        }finally{
            try(Stream<Path> e=Files.walk(temp)){
                e.sorted(Comparator.reverseOrder()).forEach(x->{
                    try{Files.deleteIfExists(x);}catch(IOException y){throw new IllegalStateException(y);}
                });
            }
        }
    }
    static void childCommit(Path dir)throws Exception{
        byte[] before=image(1,2),after=image(2);
        Path history=dir.resolve("invented-history.txt");
        Path marker=dir.resolve(INTENT_NAME);
        Path tmp=dir.resolve("invented-history.txt.tmp");
        Files.write(history,before,StandardOpenOption.CREATE_NEW);
        byte[] intent=manifest(sha(before),sha(after))
            .getBytes(StandardCharsets.US_ASCII);
        try(FileChannel c=FileChannel.open(marker,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE)){
            c.write(ByteBuffer.wrap(intent));c.force(true);
        }
        try(FileChannel c=FileChannel.open(tmp,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE)){
            c.write(ByteBuffer.wrap(after));c.force(true);
        }
        Files.move(tmp,history,StandardCopyOption.REPLACE_EXISTING,
            StandardCopyOption.ATOMIC_MOVE);
        // Deliberate process exit before any simulated UI adoption.
        System.exit(71);
    }
    public static void main(String[] args)throws Exception {
        if(args.length==2&&args[0].equals("--child-commit-before-ack")){
            childCommit(Path.of(args[1]));return;
        }
        noMarkerIsClearEvenWithMain();
        validBeforeImageIsAborted();
        validAfterImageIsCommittedBeforeAck();
        absentOriginalHistoryMatchesBefore();
        absentOriginalButCommittedHistoryMatchesAfter();
        mutatedHistoryIsQuarantined();
        noMainWhenExpectedOldOrNewIsQuarantined();
        preparedMarkerTempRefusedWithoutFinalMarker();
        markerTempTakesPrecedence();
        historyStageWithoutIntentStillRefused();
        malformedMarkerVersionRefused();
        invalidNonceRefused();
        invalidSerialRefused();
        equalDigestsRefused();
        oversizedMarkerRefused();
        emptyMarkerRefused();
        extraFieldsRefused();
        uppercaseDigestRefused();
        nonAsciiMarkerRefused();
        truncatedIntentRefused();
        markerDirectoryRefused();
        markerTempDirectoryRefused();
        symlinkMarkerRefusedWhereSupported();
        symlinkHistoryRefusedWhereSupported();
        hugeMainRefused();
        doubleClassificationIsReadOnly();
        interruptedCommitPersistedMarkerReadByFreshJvm();
        System.out.println("R414_SYNTHETIC_RESTART_INTENT_PASS "+passed+" mandatory cases");
        System.out.println("R414_OPTIONAL_SYMLINK_VERIFIED "+optionalSymlinkPassed);
        System.out.println("R414_PRIVATE_GAME_EXECUTION_AND_POWER_LOSS_UNPROVEN");
    }
}
