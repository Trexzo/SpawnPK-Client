import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.stream.Stream;

/**
 * R409 independent, invented file-backed restart-reconciliation protocol.
 * Only integer synthetic rows in self-created TEMP directories. This does
 * NOT load the private client, its JSON history, accounts, or any live data.
 *
 * Guarantees modeled: manifest-before-replace ordering, exact history hashes,
 * fail-closed ambiguous recovery, and no "queued = committed" acknowledgments.
 * NOT proven: directory fsync on Windows, whole-system power loss, real UI
 * lifecycle, interprocess writers, or integration with current history store.
 */
public final class R409DurableDeleteReconcileSynthetic {
    private static int passed;
    private static void yes(boolean b,String reason) {
        if(!b) throw new AssertionError(reason);
    }
    private static void equal(Object a,Object b,String reason) {
        if(!java.util.Objects.equals(a,b))
            throw new AssertionError(reason+" actual="+a+" wanted="+b);
    }
    private static final String ABSENT="ABSENT";
    private static final String HEADER="synthetic-history-v1\n";
    private static final int MAX_MANIFEST_BYTES=512;
    private static final int MAX_HISTORY_BYTES=1024*1024;
    enum CrashPoint {
        NONE, AFTER_PREPARED_INTENT_TMP, AFTER_INTENT_ATOMIC_MOVE,
        AFTER_HISTORY_TMP_FSYNC, AFTER_HISTORY_ATOMIC_MOVE,
        AFTER_EDT_SUCCESS_BEFORE_JOURNAL_CLEANUP
    }
    enum Result {
        CLEAN, ABORTED_BEFORE_REPLACE, COMMITTED_BEFORE_ACK,
        QUARANTINED
    }
    static final class SimulatedCrash extends RuntimeException {
        SimulatedCrash(CrashPoint location) {super(location.name());}
    }
    static final class Intent {
        final long serial;
        final String before,after;
        Intent(long serial,String before,String after) {
            this.serial=serial;this.before=before;this.after=after;
        }
        String encode() {
            return "v=1\nserial="+serial+"\nbefore="+before+"\nafter="+after+"\n";
        }
        static Intent decode(byte[] bytes) {
            if(bytes.length>MAX_MANIFEST_BYTES||bytes.length<100)
                throw new IllegalArgumentException("manifest length");
            String raw=new String(bytes,StandardCharsets.US_ASCII);
            String[] fields=raw.split("\n",-1);
            if(fields.length!=5||!fields[0].equals("v=1")||
               !fields[1].matches("serial=[1-9][0-9]{0,15}")||
               !fields[2].matches("before=(ABSENT|[0-9a-f]{64})")||
               !fields[3].matches("after=[0-9a-f]{64}")||
               !fields[4].isEmpty())
                throw new IllegalArgumentException("manifest grammar");
            long serial=Long.parseLong(fields[1].substring(7));
            Intent i=new Intent(serial,fields[2].substring(7),
                fields[3].substring(6));
            if(i.before.equals(i.after)||!raw.equals(i.encode()))
                throw new IllegalArgumentException("ambiguous or noncanonical manifest");
            return i;
        }
    }
    static final class Recovery {
        final Result result;
        final List<Integer> fileRows;
        final Intent intent;
        Recovery(Result result,List<Integer> rows,Intent intent) {
            this.result=result;
            this.fileRows=rows;
            this.intent=intent;
        }
        boolean autoWriteAllowed() {return result==Result.CLEAN;}
    }
    static final class Store {
        final Path directory,history,intent,intentTmp,historyTmp;
        final Object fileGate=new Object();
        boolean everyDirectoryForceSucceeded=true;
        int forcedFiles,attemptedDirectoryForces;
        long serial=1;
        Store(Path path) throws IOException {
            if(!Files.isDirectory(path)||Files.isSymbolicLink(path))
                throw new IllegalArgumentException("only isolated synthetic directory");
            directory=path;
            history=path.resolve("invented-history.txt");
            intent=path.resolve("invented-delete.intent");
            intentTmp=path.resolve("invented-delete.intent.tmp");
            historyTmp=path.resolve("invented-history.txt.tmp");
        }
        static String sha(byte[] bytes) {
            try {
                byte[] result=MessageDigest.getInstance("SHA-256").digest(bytes);
                StringBuilder b=new StringBuilder();
                for(byte x:result)b.append(String.format("%02x",x&255));
                return b.toString();
            } catch(NoSuchAlgorithmException e){throw new AssertionError(e);}
        }
        String currentHash() throws IOException {
            return Files.exists(history)?sha(Files.readAllBytes(history)):ABSENT;
        }
        static byte[] encode(List<Integer> values) {
            StringBuilder out=new StringBuilder(HEADER);
            for(Integer number:values) {
                if(number==null||number<0||number>999999)
                    throw new IllegalArgumentException("synthetic row");
                out.append(number).append('\n');
            }
            return out.toString().getBytes(StandardCharsets.US_ASCII);
        }
        static List<Integer> parse(byte[] bytes) {
            if(bytes.length>MAX_HISTORY_BYTES)
                throw new IllegalArgumentException("oversized history");
            String raw=new String(bytes,StandardCharsets.US_ASCII);
            if(!raw.startsWith(HEADER))throw new IllegalArgumentException("history header");
            String body=raw.substring(HEADER.length());
            if(body.isEmpty())return new ArrayList<>();
            List<Integer> rows=new ArrayList<>();
            for(String line:body.split("\n",-1)) {
                if(line.isEmpty())continue;
                if(!line.matches("(0|[1-9][0-9]{0,5})"))
                    throw new IllegalArgumentException("bad row");
                rows.add(Integer.parseInt(line));
            }
            if(!Arrays.equals(encode(rows),bytes))
                throw new IllegalArgumentException("noncanonical history");
            return rows;
        }
        List<Integer> loadRows() throws IOException {
            if(!Files.exists(history))return new ArrayList<>();
            return parse(Files.readAllBytes(history));
        }
        void forceFile(Path file,byte[] contents) throws IOException {
            // Required source is invented and validated by length and names.
            try(FileChannel channel=FileChannel.open(file,
                  StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE)) {
                ByteBuffer buf=ByteBuffer.wrap(contents);
                while(buf.hasRemaining())channel.write(buf);
                channel.force(true);
                forcedFiles++;
            }
        }
        void forceDirectoryBestEffort() {
            attemptedDirectoryForces++;
            try(FileChannel channel=FileChannel.open(directory,StandardOpenOption.READ)) {
                channel.force(true);
            }catch(IOException|UnsupportedOperationException e) {
                // Directory metadata forcing is unavailable on some
                // platforms. Never claim power-loss durability from this.
                everyDirectoryForceSucceeded=false;
            }
        }
        void replaceAtomic(Path source,Path target) throws IOException {
            try{
                Files.move(source,target,StandardCopyOption.ATOMIC_MOVE,
                    StandardCopyOption.REPLACE_EXISTING);
            }catch(AtomicMoveNotSupportedException e) {
                // Do NOT downgrade silently to a non-atomic replacement.
                throw new IOException("Atomic replacement unavailable",e);
            }
            forceDirectoryBestEffort();
        }
        void initialize(List<Integer> rows) throws IOException {
            synchronized(fileGate) {
                if(Files.exists(history)||Files.exists(intent)||
                   Files.exists(intentTmp)||Files.exists(historyTmp))
                    throw new IllegalStateException("already initialized");
                forceFile(historyTmp,encode(rows));
                replaceAtomic(historyTmp,history);
            }
        }
        void crash(CrashPoint want,CrashPoint reached) {
            if(want==reached)throw new SimulatedCrash(reached);
        }
        Intent deleteOne(int number,CrashPoint stopAt) throws IOException {
            synchronized(fileGate) {
                Recovery before=recover();
                if(!before.autoWriteAllowed())
                    throw new IllegalStateException("unresolved prior transaction");
                List<Integer> rows=new ArrayList<>(before.fileRows);
                if(!rows.remove(Integer.valueOf(number)))
                    throw new IllegalArgumentException("synthetic row absent");
                byte[] afterBytes=encode(rows);
                String priorHash=currentHash();
                String nextHash=sha(afterBytes);
                if(priorHash.equals(nextHash))
                    throw new IllegalStateException("non-changing transaction");
                long nextSerial=serial++;
                Intent tx=new Intent(nextSerial,priorHash,nextHash);
                // PREPARE: persist complete expected before/post digests
                // before any history replacement can occur.
                forceFile(intentTmp,tx.encode().getBytes(StandardCharsets.US_ASCII));
                crash(stopAt,CrashPoint.AFTER_PREPARED_INTENT_TMP);
                replaceAtomic(intentTmp,intent);
                crash(stopAt,CrashPoint.AFTER_INTENT_ATOMIC_MOVE);
                forceFile(historyTmp,afterBytes);
                crash(stopAt,CrashPoint.AFTER_HISTORY_TMP_FSYNC);
                if(!currentHash().equals(priorHash))
                    throw new IllegalStateException("outside writer changed history");
                replaceAtomic(historyTmp,history);
                crash(stopAt,CrashPoint.AFTER_HISTORY_ATOMIC_MOVE);
                return tx;
            }
        }
        Recovery recover() throws IOException {
            synchronized(fileGate) {
                // Any orphan staging file is evidence we have not proven
                // belongs to a complete transaction: refuse automatic write.
                if(Files.exists(intentTmp)||Files.exists(historyTmp))
                    return new Recovery(Result.QUARANTINED,
                        safeRows(),null);
                final byte[] historyBytes;
                if(Files.exists(history))historyBytes=Files.readAllBytes(history);
                else historyBytes=null;
                List<Integer> parsed;
                try{
                    parsed=historyBytes==null?new ArrayList<>():parse(historyBytes);
                }catch(IllegalArgumentException e) {
                    return new Recovery(Result.QUARANTINED,new ArrayList<>(),null);
                }
                if(!Files.exists(intent))
                    return new Recovery(Result.CLEAN,parsed,null);
                Intent tx;
                try{
                    tx=Intent.decode(Files.readAllBytes(intent));
                }catch(IOException|IllegalArgumentException e) {
                    return new Recovery(Result.QUARANTINED,parsed,null);
                }
                final String actual=historyBytes==null?ABSENT:sha(historyBytes);
                if(actual.equals(tx.after))
                    return new Recovery(Result.COMMITTED_BEFORE_ACK,parsed,tx);
                if(actual.equals(tx.before))
                    return new Recovery(Result.ABORTED_BEFORE_REPLACE,parsed,tx);
                return new Recovery(Result.QUARANTINED,parsed,tx);
            }
        }
        List<Integer> safeRows() {
            try{return loadRows();}
            catch(IOException|RuntimeException e){return new ArrayList<>();}
        }
        void acknowledgeAndClean(Intent expected,CrashPoint stopAt)
                throws IOException {
            synchronized(fileGate) {
                Recovery state=recover();
                if(state.result!=Result.COMMITTED_BEFORE_ACK||
                   state.intent==null||expected==null||
                   state.intent.serial!=expected.serial||
                   !state.intent.after.equals(expected.after))
                    throw new IllegalStateException("not an authenticated commit");
                // The callback may mark a successful UI state now.
                crash(stopAt,CrashPoint.AFTER_EDT_SUCCESS_BEFORE_JOURNAL_CLEANUP);
                Files.delete(intent);
                forceDirectoryBestEffort();
            }
        }
        void reconcileAndResolve(List<Integer> adoptedUiImage) throws IOException {
            synchronized(fileGate) {
                Recovery r=recover();
                if(r.result==Result.QUARANTINED)
                    throw new IllegalStateException("unknown state requires manual recovery");
                // Startup must validate that the UI actually adopted the
                // authoritative disk image BEFORE discarding the intent.
                // It is never safe to infer UI adoption from disk alone.
                if(adoptedUiImage==null||!r.fileRows.equals(adoptedUiImage))
                    throw new IllegalStateException("UI has not adopted verified disk image");
                if(r.result==Result.CLEAN)return;
                // ABORTED means the old file survived; COMMITTED means
                // the post-image was installed before an EDT callback.
                Files.delete(intent);
                forceDirectoryBestEffort();
            }
        }
    }
    interface Scenario {void run(Store s)throws Exception;}
    static void scenario(String name,Scenario check) throws Exception {
        Path directory=Files.createTempDirectory("r409-fabricated-");
        try{
            Store s=new Store(directory);
            check.run(s);
            passed++;
        }finally{
            try(Stream<Path> all=Files.walk(directory)) {
                all.sorted(java.util.Comparator.reverseOrder()).forEach(p->{
                    try {Files.deleteIfExists(p);}
                    catch(IOException e) {throw new IllegalStateException("synthetic cleanup failed",e);}
                });
            }
        }
    }
    static Store reopened(Store first) throws IOException {
        return new Store(first.directory);
    }
    static void expectCrash(Runnable action,CrashPoint which) {
        try {
            action.run();
            throw new AssertionError("missing "+which+" failure");
        }catch(SimulatedCrash e){equal(e.getMessage(),which.name(),"crash point");}
    }
    interface IORun {void run()throws IOException;}
    static void expectedIOException(IORun op) {
        try{op.run();throw new AssertionError("must fail closed");}
        catch(IOException|IllegalStateException expected){}
    }
    static void seeded(Store s)throws IOException{s.initialize(Arrays.asList(1,2,3));}
    static void assertRows(Store s,Integer... rows)throws IOException {
        equal(s.loadRows(),Arrays.asList(rows),"stored rows");
    }
    static void cleanWithoutJournal() throws Exception {
        scenario("clean",s->{
            seeded(s);
            equal(s.recover().result,Result.CLEAN,"clean status");
            yes(s.recover().autoWriteAllowed(),"ordinary load gated");
            assertRows(s,1,2,3);
        });
    }
    static void successfulCommitRequiresExplicitAck()throws Exception {
        scenario("ack",s->{
            seeded(s);
            Intent tx=s.deleteOne(2,CrashPoint.NONE);
            Recovery r=s.recover();
            equal(r.result,Result.COMMITTED_BEFORE_ACK,"preack");
            yes(!r.autoWriteAllowed(),"unacknowledged accepted new write");
            assertRows(s,1,3);
            s.acknowledgeAndClean(tx,CrashPoint.NONE);
            equal(s.recover().result,Result.CLEAN,"ack cleanup");
        });
    }
    static void crashBeforeIntentRenameQuarantinesOrphan()throws Exception {
        scenario("before_intent",s->{
            seeded(s);
            expectCrash(()->{try{s.deleteOne(2,CrashPoint.AFTER_PREPARED_INTENT_TMP);}
                catch(IOException e){throw new RuntimeException(e);}},
                CrashPoint.AFTER_PREPARED_INTENT_TMP);
            Store b=reopened(s);
            equal(b.recover().result,Result.QUARANTINED,"orphan manifest temp");
            assertRows(b,1,2,3);
        });
    }
    static void crashAfterIntentRenameRecognizesAbort()throws Exception {
        scenario("after_intent",s->{
            seeded(s);
            expectCrash(()->{try{s.deleteOne(2,CrashPoint.AFTER_INTENT_ATOMIC_MOVE);}
                catch(IOException e){throw new RuntimeException(e);}},
                CrashPoint.AFTER_INTENT_ATOMIC_MOVE);
            Store b=reopened(s);
            equal(b.recover().result,Result.ABORTED_BEFORE_REPLACE,"abort");
            assertRows(b,1,2,3);
            b.reconcileAndResolve(b.recover().fileRows);
            equal(b.recover().result,Result.CLEAN,"abort cleanup");
        });
    }
    static void crashAfterHistoryTmpQuarantinesRatherThanDeletes()throws Exception {
        scenario("history_tmp",s->{
            seeded(s);
            expectCrash(()->{try{s.deleteOne(2,CrashPoint.AFTER_HISTORY_TMP_FSYNC);}
                catch(IOException e){throw new RuntimeException(e);}},
                CrashPoint.AFTER_HISTORY_TMP_FSYNC);
            Store b=reopened(s);
            equal(b.recover().result,Result.QUARANTINED,"orphan history temp");
            assertRows(b,1,2,3);
        });
    }
    static void crashAfterReplaceRecognizesCommit()throws Exception {
        scenario("after_replace",s->{
            seeded(s);
            expectCrash(()->{try{s.deleteOne(2,CrashPoint.AFTER_HISTORY_ATOMIC_MOVE);}
                catch(IOException e){throw new RuntimeException(e);}},
                CrashPoint.AFTER_HISTORY_ATOMIC_MOVE);
            Store b=reopened(s);
            Recovery r=b.recover();
            equal(r.result,Result.COMMITTED_BEFORE_ACK,"commit recovery");
            assertRows(b,1,3);
            yes(!r.autoWriteAllowed(),"resume autosave before reconciliation");
            b.reconcileAndResolve(b.recover().fileRows);
            equal(b.recover().result,Result.CLEAN,"post-commit resolved");
        });
    }
    static void crashAfterAckBeforeCleanupIdempotent()throws Exception {
        scenario("ack_gap",s->{
            seeded(s);
            Intent tx=s.deleteOne(2,CrashPoint.NONE);
            expectCrash(()->{try{
                s.acknowledgeAndClean(tx,CrashPoint.AFTER_EDT_SUCCESS_BEFORE_JOURNAL_CLEANUP);
            }catch(IOException e){throw new RuntimeException(e);}},
                CrashPoint.AFTER_EDT_SUCCESS_BEFORE_JOURNAL_CLEANUP);
            Store b=reopened(s);
            equal(b.recover().result,Result.COMMITTED_BEFORE_ACK,"stale sidecar");
            b.reconcileAndResolve(b.recover().fileRows);
            assertRows(b,1,3);
            equal(b.recover().result,Result.CLEAN,"ack idempotent");
        });
    }
    static void forgedHistoryHashQuarantines()throws Exception {
        scenario("tamper_history",s->{
            seeded(s);s.deleteOne(2,CrashPoint.NONE);
            Files.write(s.history,Store.encode(Arrays.asList(9,9)));
            Store b=reopened(s);
            equal(b.recover().result,Result.QUARANTINED,"unknown changed disk hash");
            expectedIOException(()->b.reconcileAndResolve(b.recover().fileRows));
        });
    }
    static void forgedManifestQuarantines()throws Exception {
        scenario("tamper_intent",s->{
            seeded(s);s.deleteOne(2,CrashPoint.NONE);
            Files.write(s.intent,"unsafe\n".getBytes(StandardCharsets.US_ASCII));
            Store b=reopened(s);
            equal(b.recover().result,Result.QUARANTINED,"invalid manifest");
            expectedIOException(()->b.reconcileAndResolve(b.recover().fileRows));
        });
    }
    static void noIntentButMalformedHistoryQuarantines()throws Exception {
        scenario("malformed",s->{
            seeded(s);
            Files.write(s.history,"malformed".getBytes(StandardCharsets.US_ASCII));
            Store b=reopened(s);
            equal(b.recover().result,Result.QUARANTINED,"unsafe old state");
        });
    }
    static void noIntentMissingHistoryIsCleanEmpty()throws Exception {
        scenario("empty",s->{
            equal(s.recover().result,Result.CLEAN,"missing data permitted");
            equal(s.loadRows(),Collections.emptyList(),"empty");
        });
    }
    static void secondDeleteRefusedUntilAck()throws Exception {
        scenario("gate",s->{
            seeded(s);Intent tx=s.deleteOne(2,CrashPoint.NONE);
            expectedIOException(()->s.deleteOne(1,CrashPoint.NONE));
            s.acknowledgeAndClean(tx,CrashPoint.NONE);
            Intent next=s.deleteOne(1,CrashPoint.NONE);
            assertRows(s,3);
            s.acknowledgeAndClean(next,CrashPoint.NONE);
            equal(s.recover().result,Result.CLEAN,"second commit clean");
        });
    }
    static void abortCanBeResolvedThenNewDeletion()throws Exception {
        scenario("abort_then_retry",s->{
            seeded(s);
            expectCrash(()->{try{s.deleteOne(2,CrashPoint.AFTER_INTENT_ATOMIC_MOVE);}
                catch(IOException e){throw new RuntimeException(e);}},
                CrashPoint.AFTER_INTENT_ATOMIC_MOVE);
            Store b=reopened(s);
            expectedIOException(()->b.deleteOne(1,CrashPoint.NONE));
            b.reconcileAndResolve(b.recover().fileRows);
            Intent newTx=b.deleteOne(1,CrashPoint.NONE);
            b.acknowledgeAndClean(newTx,CrashPoint.NONE);
            assertRows(b,2,3);
        });
    }
    static void wrongReceiptCannotDeleteJournal()throws Exception {
        scenario("wrong_ack",s->{
            seeded(s);
            Intent tx=s.deleteOne(2,CrashPoint.NONE);
            Intent wrong=new Intent(tx.serial+1,tx.before,tx.after);
            expectedIOException(()->s.acknowledgeAndClean(wrong,CrashPoint.NONE));
            equal(s.recover().result,Result.COMMITTED_BEFORE_ACK,"journal kept");
        });
    }
    static void uiAdoptionRequiredBeforeJournalDeletion()throws Exception {
        scenario("adoption_guard",s->{
            seeded(s);s.deleteOne(2,CrashPoint.NONE);
            Store b=reopened(s);
            expectedIOException(()->b.reconcileAndResolve(Arrays.asList(1,2,3)));
            equal(b.recover().result,Result.COMMITTED_BEFORE_ACK,
                "unadopted UI image discarded journal");
            b.reconcileAndResolve(Arrays.asList(1,3));
            equal(b.recover().result,Result.CLEAN,"correct adoption refused");
        });
    }
    static void missingUiAdoptionCannotResolve()throws Exception {
        scenario("null_adoption",s->{
            seeded(s);s.deleteOne(2,CrashPoint.NONE);
            expectedIOException(()->s.reconcileAndResolve(null));
            equal(s.recover().result,Result.COMMITTED_BEFORE_ACK,
                "null UI adoption discarded intent");
        });
    }
    static void rawHistoryStaysBytesAfterAbort()throws Exception {
        scenario("preserve_before",s->{
            seeded(s);
            byte[] original=Files.readAllBytes(s.history);
            expectCrash(()->{try{s.deleteOne(2,CrashPoint.AFTER_INTENT_ATOMIC_MOVE);}
                catch(IOException e){throw new RuntimeException(e);}},
                CrashPoint.AFTER_INTENT_ATOMIC_MOVE);
            yes(Arrays.equals(original,Files.readAllBytes(s.history)),
                "abort changed history bytes");
        });
    }
    static void postCommitHistoryExactHash()throws Exception {
        scenario("post_digest",s->{
            seeded(s);Intent tx=s.deleteOne(2,CrashPoint.NONE);
            equal(tx.after,Store.sha(Files.readAllBytes(s.history)),"post hash");
            yes(!tx.before.equals(tx.after),"identical before/after");
        });
    }
    static void duplicateRowDeletesOneOccurrence()throws Exception {
        scenario("duplicate",s->{
            s.initialize(Arrays.asList(1,1,2));
            Intent tx=s.deleteOne(1,CrashPoint.NONE);
            assertRows(s,1,2);
            s.acknowledgeAndClean(tx,CrashPoint.NONE);
        });
    }
    static void missingRowCannotWriteJournal()throws Exception {
        scenario("unknown_row",s->{
            seeded(s);
            try{s.deleteOne(77,CrashPoint.NONE);throw new AssertionError("missing row");}
            catch(IllegalArgumentException expected){}
            yes(!Files.exists(s.intent),"unmatched delete wrote journal");
            assertRows(s,1,2,3);
        });
    }
    static void sidecarManifestExactCanonicalFormat()throws Exception {
        scenario("canonical",s->{
            seeded(s);Intent tx=s.deleteOne(2,CrashPoint.NONE);
            Intent parsed=Intent.decode(Files.readAllBytes(s.intent));
            equal(parsed.serial,tx.serial,"transaction number");
            equal(parsed.before,tx.before,"before digest");
            equal(parsed.after,tx.after,"post digest");
        });
    }
    static void replayedJournalWithChangedHistoryQuarantines()throws Exception {
        scenario("journal_replay",s->{
            seeded(s);Intent tx=s.deleteOne(2,CrashPoint.NONE);
            s.acknowledgeAndClean(tx,CrashPoint.NONE);
            // An incorrectly replayed old intent cannot bless a later
            // unrelated history image.
            Files.write(s.history,Store.encode(Arrays.asList(7,8)));
            Files.write(s.intent,tx.encode().getBytes(StandardCharsets.US_ASCII));
            equal(reopened(s).recover().result,Result.QUARANTINED,
                "stale intent authorized arbitrary file");
        });
    }
    static void staleManifestFileCannotBeOverwritten()throws Exception {
        scenario("intent_exists",s->{
            seeded(s);Intent tx=s.deleteOne(2,CrashPoint.NONE);
            expectedIOException(()->s.deleteOne(1,CrashPoint.NONE));
            equal(Intent.decode(Files.readAllBytes(s.intent)).serial,tx.serial,
                "replaced unresolved journal");
        });
    }
    static void threadLockSerializationAcrossOneStore()throws Exception {
        scenario("two_threads",s->{
            seeded(s);
            CountDownLatch start=new CountDownLatch(1),go=new CountDownLatch(1);
            AtomicBoolean firstDone=new AtomicBoolean(false),secondDone=new AtomicBoolean(false);
            AtomicBoolean firstRefused=new AtomicBoolean(false),secondRefused=new AtomicBoolean(false);
            Thread first=new Thread(()->{
                start.countDown();
                try{go.await(3,TimeUnit.SECONDS);s.deleteOne(1,CrashPoint.NONE);firstDone.set(true);}
                catch(IllegalStateException e){firstRefused.set(true);}
                catch(Exception e){throw new RuntimeException(e);}
            },"synthetic-delete-1");
            Thread second=new Thread(()->{
                try{start.await(3,TimeUnit.SECONDS);go.await(3,TimeUnit.SECONDS);
                    s.deleteOne(2,CrashPoint.NONE);secondDone.set(true);}
                catch(IllegalStateException e){secondRefused.set(true);}
                catch(Exception e){throw new RuntimeException(e);}
            },"synthetic-delete-2");
            first.setDaemon(true);second.setDaemon(true);
            first.start();second.start();go.countDown();
            first.join(4000);second.join(4000);
            yes(!first.isAlive()&&!second.isAlive(),"threads hung");
            yes(s.recover().result==Result.COMMITTED_BEFORE_ACK,"no terminal intent");
            // Exactly one local transaction must own the journal.
            // Do not assume which thread won the serialized monitor.
            yes(firstDone.get()!=secondDone.get(),"two writers succeeded or neither did");
            yes(firstRefused.get()!=secondRefused.get(),"exactly one refusal required");
            yes(firstDone.get()!=firstRefused.get()&&
                secondDone.get()!=secondRefused.get(),"writer mixed receipt state");
            yes(s.loadRows().size()==2,"unexpected number of persisted rows");
        });
    }
    static void directorySyncIsNotUniversalClaim()throws Exception {
        scenario("metadata",s->{
            seeded(s);
            yes(s.forcedFiles>0,"file force never issued");
            yes(s.attemptedDirectoryForces>0,"metadata force never attempted");
            // Windows may reject opening a directory; do not assert it succeeds.
        });
    }
    static void historyAtomicMoveNoFallback()throws Exception {
        scenario("same_directory",s->{
            seeded(s);
            Intent tx=s.deleteOne(2,CrashPoint.NONE);
            yes(!Files.exists(s.historyTmp),"staging not moved");
            yes(!Files.exists(s.intentTmp),"manifest staging not moved");
            s.acknowledgeAndClean(tx,CrashPoint.NONE);
        });
    }
    static void corruptSidecarTooLongQuarantines()throws Exception {
        scenario("oversized_intent",s->{
            seeded(s);s.deleteOne(2,CrashPoint.NONE);
            byte[] attack=new byte[MAX_MANIFEST_BYTES+1];
            Arrays.fill(attack,(byte)'a');
            Files.write(s.intent,attack);
            equal(reopened(s).recover().result,Result.QUARANTINED,
                "oversized manifest accepted");
        });
    }
    static void manifestRejectsNonCanonicalWhitespace()throws Exception {
        scenario("extra_whitespace",s->{
            seeded(s);s.deleteOne(2,CrashPoint.NONE);
            byte[] now=Files.readAllBytes(s.intent);
            Files.write(s.intent,(" "+new String(now,StandardCharsets.US_ASCII))
                .getBytes(StandardCharsets.US_ASCII));
            equal(reopened(s).recover().result,Result.QUARANTINED,"malformed journal");
        });
    }
    static void missingHistoryAfterCommitQuarantines()throws Exception {
        scenario("missing_history",s->{
            seeded(s);s.deleteOne(2,CrashPoint.NONE);
            Files.delete(s.history);
            equal(reopened(s).recover().result,Result.QUARANTINED,
                "deleted post-image silently accepted");
        });
    }
    static void missingHistoryBeforeCommitDetected()throws Exception {
        scenario("missing_after_prepare",s->{
            seeded(s);
            expectCrash(()->{try{s.deleteOne(2,CrashPoint.AFTER_INTENT_ATOMIC_MOVE);}
                catch(IOException e){throw new RuntimeException(e);}},
                CrashPoint.AFTER_INTENT_ATOMIC_MOVE);
            Files.delete(s.history);
            equal(reopened(s).recover().result,Result.QUARANTINED,
                "erased pre-image silently accepted");
        });
    }
    static void recoveryDoesNotMutateBytes()throws Exception {
        scenario("read_only_recovery",s->{
            seeded(s);s.deleteOne(2,CrashPoint.NONE);
            byte[] history=Files.readAllBytes(s.history);
            byte[] journal=Files.readAllBytes(s.intent);
            Recovery r=reopened(s).recover();
            equal(r.result,Result.COMMITTED_BEFORE_ACK,"recovery state");
            yes(Arrays.equals(history,Files.readAllBytes(s.history)),"recovery mutated history");
            yes(Arrays.equals(journal,Files.readAllBytes(s.intent)),"recovery mutated intent");
        });
    }
    static void statusWithoutIntentDoesNotInventDeletedRecord()throws Exception {
        scenario("clean_after_cleanup",s->{
            seeded(s);Intent tx=s.deleteOne(2,CrashPoint.NONE);
            s.acknowledgeAndClean(tx,CrashPoint.NONE);
            Recovery r=reopened(s).recover();
            equal(r.result,Result.CLEAN,"clean after ack");
            equal(r.fileRows,Arrays.asList(1,3),"authoritative disk rows");
        });
    }
    static void childProcessCrashAndReopenOptional()throws Exception {
        // Distinct Java process test is run through the optional '--child'
        // entrypoints below, not through untrusted client launch.
        scenario("child_script_ready",s->{
            seeded(s);
            yes(s.history.getFileName().toString().equals("invented-history.txt"),
                "unsafe child fixture");
        });
    }
    static void all()throws Exception {
        cleanWithoutJournal();
        successfulCommitRequiresExplicitAck();
        crashBeforeIntentRenameQuarantinesOrphan();
        crashAfterIntentRenameRecognizesAbort();
        crashAfterHistoryTmpQuarantinesRatherThanDeletes();
        crashAfterReplaceRecognizesCommit();
        crashAfterAckBeforeCleanupIdempotent();
        forgedHistoryHashQuarantines();
        forgedManifestQuarantines();
        noIntentButMalformedHistoryQuarantines();
        noIntentMissingHistoryIsCleanEmpty();
        secondDeleteRefusedUntilAck();
        abortCanBeResolvedThenNewDeletion();
        wrongReceiptCannotDeleteJournal();
        uiAdoptionRequiredBeforeJournalDeletion();
        missingUiAdoptionCannotResolve();
        rawHistoryStaysBytesAfterAbort();
        postCommitHistoryExactHash();
        duplicateRowDeletesOneOccurrence();
        missingRowCannotWriteJournal();
        sidecarManifestExactCanonicalFormat();
        replayedJournalWithChangedHistoryQuarantines();
        staleManifestFileCannotBeOverwritten();
        threadLockSerializationAcrossOneStore();
        directorySyncIsNotUniversalClaim();
        historyAtomicMoveNoFallback();
        corruptSidecarTooLongQuarantines();
        manifestRejectsNonCanonicalWhitespace();
        missingHistoryAfterCommitQuarantines();
        missingHistoryBeforeCommitDetected();
        recoveryDoesNotMutateBytes();
        statusWithoutIntentDoesNotInventDeletedRecord();
        childProcessCrashAndReopenOptional();
    }
    public static void main(String[] args)throws Exception {
        if(args.length==3&&args[0].equals("--child-crash-after-replace")) {
            Path root=java.nio.file.Paths.get(args[1]).toAbsolutePath().normalize();
            Store s=new Store(root);
            s.deleteOne(Integer.parseInt(args[2]),CrashPoint.AFTER_HISTORY_ATOMIC_MOVE);
            throw new AssertionError("expected simulated child crash");
        }
        if(args.length==2&&args[0].equals("--child-recover")) {
            Store s=new Store(java.nio.file.Paths.get(args[1]).toAbsolutePath().normalize());
            System.out.println("R409_CHILD_RECOVERY_"+s.recover().result);
            return;
        }
        all();
        System.out.println("R409_FILE_BACKED_SYNTHETIC_PASS "+passed+" scenarios");
        System.out.println("R409_REAL_CLIENT_OR_POWERLOSS_DURABILITY_NOT_VERIFIED");
    }
}
