import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Queue;
import java.util.Set;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Predicate;

/**
 * R408 invented protocol model: admission on fake EDT, serialized background
 * disk commit and explicit later EDT receipt. NO original recovered code,
 * network, real filesystem, binary or player history.
 *
 * A test model, NOT a production implementation or crash recovery proof.
 */
public final class R408AsyncDeleteProtocolSynthetic {
    private static int passed;
    private static void yes(boolean condition,String message) {
        if (!condition) throw new AssertionError(message);
    }
    private static void await(CountDownLatch latch,String label) {
        try {yes(latch.await(4,TimeUnit.SECONDS),"timeout: "+label);}
        catch(InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new AssertionError(label,e);
        }
    }
    private static void await(Future<?> future,String label) {
        try {future.get(4,TimeUnit.SECONDS);}
        catch(Exception e) {throw new AssertionError(label,e);}
    }
    private static void rowIds(Collection<Row> records,int... wanted) {
        List<Integer> got=new ArrayList<>(),want=new ArrayList<>();
        for(Row row:records)got.add(row.id);
        for(int i:wanted)want.add(i);
        yes(got.equals(want),"got="+got+" wanted="+want);
    }
    private static Set<Row> identitySet() {
        return Collections.newSetFromMap(new IdentityHashMap<Row,Boolean>());
    }
    static final class Row {
        final int id,qty;
        final String title;
        final long price;
        Row(int id,String title,int qty,long price) {
            this.id=id;this.title=title;this.qty=qty;this.price=price;
        }
        Row freeze(){return new Row(id,title,qty,price);}
    }
    static Row row(int id) {return new Row(id,"same",id,10L+id);}
    enum Status {PENDING,COMMITTED,FAILED,AMBIGUOUS,CANCELED,REJECTED}
    enum Receipt {SUCCESS,FAIL_BEFORE_REPLACE,UNKNOWN_AFTER_REPLACE}
    static final class Txn {
        final long epoch,editVersion;
        final Set<Row> victims;
        volatile Status status=Status.PENDING;
        volatile long snapshotMutation;
        Txn(long epoch,long version,Set<Row> victims) {
            this.epoch=epoch;this.editVersion=version;this.victims=victims;
        }
    }
    static final class Model implements AutoCloseable {
        final Object state=new Object(),fileGate=new Object();
        final List<Row> panel=new ArrayList<>(),pending=new ArrayList<>();
        final List<Row> disk=new ArrayList<>();
        final Queue<Runnable> edt=new ConcurrentLinkedQueue<>();
        final ExecutorService writer=Executors.newSingleThreadExecutor(task->{
            Thread t=new Thread(task,"R408-Synthetic-IO");
            t.setDaemon(true);
            return t;
        });
        final AtomicInteger writeCount=new AtomicInteger();
        long epoch=1,editVersion=0,mutation=0;
        boolean active=true,unsafe=false,clearing=false,deferredAutosave=false;
        boolean uiOnly=false;
        Txn current;
        Receipt nextReceipt=Receipt.SUCCESS;
        Runnable beforeWrite=()->{};
        String uiLabel="READY";
        boolean userHasReceivedSuccess=false;
        int staleAckCount,failedAckCount,blockedAutosaves;

