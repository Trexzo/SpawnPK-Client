import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.Arrays;
import java.util.Comparator;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.stream.Stream;

/**
 * R411 standalone invented quarantine model. Reads/writes only disposable
 * temporary files it creates itself; never any private game or user data.
 *
 * Its source mirrors the safety policy, not the recovered private classes.
 * No journal, cleanup/reconciliation action or power-loss proof exists here.
 */
public final class R411OrphanStageQuarantineSynthetic {
    private static int passed,optionalSymlinkSupported;
    static void yes(boolean b,String reason) {
        if(!b)throw new AssertionError(reason);
    }
    static void equal(Object actual,Object expected,String why) {
        if(!java.util.Objects.equals(actual,expected))
            throw new AssertionError(why+": "+actual+" != "+expected);
    }
    static void await(CountDownLatch x,String reason) {
        try {yes(x.await(4,TimeUnit.SECONDS),"timed out "+reason);}
        catch(InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new AssertionError(reason,e);
        }
    }
    static void join(Thread t,String label) {
        try {t.join(4000);}
        catch(InterruptedException e) {Thread.currentThread().interrupt();throw new AssertionError(e);}
        yes(!t.isAlive(),"thread hung: "+label);
    }
    enum State {CLEAR,ORPHAN,UNSAFE}
    interface AttrReader {
        BasicFileAttributes read(Path path) throws IOException;
    }
    interface AtomicReplace {
        void replace(Path stage,Path target) throws IOException;
    }
    static final class Model {
        final Path root,history,stage,legacy;
        AttrReader reader=(path)->Files.readAttributes(
            path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
        AtomicReplace atomic=(from,to)->Files.move(from,to,
            StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);
        Runnable beforeOpen=()->{},afterForce=()->{};
        int metadataProbes,stagePayloadOpens,automaticStageDeletions,
            writeAttempts,successfulWrites,clearRequests,legacyDeletions;
        boolean directoryFsyncProven,powerLossProven;
        Model(Path root) {
            this.root=root;
            history=root.resolve("invented-history.txt");
            stage=root.resolve("invented-history.txt.tmp");
            legacy=root.resolve("invented-retired-format.txt");
        }
        State state() {
            metadataProbes++;
            try {
                BasicFileAttributes a=reader.read(stage);
                return a.isRegularFile()?State.ORPHAN:State.UNSAFE;
            } catch(NoSuchFileException e) {
                return State.CLEAR;
            } catch(IOException|SecurityException e) {
                return State.UNSAFE;
            }
        }
        boolean refused() {return state()!=State.CLEAR;}
        boolean restore() {
            return !refused(); // no source payload parsing required for guard
        }
        boolean deleteRetired() {
            if(refused())return false;
            try {
                if(Files.deleteIfExists(legacy))legacyDeletions++;
                return true;
            }catch(IOException|SecurityException e){return false;}
        }
        boolean clear() {
            clearRequests++;
            if(refused())return false;
            try {
                Files.deleteIfExists(history);
                return true;
            } catch(IOException|SecurityException e){return false;}
        }
        boolean save(String value) {
            if(refused())return false;
            writeAttempts++;
            beforeOpen.run();
            byte[] payload=("invented-v1\n"+value+"\n")
                .getBytes(StandardCharsets.US_ASCII);
            try(FileChannel channel=FileChannel.open(stage,
                    StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE)) {
                ByteBuffer data=ByteBuffer.wrap(payload);
                while(data.hasRemaining())channel.write(data);
                channel.force(true);
            }catch(IOException|SecurityException e){return false;}
            afterForce.run();
            try {
                atomic.replace(stage,history);
                successfulWrites++;
                return true;
            }catch(IOException|SecurityException e){return false;}
        }
        void seed(String text)throws IOException {
            Files.write(history,("invented-v1\n"+text+"\n")
                .getBytes(StandardCharsets.US_ASCII),StandardOpenOption.CREATE_NEW);
        }
        byte[] mainBytes()throws IOException {
            return Files.exists(history)?Files.readAllBytes(history):new byte[0];
        }
    }
    interface Scenario {void run(Model model)throws Exception;}
    static void scenario(String name,Scenario run)throws Exception {
        Path path=Files.createTempDirectory("r411-public-only-");
        try {
            run.run(new Model(path));
            passed++;
        } catch(Throwable e) {
            throw new AssertionError("R411 synthetic "+name,e);
        } finally {
            try(Stream<Path> entries=Files.walk(path)) {
                entries.sorted(Comparator.reverseOrder()).forEach(x->{
                    try{Files.deleteIfExists(x);}
                    catch(IOException e){throw new IllegalStateException("cleanup of invented fixture",e);}
                });
            }
        }
    }
    static byte[] arbitraryEvidence() {
        return new byte[]{0,1,2,3,4,5,(byte)0xff};
    }
    static void absentStageIsClean()throws Exception {
        scenario("clean",m->{
            equal(m.state(),State.CLEAR,"no stage");
            yes(m.restore(),"restore denied");
            yes(m.deleteRetired(),"legacy cleanup denied");
            yes(m.clear(),"empty clear denied");
            equal(m.stagePayloadOpens,0,"stage read");
        });
    }
    static void existingRegularStageIsOrphan()throws Exception {
        scenario("regular stage",m->{
            Files.write(m.stage,arbitraryEvidence(),StandardOpenOption.CREATE_NEW);
            equal(m.state(),State.ORPHAN,"regular staged file");
            equal(m.stagePayloadOpens,0,"probe read content");
        });
    }
    static void directoryStageIsUnsafe()throws Exception {
        scenario("directory node",m->{
            Files.createDirectory(m.stage);
            equal(m.state(),State.UNSAFE,"directory stage");
            yes(!m.restore(),"directory incorrectly trusted");
        });
    }
    static void unexpectedAttributesReadFailureIsUnsafe()throws Exception {
        scenario("io failure",m->{
            m.reader=path->{throw new IOException("synthetic metadata failure");};
            equal(m.state(),State.UNSAFE,"unreadable stage treated absent");
            yes(!m.save("new"),"unreadable stage accepted write");
            yes(!m.clear(),"unreadable stage accepted delete");
        });
    }
    static void metadataPermissionDeniedIsUnsafe()throws Exception {
        scenario("security",m->{
            m.reader=path->{throw new SecurityException("synthetic deny");};
            equal(m.state(),State.UNSAFE,"security failure trusted");
            yes(!m.restore()&&!m.deleteRetired(),"security failure not fenced");
        });
    }
    static void noSuchFileMeansClear()throws Exception {
        scenario("missing",m->{
            m.reader=path->{throw new NoSuchFileException(path.toString());};
            equal(m.state(),State.CLEAR,"missing stage not clean");
        });
    }
    static void randomMalformedStageNotParsed()throws Exception {
        scenario("unreadable evidence body",m->{
            byte[] bits=arbitraryEvidence();
            Files.write(m.stage,bits,StandardOpenOption.CREATE_NEW);
            equal(m.state(),State.ORPHAN,"malformed stage content");
            yes(Arrays.equals(bits,Files.readAllBytes(m.stage)),"probe changed stage");
            equal(m.stagePayloadOpens,0,"payload opened");
        });
    }
    static void orphanBlocksStartupWithMain()throws Exception {
        scenario("main plus stage",m->{
            m.seed("old");byte[] before=m.mainBytes();
            Files.write(m.stage,arbitraryEvidence(),StandardOpenOption.CREATE_NEW);
            yes(!m.restore(),"startup accepted unresolved stage");
            yes(Arrays.equals(before,m.mainBytes()),"main changed");
            yes(Files.exists(m.stage),"stage deleted");
        });
    }
    static void orphanBlocksStartupWithoutMain()throws Exception {
        scenario("stage only",m->{
            Files.write(m.stage,arbitraryEvidence(),StandardOpenOption.CREATE_NEW);
            yes(!m.restore(),"stage-only started with empty history");
            yes(!Files.exists(m.history),"history created");
        });
    }
    static void orphanBlocksSaveWithoutChangingOldMain()throws Exception {
        scenario("save refused",m->{
            m.seed("old");byte[] previous=m.mainBytes();
            byte[] tmp=arbitraryEvidence();
            Files.write(m.stage,tmp,StandardOpenOption.CREATE_NEW);
            yes(!m.save("next"),"orphan was truncated");
            yes(Arrays.equals(previous,m.mainBytes()),"old file changed");
            yes(Arrays.equals(tmp,Files.readAllBytes(m.stage)),"stage overwritten");
            equal(m.writeAttempts,0,"payload writer opened");
        });
    }
    static void orphanBlocksClearAllAndPreservesBothFiles()throws Exception {
        scenario("clear refused",m->{
            m.seed("old");byte[] old=m.mainBytes();
            byte[] tmp=arbitraryEvidence();
            Files.write(m.stage,tmp,StandardOpenOption.CREATE_NEW);
            yes(!m.clear(),"unsafe clear reported success");
            yes(Arrays.equals(old,m.mainBytes()),"main history erased");
            yes(Arrays.equals(tmp,Files.readAllBytes(m.stage)),"stage erased");
        });
    }
    static void orphanBlocksLegacyCleanup()throws Exception {
        scenario("retired cleanup",m->{
            byte[] legacy=new byte[]{21,22};
            Files.write(m.legacy,legacy,StandardOpenOption.CREATE_NEW);
            Files.write(m.stage,arbitraryEvidence(),StandardOpenOption.CREATE_NEW);
            yes(!m.deleteRetired(),"deleted old format while unresolved stage");
            yes(Arrays.equals(legacy,Files.readAllBytes(m.legacy)),"retired evidence lost");
        });
    }
    static void unknownNodeBlocksClearAndLegacyCleanup()throws Exception {
        scenario("unknown stage",m->{
            m.seed("old");byte[] orig=m.mainBytes();
            Files.createDirectory(m.stage);
            yes(!m.clear(),"removed main with unsafe stage");
            yes(!m.deleteRetired(),"cleanup allowed");
            yes(Arrays.equals(orig,m.mainBytes()),"main changed");
        });
    }
    static void secondStartupStillRefusesWithoutManualResolution()throws Exception {
        scenario("reload",m->{
            m.seed("old");
            Files.write(m.stage,arbitraryEvidence(),StandardOpenOption.CREATE_NEW);
            Model reopened=new Model(m.root);
            yes(!m.restore()&&!reopened.restore(),"restart automatically trusted stage");
            yes(Files.exists(m.stage),"auto recovered stage");
        });
    }
    static void normalSaveLeavesNoOrphanStage()throws Exception {
        scenario("normal save",m->{
            m.seed("old");
            yes(m.save("new"),"ordinary synthetic save failed");
            equal(m.state(),State.CLEAR,"post-replace stage persists");
            equal(new String(m.mainBytes(),StandardCharsets.US_ASCII),
                "invented-v1\nnew\n","main contents");
        });
    }
    static void createNewDefeatsRaceWithStageAppear()throws Exception {
        scenario("CREATE_NEW race",m->{
            m.seed("old");byte[] before=m.mainBytes();
            byte[] evidence=arbitraryEvidence();
            m.beforeOpen=()->{
                try{Files.write(m.stage,evidence,StandardOpenOption.CREATE_NEW);}
                catch(IOException e){throw new RuntimeException(e);}
            };
            yes(!m.save("new"),"CREATE_NEW overwrote raced stage");
            yes(Arrays.equals(before,m.mainBytes()),"main changed after race");
            yes(Arrays.equals(evidence,Files.readAllBytes(m.stage)),
                "raced stage destroyed");
            equal(m.successfulWrites,0,"false commit receipt");
        });
    }
    static void failedAtomicMoveLeavesStageForRecovery()throws Exception {
        scenario("failed replacement",m->{
            m.seed("old");byte[] before=m.mainBytes();
            m.atomic=(a,b)->{throw new AtomicMoveNotSupportedException(
                a.toString(),b.toString(),"invented unsupported");};
            yes(!m.save("new"),"unsupported atomic write marked success");
            equal(m.state(),State.ORPHAN,"failed commit lost stage");
            yes(Arrays.equals(before,m.mainBytes()),"main changed");
            yes(!m.save("again"),"retry clobbered unresolved evidence");
        });
    }
    static void noAutomaticStageDeletionOnAnyRefusal()throws Exception {
        scenario("no delete",m->{
            Files.write(m.stage,arbitraryEvidence(),StandardOpenOption.CREATE_NEW);
            m.restore();m.save("new");m.clear();m.deleteRetired();
            equal(m.automaticStageDeletions,0,"automatic stage deletion");
            yes(Files.exists(m.stage),"stage disappeared");
        });
    }
    static void metadataProbeDoesNotNeedMainHistory()throws Exception {
        scenario("probe alone",m->{
            equal(m.state(),State.CLEAR,"no stage");
            yes(!Files.exists(m.history),"probe created history");
            equal(m.stagePayloadOpens,0,"stage bytes opened");
        });
    }
    static void manualExternalResolutionReopensFutureSaves()throws Exception {
        scenario("external action only",m->{
            m.seed("old");
            Files.write(m.stage,arbitraryEvidence(),StandardOpenOption.CREATE_NEW);
            yes(!m.save("new"),"unsafe save allowed");
            // This deliberate synthetic test action is NOT performed
            // by the model's restore/save/clear/cleanup methods.
            Files.delete(m.stage);
            equal(m.state(),State.CLEAR,"external resolution not seen");
            yes(m.save("new"),"normal saving stayed blocked after manual resolution");
            equal(new String(m.mainBytes(),StandardCharsets.US_ASCII),
                "invented-v1\nnew\n","main after manual resolution");
        });
    }
    static void inFlightStageCausesSecondWriterToRefuse()throws Exception {
        scenario("concurrent instance",m->{
            m.seed("old");
            CountDownLatch ready=new CountDownLatch(1),release=new CountDownLatch(1);
            AtomicBoolean committed=new AtomicBoolean(false);
            m.afterForce=()->{ready.countDown();await(release,"release first writer");};
            Thread first=new Thread(()->committed.set(m.save("first")),
                "invented-first-writer");
            first.setDaemon(true);first.start();
            await(ready,"first forced stage");
            Model other=new Model(m.root);
            yes(!other.save("second"),"second writer overwrote first stage");
            equal(other.state(),State.ORPHAN,"active stage not recognized");
            release.countDown();join(first,"first write");
            yes(committed.get(),"first writer was lost");
            equal(new String(m.mainBytes(),StandardCharsets.US_ASCII),
                "invented-v1\nfirst\n","first writer contents changed");
        });
    }
    static void optionalRealSymlinkNoFollow()throws Exception {
        // Symlink permissions vary (notably on Windows). An unsupported
        // environment is printed explicitly rather than counted as a
        // successful symlink test.
        Path dir=Files.createTempDirectory("r411-optional-link-");
        try {
            Model m=new Model(dir);
            Path outside=dir.resolve("unrelated-file.txt");
            Files.write(outside,new byte[]{5},StandardOpenOption.CREATE_NEW);
            try {
                Files.createSymbolicLink(m.stage,outside.getFileName());
                equal(m.state(),State.UNSAFE,"symlink followed as regular file");
                yes(!m.clear(),"symlink allowed Clear all");
                optionalSymlinkSupported++;
            } catch(UnsupportedOperationException|SecurityException|IOException unsupported) {
                System.out.println("R411_OPTIONAL_SYMLINK_TEST_UNSUPPORTED");
            }
        }finally {
            try(Stream<Path> entries=Files.walk(dir)) {
                entries.sorted(Comparator.reverseOrder()).forEach(x->{
                    try{Files.deleteIfExists(x);}
                    catch(IOException e){throw new IllegalStateException(e);}
                });
            }
        }
    }
    public static void main(String[] args)throws Exception {
        absentStageIsClean();
        existingRegularStageIsOrphan();
        directoryStageIsUnsafe();
        unexpectedAttributesReadFailureIsUnsafe();
        metadataPermissionDeniedIsUnsafe();
        noSuchFileMeansClear();
        randomMalformedStageNotParsed();
        orphanBlocksStartupWithMain();
        orphanBlocksStartupWithoutMain();
        orphanBlocksSaveWithoutChangingOldMain();
        orphanBlocksClearAllAndPreservesBothFiles();
        orphanBlocksLegacyCleanup();
        unknownNodeBlocksClearAndLegacyCleanup();
        secondStartupStillRefusesWithoutManualResolution();
        normalSaveLeavesNoOrphanStage();
        createNewDefeatsRaceWithStageAppear();
        failedAtomicMoveLeavesStageForRecovery();
        noAutomaticStageDeletionOnAnyRefusal();
        metadataProbeDoesNotNeedMainHistory();
        manualExternalResolutionReopensFutureSaves();
        inFlightStageCausesSecondWriterToRefuse();
        optionalRealSymlinkNoFollow();
        System.out.println("R411_SYNTHETIC_ORPHAN_STAGE_PASS "+passed+" mandatory cases");
        System.out.println("R411_OPTIONAL_SYMLINK_VERIFIED "+optionalSymlinkSupported);
        System.out.println("R411_REAL_CLIENT_AND_POWER_LOSS_UNVERIFIED");
    }
}
