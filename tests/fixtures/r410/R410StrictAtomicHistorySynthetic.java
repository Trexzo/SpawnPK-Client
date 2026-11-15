import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.FileSystemException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;
import java.util.stream.Stream;

/**
 * R410 independent invented Java11 real-TEMP-filesystem model.
 * No private game code, history, accounts, renderer, JAR or network use.
 * File.force(true) is exercised, but is NOT proof of power-loss durability.
 */
public final class R410StrictAtomicHistorySynthetic {
    static int passed;
    static void yes(boolean value,String what) {
        if(!value)throw new AssertionError(what);
    }
    static void equal(Object got,Object wanted,String what) {
        if(!java.util.Objects.equals(got,wanted))
            throw new AssertionError(what+" got="+got+" wanted="+wanted);
    }
    static final class Evidence {
        final List<String> order=new ArrayList<>();
        int atomicAttempts,nonAtomicMoves,forcedChannels,retries,directoryForceAttempts;
        boolean directoryPowerLossDurabilityProven;
    }
    interface MoveOp {void move(Path from,Path to) throws IOException;}
    interface Pause {void waitBetweenRetries() throws InterruptedException;}
    static final class Model {
        final Path directory,target,stage;
        final Evidence receipt=new Evidence();
        MoveOp atomicMove;
        Pause pause=()->{};
        Model(Path dir) {
            directory=dir;
            target=dir.resolve("invented-history.txt");
            stage=dir.resolve("invented-history.txt.tmp");
            atomicMove=(a,b)->Files.move(a,b,
                StandardCopyOption.REPLACE_EXISTING,
                StandardCopyOption.ATOMIC_MOVE);
        }
        static byte[] encode(Integer... values) {
            StringBuilder text=new StringBuilder("synthetic-v1\n");
            for(Integer number:values) {
                if(number==null||number<0)throw new IllegalArgumentException("fake ID");
                text.append(number).append('\n');
            }
            return text.toString().getBytes(StandardCharsets.US_ASCII);
        }
        void initialize(Integer... values) throws IOException {
            if(Files.exists(target)||Files.exists(stage))
                throw new IllegalStateException("already initialized");
            Files.write(target,encode(values),StandardOpenOption.CREATE_NEW);
        }
        String disk() throws IOException {
            if(!Files.exists(target))return "ABSENT";
            return new String(Files.readAllBytes(target),StandardCharsets.US_ASCII);
        }
        boolean save(Integer... values) {
            byte[] body=encode(values);
            try(FileChannel chan=FileChannel.open(stage,
                    StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE)) {
                receipt.order.add("stage-open");
                ByteBuffer buf=ByteBuffer.wrap(body);
                while(buf.hasRemaining())chan.write(buf);
                receipt.order.add("stage-write");
                chan.force(true);
                receipt.forcedChannels++;
                receipt.order.add("stage-force");
            }catch(IOException e) {
                receipt.order.add("stage-refused");
                return false;
            }
            try {
                moveStrict(stage,target);
                receipt.order.add("committed");
                return true;
            }catch(IOException e) {
                receipt.order.add("move-refused");
                return false;
            }
        }
        void moveStrict(Path from,Path to)throws IOException {
            if(!from.toFile().getCanonicalFile().getParentFile().equals(
                 to.toFile().getCanonicalFile().getParentFile()))
                throw new IOException("not the same directory");
            receipt.order.add("same-directory");
            for(int attempt=1;;attempt++) {
                try {
                    receipt.atomicAttempts++;
                    receipt.order.add("atomic-attempt");
                    atomicMove.move(from,to);
                    return;
                }catch(AtomicMoveNotSupportedException noAtomic) {
                    receipt.order.add("atomic-unsupported");
                    throw noAtomic;
                }catch(FileSystemException lock) {
                    if(attempt>=5) {
                        receipt.order.add("retry-exhausted");
                        throw lock;
                    }
                    receipt.retries++;
                    try {pause.waitBetweenRetries();}
                    catch(InterruptedException interrupted) {
                        Thread.currentThread().interrupt();
                        throw new IOException("interrupted",interrupted);
                    }
                }
            }
        }
        void simulateLegacyPriceCacheMove(Path from,Path to,boolean atomicUnavailable)
                throws IOException {
            try {
                if(atomicUnavailable)
                    throw new AtomicMoveNotSupportedException(
                        from.toString(),to.toString(),"fake unsupported");
                Files.move(from,to,StandardCopyOption.REPLACE_EXISTING,
                    StandardCopyOption.ATOMIC_MOVE);
            }catch(AtomicMoveNotSupportedException e) {
                Files.move(from,to,StandardCopyOption.REPLACE_EXISTING);
                receipt.nonAtomicMoves++;
            }
        }
    }
    interface Scenario {void run(Model model)throws Exception;}
    static void caseTest(String name,Scenario task)throws Exception {
        Path directory=Files.createTempDirectory("r410-public-synthetic-");
        try {
            Model model=new Model(directory);
            task.run(model);
            passed++;
        }catch(Throwable e) {
            throw new AssertionError("R410 synthetic case "+name,e);
        }finally {
            try(Stream<Path> s=Files.walk(directory)) {
                s.sorted(Comparator.reverseOrder()).forEach(x->{
                    try{Files.deleteIfExists(x);}
                    catch(IOException e){throw new IllegalStateException(e);}
                });
            }
        }
    }
    static void testFirstCreation()throws Exception {
        caseTest("first-create",m->{
            yes(m.save(1,2),"first save rejected");
            equal(m.disk(),"synthetic-v1\n1\n2\n","first file contents");
            yes(!Files.exists(m.stage),"stage not renamed");
        });
    }
    static void testAtomicReplacement()throws Exception {
        caseTest("replace",m->{
            m.initialize(1,2,3);
            yes(m.save(1,3),"replacement failed");
            equal(m.disk(),"synthetic-v1\n1\n3\n","new contents");
            equal(m.receipt.atomicAttempts,1,"atomic move calls");
        });
    }
    static void testStageForceBeforeMove()throws Exception {
        caseTest("force-order",m->{
            yes(m.save(1),"save");
            equal(m.receipt.order,Arrays.asList("stage-open","stage-write",
                "stage-force","same-directory","atomic-attempt","committed"),
                "force-before-move order");
            equal(m.receipt.forcedChannels,1,"stage channel forced");
        });
    }
    static void testAtomicUnsupportedNoFallback()throws Exception {
        caseTest("unsupported",m->{
            m.initialize(1,2);
            m.atomicMove=(a,b)->{throw new AtomicMoveNotSupportedException(
                    a.toString(),b.toString(),"synthetic unsupported");};
            yes(!m.save(2),"non-atomic fallback was accepted");
            equal(m.disk(),"synthetic-v1\n1\n2\n","old data changed");
            yes(Files.exists(m.stage),"unexplained stage erased");
            equal(m.receipt.atomicAttempts,1,"unsupported move retried");
            equal(m.receipt.nonAtomicMoves,0,"non-atomic fallback occurred");
        });
    }
    static void testBusyRetriesAndSucceeds()throws Exception {
        caseTest("transient lock",m->{
            m.initialize(1,2);
            final int[] count={0};
            m.atomicMove=(a,b)->{
                if(++count[0]<=2)throw new FileSystemException(
                    a.toString(),b.toString(),"fake temporary lock");
                Files.move(a,b,StandardCopyOption.ATOMIC_MOVE,
                    StandardCopyOption.REPLACE_EXISTING);
            };
            yes(m.save(2),"transient lock rejected final retry");
            equal(m.receipt.atomicAttempts,3,"attempts");
            equal(m.receipt.retries,2,"retries");
            equal(m.disk(),"synthetic-v1\n2\n","committed contents");
        });
    }
    static void testBusyExhaustsFive()throws Exception {
        caseTest("five attempts",m->{
            m.initialize(1,2);
            m.atomicMove=(a,b)->{throw new FileSystemException(
                a.toString(),b.toString(),"still locked");};
            yes(!m.save(2),"exhausted lock treated as success");
            equal(m.receipt.atomicAttempts,5,"max five attempts");
            equal(m.receipt.retries,4,"four pauses");
            equal(m.disk(),"synthetic-v1\n1\n2\n","old bytes");
            yes(Files.exists(m.stage),"failed temp discarded");
        });
    }
    static void testOrphanStageCannotBeOverwritten()throws Exception {
        caseTest("orphan",m->{
            m.initialize(1);
            byte[] evidence="unexplained existing stage".getBytes(StandardCharsets.US_ASCII);
            Files.write(m.stage,evidence,StandardOpenOption.CREATE_NEW);
            yes(!m.save(3),"existing stage clobbered");
            yes(Arrays.equals(Files.readAllBytes(m.stage),evidence),
                "orphan evidence changed");
            equal(m.disk(),"synthetic-v1\n1\n","existing data changed");
            equal(m.receipt.atomicAttempts,0,"move started with orphan");
        });
    }
    static void testFailureLeavesStageNoAutomaticCleanup()throws Exception {
        caseTest("failed stage",m->{
            m.initialize(1);
            m.atomicMove=(a,b)->{throw new AtomicMoveNotSupportedException(
                a.toString(),b.toString(),"no atomic");};
            yes(!m.save(2),"expected error");
            byte[] stage=Files.readAllBytes(m.stage);
            yes(!m.save(3),"automatic clobber of failed stage");
            yes(Arrays.equals(stage,Files.readAllBytes(m.stage)),
                "staged file changed during retry");
            equal(m.disk(),"synthetic-v1\n1\n","old history");
        });
    }
    static void testDifferentDirectoryRefused()throws Exception {
        caseTest("different directory",m->{
            Path elsewhere=Files.createTempDirectory("r410-another-");
            try {
                Path foreign=elsewhere.resolve("synthetic.tmp");
                Files.write(foreign,Model.encode(4),StandardOpenOption.CREATE_NEW);
                try {m.moveStrict(foreign,m.target);
                    throw new AssertionError("cross-directory move accepted");
                }catch(IOException expected) {
                    yes(expected.getMessage().contains("same directory"),
                        "unexpected refusal reason");
                }
                equal(m.receipt.atomicAttempts,0,"move attempted across directories");
                yes(Files.exists(foreign),"foreign stage removed");
            }finally{try(Stream<Path> s=Files.walk(elsewhere)){
                s.sorted(Comparator.reverseOrder()).forEach(x->{
                    try{Files.deleteIfExists(x);}catch(IOException e){throw new IllegalStateException(e);}
                });
            }}
        });
    }
    static void testUnexpectedNonFileSystemIoRefused()throws Exception {
        caseTest("plain io error",m->{
            m.initialize(1);
            m.atomicMove=(a,b)->{throw new IOException("not file lock");};
            yes(!m.save(2),"plain error acknowledged");
            equal(m.receipt.atomicAttempts,1,"plain error retried");
            equal(m.disk(),"synthetic-v1\n1\n","old file");
        });
    }
    static void testInterruptedRetryRefused()throws Exception {
        caseTest("interrupted",m->{
            m.initialize(1);
            m.atomicMove=(a,b)->{throw new FileSystemException(
                a.toString(),b.toString(),"locked");};
            m.pause=()->{throw new InterruptedException("fake interrupt");};
            yes(!m.save(2),"interrupted worker treated as success");
            yes(Thread.interrupted(),"interrupt flag not restored");
            equal(m.receipt.atomicAttempts,1,"interrupted move retried");
            equal(m.disk(),"synthetic-v1\n1\n","old file");
        });
    }
    static void testPriceCacheLegacyFallbackRemains()throws Exception {
        caseTest("legacy cache",m->{
            Path cacheTemp=m.directory.resolve("invented-price-cache.tmp");
            Path cache=m.directory.resolve("invented-price-cache.dat");
            Files.write(cacheTemp,new byte[]{4,5,6},StandardOpenOption.CREATE_NEW);
            m.simulateLegacyPriceCacheMove(cacheTemp,cache,true);
            yes(Arrays.equals(Files.readAllBytes(cache),new byte[]{4,5,6}),
                "price cache fallback failed");
            equal(m.receipt.nonAtomicMoves,1,"legacy fallback not isolated");
            equal(m.receipt.atomicAttempts,0,"history move path incorrectly invoked");
        });
    }
    static void testNoDirectoryPowerLossGuarantee()throws Exception {
        caseTest("directory durability unproven",m->{
            yes(m.save(1),"save");
            equal(m.receipt.directoryForceAttempts,0,
                "unexpected directory flush added");
            yes(!m.receipt.directoryPowerLossDurabilityProven,
                "claimed power-loss guarantee");
        });
    }
    static void testAmbiguousPostMoveIoDoesNotClaimSuccess()throws Exception {
        caseTest("move then error ambiguous",m->{
            m.initialize(1,2);
            m.atomicMove=(a,b)->{
                Files.move(a,b,StandardCopyOption.ATOMIC_MOVE,
                    StandardCopyOption.REPLACE_EXISTING);
                throw new FileSystemException(a.toString(),b.toString(),
                    "fabricated exception after successful move");
            };
            yes(!m.save(2),"ambiguous commit incorrectly reported success");
            equal(m.disk(),"synthetic-v1\n2\n",
                "fixture should demonstrate committed bytes");
            yes(!Files.exists(m.stage),"stage should already be moved");
            // This is a deliberate outstanding reason R411 needs a journal:
            // false return does NOT prove the old file was preserved.
        });
    }
    static void testZeroItemSaveIsCanonical()throws Exception {
        caseTest("empty data",m->{
            m.initialize(1);
            yes(m.save(),"empty save");
            equal(m.disk(),"synthetic-v1\n","empty canonical history");
        });
    }
    static void testExistingTargetCannotBeTruncatedBeforeRename()throws Exception {
        caseTest("target preserved while staged",m->{
            m.initialize(1,2);
            m.atomicMove=(a,b)->{
                equal(m.disk(),"synthetic-v1\n1\n2\n",
                    "existing history truncated before move");
                Files.move(a,b,StandardCopyOption.ATOMIC_MOVE,
                    StandardCopyOption.REPLACE_EXISTING);
            };
            yes(m.save(2),"replace");
            equal(m.disk(),"synthetic-v1\n2\n","final history");
        });
    }
    static void testMissingStageCannotBecomeSuccess()throws Exception {
        caseTest("vanishing stage",m->{
            m.initialize(1);
            m.atomicMove=(a,b)->{
                Files.deleteIfExists(a);
                Files.move(a,b,StandardCopyOption.ATOMIC_MOVE,
                    StandardCopyOption.REPLACE_EXISTING);
            };
            yes(!m.save(2),"missing stage returned success");
            equal(m.disk(),"synthetic-v1\n1\n","existing file changed");
        });
    }
    static void testAtomicUnsupportedLeavesOriginalDestination()throws Exception {
        caseTest("unsupported empty target",m->{
            m.atomicMove=(a,b)->{throw new AtomicMoveNotSupportedException(
                a.toString(),b.toString(),"no atomic");};
            yes(!m.save(9),"unsupported created destination");
            equal(m.disk(),"ABSENT","unexpected destination");
            yes(Files.exists(m.stage),"stage lost");
        });
    }
    static void testManySequentialCommits()throws Exception {
        caseTest("sequential writes",m->{
            for(int i=0;i<12;i++)yes(m.save(i),"sequential stage "+i);
            equal(m.disk(),"synthetic-v1\n11\n","latest value");
            equal(m.receipt.atomicAttempts,12,"unexpected attempt count");
            equal(m.receipt.forcedChannels,12,"missing stage force");
        });
    }
    static void testUntouchedOriginalAfterPreCommitFailure()throws Exception {
        caseTest("precommit unchanged",m->{
            m.initialize(2,3);
            byte[] old=Files.readAllBytes(m.target);
            m.atomicMove=(a,b)->{throw new AtomicMoveNotSupportedException(
                a.toString(),b.toString(),"fail");};
            yes(!m.save(4),"failure");
            yes(Arrays.equals(old,Files.readAllBytes(m.target)),
                "old bytes not preserved");
        });
    }
    public static void main(String[] args)throws Exception {
        testFirstCreation();
        testAtomicReplacement();
        testStageForceBeforeMove();
        testAtomicUnsupportedNoFallback();
        testBusyRetriesAndSucceeds();
        testBusyExhaustsFive();
        testOrphanStageCannotBeOverwritten();
        testFailureLeavesStageNoAutomaticCleanup();
        testDifferentDirectoryRefused();
        testUnexpectedNonFileSystemIoRefused();
        testInterruptedRetryRefused();
        testPriceCacheLegacyFallbackRemains();
        testNoDirectoryPowerLossGuarantee();
        testAmbiguousPostMoveIoDoesNotClaimSuccess();
        testZeroItemSaveIsCanonical();
        testExistingTargetCannotBeTruncatedBeforeRename();
        testMissingStageCannotBecomeSuccess();
        testAtomicUnsupportedLeavesOriginalDestination();
        testManySequentialCommits();
        testUntouchedOriginalAfterPreCommitFailure();
        System.out.println("R410_SYNTHETIC_STRICT_HISTORY_PASS "+passed+" cases");
        System.out.println("R410_POWERLOSS_AND_REAL_CLIENT_NOT_PROVEN");
    }
}