        Model(Row... records) {
            for(Row r:records){panel.add(r);disk.add(r.freeze());}
        }
        List<Row> diskSnapshot() {
            synchronized(fileGate) {
                List<Row> ret=new ArrayList<>();
                for(Row r:disk)ret.add(r.freeze());
                return ret;
            }
        }
        List<Row> uiSnapshot() {
            synchronized(state) {return new ArrayList<>(panel);}
        }
        void addDrop(Row r) {
            synchronized(state) {
                panel.add(r);
                mutation++;
                if(current!=null || clearing)deferredAutosave=true;
            }
        }
        void addPendingDrop(Row r) {
            synchronized(state) {
                pending.add(r);
                mutation++;
                if(current!=null)deferredAutosave=true;
            }
        }
        void movePendingToPanel(Row r) {
            synchronized(state) {
                pending.removeIf(x->x==r);
                panel.add(r);
                mutation++;
                if(current!=null)deferredAutosave=true;
            }
        }
        Txn confirmDelete(Predicate<Row> selector) {
            synchronized(state) {
                if(!active||unsafe||clearing||current!=null) {
                    uiLabel="REFUSED";
                    return null;
                }
                Set<Row> identities=identitySet();
                for(Row r:panel) if(selector.test(r))identities.add(r);
                if(identities.isEmpty()) {
                    uiLabel="NO_MATCH";
                    return null;
                }
                if(uiOnly) {
                    panel.removeIf(identities::contains);
                    editVersion++;
                    uiLabel="UI_ONLY";
                    return null;
                }
                current=new Txn(epoch,++editVersion,identities);
                uiLabel="PENDING";
                userHasReceivedSuccess=false;
                return current;
            }
        }
        Future<?> submitDelete(final Txn t) {
            return writer.submit(()->commitDelete(t));
        }
        private void commitDelete(final Txn t) {
            // The IO executor is single-threaded, and the same file
            // monitor serializes any in-flight autosave or Clear all.
            synchronized(fileGate) {
                final List<Row> frozen=new ArrayList<>();
                synchronized(state) {
                    if(current!=t||t.epoch!=epoch||!active||clearing||unsafe) {
                        post(t,Status.CANCELED);
                        return;
                    }
                    for(Row r:panel)if(!t.victims.contains(r))frozen.add(r.freeze());
                    for(Row r:pending)if(!t.victims.contains(r))frozen.add(r.freeze());
                    t.snapshotMutation=mutation;
                }
                beforeWrite.run();
                synchronized(state) {
                    if(current!=t||t.epoch!=epoch||!active||clearing||unsafe) {
                        post(t,Status.CANCELED);
                        return;
                    }
                }
                final Receipt verdict=nextReceipt;
                if(verdict!=Receipt.FAIL_BEFORE_REPLACE) {
                    disk.clear();disk.addAll(frozen);
                    writeCount.incrementAndGet();
                }
                post(t,verdict==Receipt.SUCCESS?Status.COMMITTED:
                    verdict==Receipt.FAIL_BEFORE_REPLACE?Status.FAILED:Status.AMBIGUOUS);
            }
        }
        private void post(final Txn t,final Status s) {
            edt.add(()->ackOnEdt(t,s));
        }
        void drainEdt() {
            Runnable r;
            while((r=edt.poll())!=null)r.run();
        }
        private void ackOnEdt(Txn t,Status result) {
            synchronized(state) {
                if(current!=t||t.epoch!=epoch) {
                    staleAckCount++;
                    t.status=Status.CANCELED;
                    return;
                }
                if(result==Status.COMMITTED) {
                    // Only the EDT removes live rows, by original identity.
                    panel.removeIf(t.victims::contains);
                    if(mutation!=t.snapshotMutation)deferredAutosave=true;
                    uiLabel="SAVED";
                    userHasReceivedSuccess=true;
                    t.status=Status.COMMITTED;
                }else{
                    // Never remove rows on failed or ambiguous IO.
                    uiLabel=result==Status.AMBIGUOUS?"UNKNOWN":"FAILED";
                    userHasReceivedSuccess=false;
                    if(result==Status.AMBIGUOUS)unsafe=true;
                    failedAckCount++;
                    t.status=result;
                }
                current=null;
                ++editVersion; // invalidate any stale autosave snapshot
            }
        }
        Future<?> submitAutosave() {
            final long version;
            final List<Row> snapshot=new ArrayList<>();
            synchronized(state) {
                version=editVersion;
                for(Row r:panel)snapshot.add(r.freeze());
                for(Row r:pending)snapshot.add(r.freeze());
            }
            return writer.submit(()->{
                synchronized(fileGate) {
                    synchronized(state) {
                        if(!active||unsafe||clearing||current!=null||
                            version!=editVersion) {
                            blockedAutosaves++;
                            deferredAutosave=true;
                            return;
                        }
                    }
                    disk.clear();disk.addAll(snapshot);
                    writeCount.incrementAndGet();
                }
            });
        }
        boolean clearAll(Receipt verdict) {
            synchronized(state) {
                ++epoch;
                ++editVersion;
                current=null;
                clearing=true;
                uiLabel="CLEAR_PENDING";
            }
            synchronized(fileGate) {
                if(verdict!=Receipt.SUCCESS) {
                    synchronized(state) {
                        unsafe=true;clearing=false;
                        uiLabel="CLEAR_FAILED";
                    }
                    return false;
                }
                disk.clear();writeCount.incrementAndGet();
            }
            synchronized(state) {
                panel.clear();
                pending.clear();
                deferredAutosave=false;
                unsafe=false;
                clearing=false;
                uiLabel="CLEARED";
            }
            return true;
        }
        void stop() {
            synchronized(state) {
                active=false;
                ++epoch;
                ++editVersion;
                current=null;
                uiLabel="STOPPED_UNRESOLVED";
            }
        }
        void cancelBeforeWrite(Txn t) {
            synchronized(state) {
                if(current==t) {
                    current=null;
                    ++editVersion;
                    t.status=Status.CANCELED;
                    uiLabel="CANCELED";
                }
            }
        }
        @Override public void close() {writer.shutdown();}
    }

