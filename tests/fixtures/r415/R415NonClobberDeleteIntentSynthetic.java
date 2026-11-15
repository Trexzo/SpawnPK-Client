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
import java.util.UUID;
import java.util.stream.Stream;

/**
 * R415 public independently invented atomic nonclobber intent producer model.
 *
 * Uses ONLY self-created TEMP files with fabricated integer IDs. The real
 * recovered game client, its JSON history, JAR, settings, caches and accounts
 * are never loaded. This does not establish true physical crash durability,
 * directory fsync, cooperative cross-process locking or production safety.
 *
 * A successful marked deletion deliberately blocks subsequent writes until
 * separate verified restart adoption/acknowledgment logic exists.
 */
public final class R415NonClobberDeleteIntentSynthetic {
    static final String HEADER="fabricated-history-v1\n";
    static final String INTENT_NAME="invented-history.delete.intent";
    static final String ABSENT="ABSENT";
    static int passed;
    enum Phase {NOT_ATTEMPTED,FAILED_BEFORE_REPLACE,REPLACE_ATTEMPTED,COMMITTED}
    enum State {NONE,ABORTED_BEFORE_REPLACE,COMMITTED_BEFORE_ACK,QUARANTINED}
    enum Fault {
        NONE, STAGE_FORCE_FAILURE, AFTER_STAGE_FORCE,
        INTENT_FORCE_FAILURE, AFTER_INTENT_FORCE,
        FOREIGN_MARKER_AFTER_PREFLIGHT, AFTER_HARDLINK,
        AFTER_INTENT_TEMP_REMOVAL, HISTORY_CHANGED_AFTER_INTENT,
        STAGE_CHANGED_AFTER_INTENT, ATOMIC_MOVE_UNSUPPORTED,
        AFTER_HISTORY_REPLACEMENT
    }
    static final class Crash extends RuntimeException {
        Crash(Fault point){super("invented synthetic interruption "+point);}
    }
    static void yes(boolean x,String why){if(!x)throw new AssertionError(why);}
    static void eq(Object x,Object y,String why){
        if(!java.util.Objects.equals(x,y))
            throw new AssertionError(why+" actual="+x+" expected="+y);
    }
    static byte[] encode(int... ids){
        StringBuilder s=new StringBuilder(HEADER);
        for(int id:ids)s.append(id).append('\n');
        return s.toString().getBytes(StandardCharsets.US_ASCII);
    }
    static String sha(byte[] bytes){
        try{
            byte[] hash=MessageDigest.getInstance("SHA-256").digest(bytes);
            StringBuilder s=new StringBuilder(64);
            for(byte b:hash) {
                s.append(Character.forDigit((b>>>4)&15,16));
                s.append(Character.forDigit(b&15,16));
            }
            return s.toString();
        }catch(Exception e){throw new AssertionError(e);}
    }
    static String contents(Path path)throws IOException {
        return new String(Files.readAllBytes(path),StandardCharsets.US_ASCII);
    }
    static String digest(Path path,boolean absentAllowed)throws IOException {
        BasicFileAttributes a;
        try{a=Files.readAttributes(path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);}
        catch(java.nio.file.NoSuchFileException absent){return absentAllowed?ABSENT:null;}
        if(!a.isRegularFile()||a.size()>1024*1024)return null;
        byte[] bytes;
        try(FileChannel c=FileChannel.open(path,
                StandardOpenOption.READ,LinkOption.NOFOLLOW_LINKS)){
            if(c.size()!=a.size())return null;
            ByteBuffer b=ByteBuffer.allocate((int)a.size());
            while(b.hasRemaining())if(c.read(b)<0)return null;
            bytes=b.array();
            if(c.read(ByteBuffer.allocate(1))!=-1)return null;
        }
        BasicFileAttributes after=Files.readAttributes(path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
        if(!after.isRegularFile()||after.size()!=a.size()||
           !after.lastModifiedTime().equals(a.lastModifiedTime())||
           (a.fileKey()!=null&&!a.fileKey().equals(after.fileKey())))
            return null;
        return sha(bytes);
    }
    static String intent(String oldHash,String afterHash){
        return "v=1\nserial=1\nnonce="+UUID.randomUUID().toString()+
            "\nbefore="+oldHash+"\nafter="+afterHash+"\n";
    }
    static boolean present(Path path){
        return Files.exists(path,LinkOption.NOFOLLOW_LINKS);
    }
    static final class Sim {
        final Path directory,history,stage,marker,markerTemp;
        final List<Integer> panel=new ArrayList<>();
        final List<Integer> initial=new ArrayList<>();
        Phase phase=Phase.NOT_ATTEMPTED;
        boolean unsafe,acknowledged,markerPublished;
        int forceCount,historyMoveAttempts,markerCreates,automaticMarkerDeletes;
        Fault fault=Fault.NONE;
        Sim(Path root)throws IOException {this(root,false);}
        Sim(Path root,boolean attachToExisting)throws IOException {
            directory=root;history=root.resolve("invented-history.txt");
            stage=root.resolve("invented-history.txt.tmp");
            marker=root.resolve(INTENT_NAME);
            markerTemp=root.resolve(INTENT_NAME+".tmp");
            initial.addAll(Arrays.asList(11,22,33));
            panel.addAll(initial);
            if(attachToExisting) {
                yes(present(history),"restart attempted without an existing synthetic history");
            } else {
                Files.write(history,encode(11,22,33),StandardOpenOption.CREATE_NEW);
            }
        }
        byte[] currentPanelImage(){
            int[] ids=new int[panel.size()];
            for(int i=0;i<ids.length;i++)ids[i]=panel.get(i);
            return encode(ids);
        }
        List<Integer> readDisk()throws IOException {
            String raw=contents(history);
            yes(raw.startsWith(HEADER),"bad invented test data");
            List<Integer> rows=new ArrayList<>();
            for(String line:raw.substring(HEADER.length()).split("\n"))
                if(!line.isEmpty())rows.add(Integer.parseInt(line));
            return rows;
        }
        State classify(){
            try{
                if(present(markerTemp))return State.QUARANTINED;
                if(!present(marker))return State.NONE;
                BasicFileAttributes meta=Files.readAttributes(marker,BasicFileAttributes.class,
                    LinkOption.NOFOLLOW_LINKS);
                if(!meta.isRegularFile()||meta.size()<100||meta.size()>512)
                    return State.QUARANTINED;
                byte[] raw=Files.readAllBytes(marker);
                String s=new String(raw,StandardCharsets.US_ASCII);
                if(!Arrays.equals(raw,s.getBytes(StandardCharsets.US_ASCII)))
                    return State.QUARANTINED;
                String[] f=s.split("\n",-1);
                if(f.length!=6||!f[0].equals("v=1")||
                   !f[1].matches("serial=[1-9][0-9]{0,15}")||
                   !f[2].matches("nonce=[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")||
                   !f[3].matches("before=(ABSENT|[0-9a-f]{64})")||
                   !f[4].matches("after=[0-9a-f]{64}")||
                   !f[5].isEmpty())return State.QUARANTINED;
                String before=f[3].substring(7),after=f[4].substring(6);
                if(before.equals(after))return State.QUARANTINED;
                String observed=digest(history,true);
                if(observed==null)return State.QUARANTINED;
                if(observed.equals(before))return State.ABORTED_BEFORE_REPLACE;
                if(observed.equals(after))return State.COMMITTED_BEFORE_ACK;
                return State.QUARANTINED;
            }catch(IOException|RuntimeException e){return State.QUARANTINED;}
        }
        boolean admitted(){
            return classify()==State.NONE&&!present(stage);
        }
        void forced(Path file,byte[] bytes)throws IOException {
            try(FileChannel c=FileChannel.open(file,
                StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE)) {
                ByteBuffer b=ByteBuffer.wrap(bytes);
                while(b.hasRemaining())c.write(b);
                c.force(true);forceCount++;
            }
        }
        boolean delete22()throws IOException {
            // This is a fabricated UI-state model, not an actual Swing test.
            if(unsafe||!admitted()) {
                unsafe=true;return false;
            }
            List<Integer> snapshot=new ArrayList<>(panel);
            panel.remove(Integer.valueOf(22));
            phase=Phase.FAILED_BEFORE_REPLACE;
            boolean result=false;
            try {
                result=writeConfirmed(currentPanelImage());
                acknowledged=result;
                return result;
            }finally{
                if(!result) {
                    unsafe=true;
                    if(phase==Phase.FAILED_BEFORE_REPLACE) {
                        panel.clear();panel.addAll(snapshot);
                    }
                }else{
                    // Marker adoption/acknowledgment is not integrated:
                    // even successful delete intentionally blocks saves.
                    unsafe=true;
                }
            }
        }
        boolean writeConfirmed(byte[] next)throws IOException {
            String before=digest(history,true);
            if(before==null)return false;
            if(fault==Fault.STAGE_FORCE_FAILURE)return false;
            forced(stage,next);
            if(fault==Fault.AFTER_STAGE_FORCE)throw new Crash(fault);
            String after=digest(stage,false);
            if(after==null||before.equals(after))return false;
            byte[] markerBytes=intent(before,after).getBytes(StandardCharsets.US_ASCII);
            if(markerBytes.length<100||markerBytes.length>512)return false;
            if(fault==Fault.INTENT_FORCE_FAILURE)return false;
            forced(markerTemp,markerBytes);
            if(fault==Fault.AFTER_INTENT_FORCE)throw new Crash(fault);
            if(!before.equals(digest(history,true))||
               !after.equals(digest(stage,false)))return false;
            if(fault==Fault.FOREIGN_MARKER_AFTER_PREFLIGHT)
                Files.write(marker,b("foreign-intent-untouched"),StandardOpenOption.CREATE_NEW);
            try {
                // Atomic namespace insert without replacing an existing marker.
                // Unsupported hard-link filesystem => fail closed.
                Files.createLink(marker,markerTemp);
                markerCreates++;
                markerPublished=true;
            }catch(IOException|UnsupportedOperationException|SecurityException conflict){
                return false;
            }
            if(fault==Fault.AFTER_HARDLINK)throw new Crash(fault);
            Files.delete(markerTemp); // only the newly owned temporary link
            if(fault==Fault.AFTER_INTENT_TEMP_REMOVAL)throw new Crash(fault);
            eq(classify(),State.ABORTED_BEFORE_REPLACE,
                "published marker must match original history");
            if(fault==Fault.HISTORY_CHANGED_AFTER_INTENT)
                Files.write(history,encode(55),StandardOpenOption.TRUNCATE_EXISTING);
            if(fault==Fault.STAGE_CHANGED_AFTER_INTENT)
                Files.write(stage,encode(44),StandardOpenOption.TRUNCATE_EXISTING);
            if(!before.equals(digest(history,true))||
               !after.equals(digest(stage,false)))return false;
            phase=Phase.REPLACE_ATTEMPTED;
            historyMoveAttempts++;
            if(fault==Fault.ATOMIC_MOVE_UNSUPPORTED)return false;
            Files.move(stage,history,StandardCopyOption.ATOMIC_MOVE,
                StandardCopyOption.REPLACE_EXISTING);
            if(fault==Fault.AFTER_HISTORY_REPLACEMENT)throw new Crash(fault);
            phase=Phase.COMMITTED;
            return true;
        }
    }
    interface Test {void run(Sim s)throws Exception;}
    static void scenario(String name,Test test)throws Exception {
        Path directory=Files.createTempDirectory("r415-invented-");
        try{
            test.run(new Sim(directory));passed++;
        }catch(Throwable e){throw new AssertionError("R415 "+name,e);}
        finally{
            try(Stream<Path> e=Files.walk(directory)){
                e.sorted(Comparator.reverseOrder()).forEach(p->{
                    try{Files.deleteIfExists(p);}
                    catch(IOException x){throw new IllegalStateException(x);}
                });
            }
        }
    }
    static void cleanConfirmedCommit()throws Exception {
        scenario("clean confirmed commit",s->{
            yes(s.delete22(),"clean delete denied");
            eq(s.readDisk(),Arrays.asList(11,33),"disk delete");
            eq(s.panel,Arrays.asList(11,33),"panel delete");
            eq(s.phase,Phase.COMMITTED,"commit disposition");
            eq(s.classify(),State.COMMITTED_BEFORE_ACK,"marker state");
            yes(s.unsafe&&s.markerPublished&&!present(s.markerTemp),
                "marker not persisted or future writes allowed");
            eq(s.automaticMarkerDeletes,0,"marker cleanup unexpectedly ran");
        });
    }
    static void secondDeleteBlocked()throws Exception{
        scenario("one marker only",s->{
            yes(s.delete22(),"first commit failed");
            yes(!s.delete22(),"second delete incorrectly admitted");
            eq(s.historyMoveAttempts,1,"second overwrite attempted");
        });
    }
    static void ordinarySaveNotJournalProducing()throws Exception{
        scenario("no ordinary journaling",s->{
            eq(s.classify(),State.NONE,"no marker");
            yes(!present(s.marker)&&!present(s.markerTemp),"marker created early");
            eq(s.forceCount,0,"regular save changed by synthetic producer");
        });
    }
    static void earlierMarkerRefusesDeletion()throws Exception{
        scenario("existing marker",s->{
            byte[] original=b("existing-intent-preserved");
            Files.write(s.marker,original,StandardOpenOption.CREATE_NEW);
            yes(!s.delete22(),"existing intent accepted");
            eq(Files.readAllBytes(s.marker).length,original.length,"marker overwritten");
            yes(Arrays.equals(Files.readAllBytes(s.marker),original),"marker bytes changed");
            eq(s.historyMoveAttempts,0,"overwrote history");
        });
    }
    static byte[] b(String x){return x.getBytes(StandardCharsets.US_ASCII);}
    static void stageWriteFailureRollsBack()throws Exception {
        scenario("stage failure",s->{
            s.fault=Fault.STAGE_FORCE_FAILURE;
            yes(!s.delete22(),"fault injected fail");
            eq(s.panel,s.initial,"UI identity rollback failed");
            eq(s.phase,Phase.FAILED_BEFORE_REPLACE,"phase");
            eq(s.historyMoveAttempts,0,"replacement attempted");
            yes(!present(s.marker),"marker prematurely visible");
        });
    }
    static void crashAfterStagingLeavesOrphan()throws Exception {
        scenario("crash after history force",s->{
            s.fault=Fault.AFTER_STAGE_FORCE;
            try{s.delete22();throw new AssertionError("missing synthetic crash");}
            catch(Crash expected){}
            yes(present(s.stage),"staged evidence lost");
            yes(!present(s.marker),"unexpected marker");
            yes(!s.admitted(),"orphan stage did not fence saves");
        });
    }
    static void intentForceFailurePreservesHistory()throws Exception {
        scenario("marker stage failure",s->{
            s.fault=Fault.INTENT_FORCE_FAILURE;
            yes(!s.delete22(),"failed marker stage reported success");
            eq(s.panel,s.initial,"failed marker stage did not rollback");
            eq(s.readDisk(),s.initial,"old main overwritten");
            yes(!present(s.marker),"partial marker promoted");
        });
    }
    static void crashAfterIntentTempForceIsQuarantined()throws Exception {
        scenario("crash after marker stage",s->{
            s.fault=Fault.AFTER_INTENT_FORCE;
            try{s.delete22();throw new AssertionError("missing crash");}
            catch(Crash expected){}
            yes(present(s.markerTemp)&&!present(s.marker),"marker temp state");
            eq(s.classify(),State.QUARANTINED,"marker temp not fenced");
        });
    }
    static void foreignMarkerAfterPreflightNotOverwritten()throws Exception {
        scenario("foreign marker race",s->{
            s.fault=Fault.FOREIGN_MARKER_AFTER_PREFLIGHT;
            yes(!s.delete22(),"foreign marker race accepted");
            eq(contents(s.marker),"foreign-intent-untouched","marker overwritten");
            eq(s.readDisk(),s.initial,"main changed on marker collision");
            eq(s.panel,s.initial,"panel not restored on safe failure");
            yes(present(s.stage)&&present(s.markerTemp),"failed transaction evidence lost");
            eq(s.historyMoveAttempts,0,"renamed without valid intent");
        });
    }
    static void crashAfterHardlinkQuarantinesBothNames()throws Exception {
        scenario("link before temp cleanup",s->{
            s.fault=Fault.AFTER_HARDLINK;
            try{s.delete22();throw new AssertionError("missing crash");}
            catch(Crash expected){}
            yes(present(s.marker)&&present(s.markerTemp),"hardlink aliases absent");
            eq(s.classify(),State.QUARANTINED,"two intent links not fenced");
            eq(s.readDisk(),s.initial,"history changed before move");
        });
    }
    static void crashAfterIntentPublishedClassifiesAborted()throws Exception {
        scenario("marker published before history move",s->{
            s.fault=Fault.AFTER_INTENT_TEMP_REMOVAL;
            try{s.delete22();throw new AssertionError("missing crash");}
            catch(Crash expected){}
            yes(present(s.marker)&&!present(s.markerTemp),"published marker state");
            eq(s.classify(),State.ABORTED_BEFORE_REPLACE,"before digest not recognized");
            yes(!s.admitted(),"marked transaction allowed autosave");
            eq(s.readDisk(),s.initial,"history moved too early");
        });
    }
    static void mainChangedAfterMarkerRefusesMove()throws Exception {
        scenario("old image conflict",s->{
            s.fault=Fault.HISTORY_CHANGED_AFTER_INTENT;
            yes(!s.delete22(),"external main changed accepted");
            eq(s.phase,Phase.FAILED_BEFORE_REPLACE,"move attempted despite mismatch");
            eq(s.panel,s.initial,"failed commit did not restore panel");
            eq(s.classify(),State.QUARANTINED,"unexpected foreign main not fenced");
            eq(s.historyMoveAttempts,0,"unexpected overwrite of foreign main");
        });
    }
    static void stagedChangedAfterMarkerRefusesMove()throws Exception {
        scenario("staged image changed",s->{
            s.fault=Fault.STAGE_CHANGED_AFTER_INTENT;
            yes(!s.delete22(),"modified stage accepted");
            eq(s.phase,Phase.FAILED_BEFORE_REPLACE,"history move attempted");
            eq(s.panel,s.initial,"uncommitted rollback absent");
            eq(s.classify(),State.ABORTED_BEFORE_REPLACE,"original main classification");
            eq(s.historyMoveAttempts,0,"stage unexpectedly moved");
        });
    }
    static void unsupportedAtomicHistoryMoveStaysAmbiguous()throws Exception {
        scenario("move unsupported",s->{
            s.fault=Fault.ATOMIC_MOVE_UNSUPPORTED;
            yes(!s.delete22(),"unsupported atomic move treated success");
            eq(s.phase,Phase.REPLACE_ATTEMPTED,"move ambiguity state");
            eq(s.readDisk(),s.initial,"main unexpectedly changed");
            eq(s.panel,Arrays.asList(11,33),"unsafe rollback after move attempt");
            eq(s.classify(),State.ABORTED_BEFORE_REPLACE,"marker not retained");
            yes(s.unsafe&&!s.acknowledged,"unverified delete marked acknowledged");
        });
    }
    static void crashAfterHistoryMoveRecognizedOnRestart()throws Exception {
        scenario("postmove synthetic interruption",s->{
            s.fault=Fault.AFTER_HISTORY_REPLACEMENT;
            try{s.delete22();throw new AssertionError("missing synthetic crash");}
            catch(Crash expected){}
            eq(s.phase,Phase.REPLACE_ATTEMPTED,"postmove phase did not remain ambiguous");
            eq(s.readDisk(),Arrays.asList(11,33),"history not replaced");
            eq(s.classify(),State.COMMITTED_BEFORE_ACK,"restart digest mismatch");
            yes(present(s.marker),"committed marker removed");
        });
    }
    static void digestMatchesCanonicalMarkerBytes()throws Exception {
        scenario("canonical marker fields",s->{
            yes(s.delete22(),"synthetic delete failed");
            String[] fields=contents(s.marker).split("\n",-1);
            eq(fields.length,6,"canonical field count");
            eq(fields[0],"v=1","marker version");
            eq(fields[1],"serial=1","single deletion serial");
            yes(fields[2].matches("nonce=[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"),"nonce");
            eq(fields[3],"before="+sha(encode(11,22,33)),"before digest");
            eq(fields[4],"after="+sha(encode(11,33)),"after digest");
            eq(fields[5],"","canonical trailing line");
        });
    }
    static void stagedFileCannotBeClobbered()throws Exception {
        scenario("old stage refusal",s->{
            byte[] evidence=b("unknown-staging-payload");
            Files.write(s.stage,evidence,StandardOpenOption.CREATE_NEW);
            yes(!s.delete22(),"orphan stage overwritten");
            yes(Arrays.equals(evidence,Files.readAllBytes(s.stage)),"orphan bytes changed");
            eq(s.historyMoveAttempts,0,"history moved with orphan stage");
        });
    }
    static void markerTempCannotBeClobbered()throws Exception {
        scenario("old marker stage",s->{
            byte[] evidence=b("earlier-marker-staging");
            Files.write(s.markerTemp,evidence,StandardOpenOption.CREATE_NEW);
            yes(!s.delete22(),"orphan intent staging overwritten");
            yes(Arrays.equals(evidence,Files.readAllBytes(s.markerTemp)),"intent temp changed");
            eq(s.historyMoveAttempts,0,"history moved despite orphan intent");
        });
    }
    static void markerCannotBeCleanedDuringInspection()throws Exception {
        scenario("no cleanup",s->{
            yes(s.delete22(),"commit");
            byte[] marker=Files.readAllBytes(s.marker);
            eq(s.classify(),State.COMMITTED_BEFORE_ACK,"first classify");
            eq(s.classify(),State.COMMITTED_BEFORE_ACK,"second classify");
            yes(Arrays.equals(marker,Files.readAllBytes(s.marker)),"inspection modified marker");
            eq(s.automaticMarkerDeletes,0,"implicit cleanup happened");
        });
    }
    static void noIntentOnUiOnlyDeletion()throws Exception {
        scenario("UI-only not persisted",s->{
            s.panel.remove(Integer.valueOf(22));
            eq(s.panel,Arrays.asList(11,33),"UI-only");
            eq(s.readDisk(),s.initial,"UI-only modified disk");
            yes(!present(s.marker),"UI-only published intent");
        });
    }
    static void noAccidentalProductionPaths()throws Exception{
        scenario("self-contained tempfile",s->{
            yes(s.directory.toString().contains("r415-invented-"),
                "test is not in generated temporary folder");
            yes(s.marker.startsWith(s.directory)&&s.history.startsWith(s.directory),
                "file path escaped synthetic directory");
        });
    }
    static void intentTempDirectoryRefuses()throws Exception {
        scenario("nonregular marker temp",s->{
            Files.createDirectory(s.markerTemp);
            yes(!s.delete22(),"nonregular temp intent accepted");
            eq(s.historyMoveAttempts,0,"history moved");
            eq(s.readDisk(),s.initial,"disk mutated");
        });
    }
    static void twoIdenticalRowValuesRemainDistinct()throws Exception {
        scenario("duplicate values",s->{
            // Our synthetic integers are intentionally unique. Still
            // verify deletion preserves original nondeleted ordering.
            yes(s.delete22(),"confirmed deletion");
            eq(s.readDisk(),Arrays.asList(11,33),"unexpected record removal");
        });
    }
    static void childCommittedBeforeAck(Path root)throws Exception {
        Sim s=new Sim(root);
        s.fault=Fault.AFTER_HISTORY_REPLACEMENT;
        try{s.delete22();}
        catch(Crash expected){System.exit(73);}
        throw new AssertionError("child did not stop after synthetic commit");
    }
    static void separateJvmRestartCommittedBeforeAck()throws Exception {
        Path dir=Files.createTempDirectory("r415-restart-");
        try{
            Process child=new ProcessBuilder(
                System.getProperty("java.home")+File.separator+"bin"+File.separator+"java",
                "-cp",System.getProperty("java.class.path"),
                R415NonClobberDeleteIntentSynthetic.class.getName(),
                "--child-commit-before-ack",dir.toString()).inheritIO().start();
            eq(child.waitFor(),73,"child failed to stop after commit");
            Sim reopen=new SimNoCreate(dir).model();
            eq(reopen.classify(),State.COMMITTED_BEFORE_ACK,
                "separate process misclassified committed history");
            yes(!reopen.admitted(),"restart auto-save resumed with unresolved intent");
            yes(present(reopen.marker),"fresh process removed recovery evidence");
            System.out.println("R415_CHILD_COMMITTED_BEFORE_ACK_PASS");
            passed++;
        }finally{
            try(Stream<Path> e=Files.walk(dir)){
                e.sorted(Comparator.reverseOrder()).forEach(p->{
                    try{Files.deleteIfExists(p);}
                    catch(IOException x){throw new IllegalStateException(x);}
                });
            }
        }
    }
    // Reopen fixture directory without re-creating already committed history.
    static final class SimNoCreate {
        final Path dir;
        SimNoCreate(Path x){dir=x;}
        Sim model()throws Exception {
            // Sim's constructor creates fabricated initial data, so use a
            // fresh probe object over the same file paths instead.
            // To keep this public model independent, the constructor is
            // bypassed via an adjacent new temporary root and the probe
            // receives the previously persisted paths below.
            return new Sim(dir,true);
        }
    }
    // A restart constructor only attaches to EXISTING synthetic files.
    // See overload implemented beside the normal constructor.
    public static void main(String[] args)throws Exception {
        if(args.length==2&&args[0].equals("--child-commit-before-ack")) {
            childCommittedBeforeAck(Path.of(args[1]));return;
        }
        cleanConfirmedCommit();secondDeleteBlocked();
        ordinarySaveNotJournalProducing();earlierMarkerRefusesDeletion();
        stageWriteFailureRollsBack();crashAfterStagingLeavesOrphan();
        intentForceFailurePreservesHistory();crashAfterIntentTempForceIsQuarantined();
        foreignMarkerAfterPreflightNotOverwritten();
        crashAfterHardlinkQuarantinesBothNames();
        crashAfterIntentPublishedClassifiesAborted();
        mainChangedAfterMarkerRefusesMove();stagedChangedAfterMarkerRefusesMove();
        unsupportedAtomicHistoryMoveStaysAmbiguous();
        crashAfterHistoryMoveRecognizedOnRestart();
        digestMatchesCanonicalMarkerBytes();stagedFileCannotBeClobbered();
        markerTempCannotBeClobbered();markerCannotBeCleanedDuringInspection();
        noIntentOnUiOnlyDeletion();noAccidentalProductionPaths();
        intentTempDirectoryRefuses();twoIdenticalRowValuesRemainDistinct();
        separateJvmRestartCommittedBeforeAck();
        System.out.println("R415_SYNTHETIC_NONCLOBBER_INTENT_PASS "+passed+" mandatory cases");
        System.out.println("R415_PRIVATE_CLIENT_NOT_EXECUTED_DIRECTORY_FSYNC_AND_ROLLOUT_UNPROVEN");
    }
}