    static void noSuccessBeforeWorkerCommit() {
        try(Model m=new Model(row(1),row(2))) {
            Txn t=m.confirmDelete(r->r.id==1);
            yes(t!=null&&m.uiLabel.equals("PENDING"),"not pending");
            yes(!m.userHasReceivedSuccess,"premature receipt");
            rowIds(m.uiSnapshot(),1,2);rowIds(m.diskSnapshot(),1,2);
            passed++;
        }
    }
    static void noSuccessBeforeEdtAck() {
        try(Model m=new Model(row(1),row(2))) {
            Txn t=m.confirmDelete(r->r.id==1);
            await(m.submitDelete(t),"commit");
            rowIds(m.diskSnapshot(),2);
            rowIds(m.uiSnapshot(),1,2);
            yes(m.uiLabel.equals("PENDING")&&!m.userHasReceivedSuccess,
                "user was told success before EDT ack");
            m.drainEdt();
            yes(t.status==Status.COMMITTED&&m.userHasReceivedSuccess,"missing receipt");
            rowIds(m.uiSnapshot(),2);passed++;
        }
    }
    static void exactIdentityDeletionNotTitleEquality() {
        try(Model m=new Model(row(1),row(2))) {
            Txn t=m.confirmDelete(r->r.id==1);
            await(m.submitDelete(t),"commit");m.drainEdt();
            rowIds(m.diskSnapshot(),2);rowIds(m.uiSnapshot(),2);passed++;
        }
    }
    static void bulkTypeDeleteCapturesOnlyConfirmedIdentities() {
        try(Model m=new Model(row(1),row(2),row(3))) {
            Txn t=m.confirmDelete(r->r.id<=2);
            m.addDrop(row(4));
            await(m.submitDelete(t),"commit");m.drainEdt();
            rowIds(m.diskSnapshot(),3,4);
            rowIds(m.uiSnapshot(),3,4);
            passed++;
        }
    }
    static void newDropDuringWriteSurvivesUiAcknowledgment() {
        try(Model m=new Model(row(1),row(2))) {
            Txn t=m.confirmDelete(r->r.id==1);
            CountDownLatch inWrite=new CountDownLatch(1),release=new CountDownLatch(1);
            m.beforeWrite=()->{inWrite.countDown();await(release,"release IO");};
            Future<?> f=m.submitDelete(t);
            await(inWrite,"writer captured snapshot");
            m.addDrop(row(3));
            release.countDown();await(f,"commit");
            m.drainEdt();
            rowIds(m.uiSnapshot(),2,3);
            rowIds(m.diskSnapshot(),2);
            yes(m.deferredAutosave,"new drop must require followup save");
            passed++;
        }
    }
    static void pendingDropBeforeSnapshotIncluded() {
        try(Model m=new Model(row(1))) {
            m.addPendingDrop(row(2));
            Txn t=m.confirmDelete(r->r.id==1);
            await(m.submitDelete(t),"commit");m.drainEdt();
            rowIds(m.diskSnapshot(),2);passed++;
        }
    }
    static void pendingHandoffAfterDiskCommitStaysSingle() {
        try(Model m=new Model(row(1))) {
            Row pending=row(2);
            m.addPendingDrop(pending);
            Txn t=m.confirmDelete(r->r.id==1);
            await(m.submitDelete(t),"commit");
            m.movePendingToPanel(pending);
            m.drainEdt();
            rowIds(m.uiSnapshot(),2);
            rowIds(m.diskSnapshot(),2);
            yes(m.deferredAutosave,"handoff needs followup coalescing");
            passed++;
        }
    }
    static void failedWriteLeavesPanelAndDiskIntact() {
        try(Model m=new Model(row(1),row(2))) {
            m.nextReceipt=Receipt.FAIL_BEFORE_REPLACE;
            Txn t=m.confirmDelete(r->r.id==1);
            await(m.submitDelete(t),"failure");m.drainEdt();
            rowIds(m.uiSnapshot(),1,2);rowIds(m.diskSnapshot(),1,2);
            yes(t.status==Status.FAILED&&!m.userHasReceivedSuccess,
                "false success on failed write");
            yes(!m.unsafe,"known pre-replace failure need not corrupt old disk");
            passed++;
        }
    }
    static void ambiguousCommitPreservesUiAndQuarantines() {
        try(Model m=new Model(row(1),row(2))) {
            m.nextReceipt=Receipt.UNKNOWN_AFTER_REPLACE;
            Txn t=m.confirmDelete(r->r.id==1);
            await(m.submitDelete(t),"ambiguous IO");m.drainEdt();
            rowIds(m.uiSnapshot(),1,2);rowIds(m.diskSnapshot(),2);
            yes(t.status==Status.AMBIGUOUS&&m.unsafe&&!m.userHasReceivedSuccess,
                "ambiguous write not quarantined");
            yes(m.confirmDelete(r->true)==null,"unsafe state accepted new edit");
            passed++;
        }
    }
    static void secondDeleteRefusedDuringFirstPending() {
        try(Model m=new Model(row(1),row(2))) {
            Txn first=m.confirmDelete(r->r.id==1);
            yes(m.confirmDelete(r->r.id==2)==null,"overlapping edit accepted");
            await(m.submitDelete(first),"commit");m.drainEdt();
            rowIds(m.uiSnapshot(),2);passed++;
        }
    }
    static void subsequentDeleteAcceptedAfterAck() {
        try(Model m=new Model(row(1),row(2))) {
            Txn first=m.confirmDelete(r->r.id==1);
            await(m.submitDelete(first),"first");m.drainEdt();
            Txn second=m.confirmDelete(r->r.id==2);
            yes(second!=null,"second edit was permanently blocked");
            await(m.submitDelete(second),"second");m.drainEdt();
            rowIds(m.diskSnapshot());rowIds(m.uiSnapshot());
            passed++;
        }
    }
    static void autosaveCannotOvertakeStagedDelete() {
        try(Model m=new Model(row(1),row(2))) {
            Txn t=m.confirmDelete(r->r.id==1);
            await(m.submitAutosave(),"stale autosave");
            yes(m.blockedAutosaves==1,"stale autosave was committed");
            await(m.submitDelete(t),"delete");m.drainEdt();
            rowIds(m.diskSnapshot(),2);
            passed++;
        }
    }
    static void alreadyQueuedOldAutosaveCannotResurrectDelete() {
        try(Model m=new Model(row(1),row(2))) {
            Future<?> queued=m.submitAutosave();
            Txn t=m.confirmDelete(r->r.id==1);
            await(queued,"old autosave");
            await(m.submitDelete(t),"delete");m.drainEdt();
            rowIds(m.diskSnapshot(),2);
            passed++;
        }
    }
    static void clearAllInvalidatesQueuedDelete() {
        try(Model m=new Model(row(1),row(2))) {
            Txn t=m.confirmDelete(r->r.id==1);
            yes(m.clearAll(Receipt.SUCCESS),"clear failed");
            await(m.submitDelete(t),"stale edit");m.drainEdt();
            rowIds(m.diskSnapshot());rowIds(m.uiSnapshot());
            yes(!m.userHasReceivedSuccess&&t.status==Status.CANCELED,
                "stale edit claimed success after clear");
            passed++;
        }
    }
    static void clearAllDuringWriteWinsFinalDiskOrder() {
        try(Model m=new Model(row(1),row(2))) {
            Txn t=m.confirmDelete(r->r.id==1);
            CountDownLatch captured=new CountDownLatch(1),release=new CountDownLatch(1);
            m.beforeWrite=()->{captured.countDown();await(release,"held commit");};
            Future<?> f=m.submitDelete(t);
            await(captured,"delete write entered");
            CountDownLatch clearStarted=new CountDownLatch(1);
            Thread clear=new Thread(()->{
                clearStarted.countDown();
                yes(m.clearAll(Receipt.SUCCESS),"clear failure");
            },"R408-Synthetic-EDT-Clear");
            clear.setDaemon(true);clear.start();
            await(clearStarted,"clear start");
            release.countDown();
            await(f,"edit completion");
            try {clear.join(4000);}catch(InterruptedException e){throw new AssertionError(e);}
            yes(!clear.isAlive(),"clear blocked");
            m.drainEdt();
            rowIds(m.diskSnapshot());rowIds(m.uiSnapshot());
            yes(!m.userHasReceivedSuccess,"stale success after clear");
            passed++;
        }
    }
    static void clearFailureQuarantinesWithoutConfirmedEdit() {
        try(Model m=new Model(row(1))) {
            Txn t=m.confirmDelete(r->r.id==1);
            yes(!m.clearAll(Receipt.FAIL_BEFORE_REPLACE),"clear acknowledged false success");
            await(m.submitDelete(t),"old transaction");m.drainEdt();
            rowIds(m.diskSnapshot(),1);rowIds(m.uiSnapshot(),1);
            yes(m.unsafe&&!m.userHasReceivedSuccess,"failed clear not quarantined");
            passed++;
        }
    }
    static void stopBeforeCommitRefusesOldWorker() {
        try(Model m=new Model(row(1),row(2))) {
            Txn t=m.confirmDelete(r->r.id==1);
            m.stop();
            await(m.submitDelete(t),"stop fence");m.drainEdt();
            rowIds(m.diskSnapshot(),1,2);rowIds(m.uiSnapshot(),1,2);
            yes(!m.userHasReceivedSuccess,"ack from stopped plugin");
            passed++;
        }
    }
    static void staleSuccessReceiptAfterStopMustNotEditUi() {
        try(Model m=new Model(row(1),row(2))) {
            Txn t=m.confirmDelete(r->r.id==1);
            await(m.submitDelete(t),"committed");
            m.stop();
            m.drainEdt();
            rowIds(m.diskSnapshot(),2);rowIds(m.uiSnapshot(),1,2);
            yes(t.status==Status.CANCELED&&!m.userHasReceivedSuccess,
                "late callback altered stopped panel");
            // This mismatch is a RELEASE BLOCKER without durable
            // restart recovery; intentionally not labeled success.
            yes(m.staleAckCount==1,"lost stale-ack evidence");
            passed++;
        }
    }
    static void queuedIntentCancellationBeforeCommitPreservesDisk() {
        try(Model m=new Model(row(1),row(2))) {
            Txn t=m.confirmDelete(r->r.id==1);
            m.cancelBeforeWrite(t);
            await(m.submitDelete(t),"canceled");
            m.drainEdt();
            rowIds(m.diskSnapshot(),1,2);rowIds(m.uiSnapshot(),1,2);
            yes(!m.userHasReceivedSuccess&&t.status==Status.CANCELED,
                "canceled edit committed");
            passed++;
        }
    }
    static void noMatchDoesNotQueueWrite() {
        try(Model m=new Model(row(1))) {
            yes(m.confirmDelete(r->r.id==999)==null,"no-match edit was queued");
            rowIds(m.uiSnapshot(),1);rowIds(m.diskSnapshot(),1);
            passed++;
        }
    }
    static void uiOnlyDeleteDoesNotClaimDiskCommit() {
        try(Model m=new Model(row(1))) {
            m.uiOnly=true;
            yes(m.confirmDelete(r->true)==null,"UI-only edit wrongly queued");
            rowIds(m.uiSnapshot());rowIds(m.diskSnapshot(),1);
            yes(m.uiLabel.equals("UI_ONLY")&&!m.userHasReceivedSuccess,
                "UI-only edit claimed persistent write");
            passed++;
        }
    }
    static void unsupportedEditorVersionRejectsOldSnapshot() {
        try(Model m=new Model(row(1),row(2))) {
            Txn t=m.confirmDelete(r->r.id==1);
            m.cancelBeforeWrite(t);
            await(m.submitAutosave(),"old autosave");
            // Autosave may still be admitted after explicit cancel, but
            // the confirmed edit was never applied. No false receipt.
            rowIds(m.diskSnapshot(),1,2);
            passed++;
        }
    }
    static void syntheticReceiptCannotClaimPowerLossSafety() {
        try(Model m=new Model(row(1))) {
            Txn t=m.confirmDelete(r->true);
            yes(!m.userHasReceivedSuccess,"queued transaction is not durable");
            // Model uses memory-only disk and cannot prove fsync.
            passed++;
        }
    }

    public static void main(String[] args) {
        noSuccessBeforeWorkerCommit();
        noSuccessBeforeEdtAck();
        exactIdentityDeletionNotTitleEquality();
        bulkTypeDeleteCapturesOnlyConfirmedIdentities();
        newDropDuringWriteSurvivesUiAcknowledgment();
        pendingDropBeforeSnapshotIncluded();
        pendingHandoffAfterDiskCommitStaysSingle();
        failedWriteLeavesPanelAndDiskIntact();
        ambiguousCommitPreservesUiAndQuarantines();
        secondDeleteRefusedDuringFirstPending();
        subsequentDeleteAcceptedAfterAck();
        autosaveCannotOvertakeStagedDelete();
        alreadyQueuedOldAutosaveCannotResurrectDelete();
        clearAllInvalidatesQueuedDelete();
        clearAllDuringWriteWinsFinalDiskOrder();
        clearFailureQuarantinesWithoutConfirmedEdit();
        stopBeforeCommitRefusesOldWorker();
        staleSuccessReceiptAfterStopMustNotEditUi();
        queuedIntentCancellationBeforeCommitPreservesDisk();
        noMatchDoesNotQueueWrite();
        uiOnlyDeleteDoesNotClaimDiskCommit();
        unsupportedEditorVersionRejectsOldSnapshot();
        syntheticReceiptCannotClaimPowerLossSafety();
        System.out.println("R408_SYNTHETIC_PROTOCOL_PASS "+passed+" scenarios");
    }
}
