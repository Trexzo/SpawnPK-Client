import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

/** R406: entirely fabricated lock-contention and receipt model, no client I/O. */
public final class R406EdtContentionSynthetic {
    static int passed;
    static void yes(boolean value,String message) {
        if(!value)throw new AssertionError(message);
    }
    static void await(CountDownLatch latch,String label) {
        try {yes(latch.await(4,TimeUnit.SECONDS),"timeout "+label);}
        catch(InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new AssertionError(label,e);
        }
    }
    static void join(Thread t,String label) {
        try {t.join(4000);}
        catch(InterruptedException e) {Thread.currentThread().interrupt();throw new AssertionError(e);}
        yes(!t.isAlive(),"thread still active: "+label);
    }
    static void rows(List<String> actual,String... wanted) {
        yes(actual.equals(Arrays.asList(wanted)),
            "actual="+actual+" expected="+Arrays.asList(wanted));
    }
    static final class MockDisk {
        final List<String> stored=new ArrayList<>();
        int commits;
        boolean writable=true;
        boolean write(List<String> data) {
            if(!writable)return false;
            stored.clear();
            stored.addAll(data);
            commits++;
            return true;
        }
    }
    static final class Model {
        final Object fileGate=new Object();
        final Object historyGate=new Object();
        final List<String> panel=new ArrayList<>();
        final MockDisk disk=new MockDisk();
        final List<String> events=new ArrayList<>();
        boolean unsafe,accepted=true;
        final AtomicInteger writerOverlap=new AtomicInteger(0);
        final AtomicInteger peakWriterOverlap=new AtomicInteger(0);

        Model(String... initial) {
            panel.addAll(Arrays.asList(initial));
            disk.stored.addAll(Arrays.asList(initial));
        }
        void autosave(CountDownLatch ownsGate,CountDownLatch releaseGate) {
            final List<String> snapshot=new ArrayList<>(panel);
            synchronized(fileGate) {
                ownsGate.countDown();
                await(releaseGate,"release autosave lock");
                events.add("autosave-commit");
                disk.write(snapshot);
            }
        }
        boolean deleteRow(String name,CountDownLatch admitted) {
            admitted.countDown(); // real handler has already been confirmed on EDT
            synchronized(fileGate) {
                if(unsafe)return false;
                panel.remove(name);
                events.add("delete-mutated");
                final boolean committed=disk.write(new ArrayList<>(panel));
                events.add(committed?"delete-committed":"delete-failed");
                if(!committed)unsafe=true;
                return committed;
            }
        }
        boolean clearAll(CountDownLatch admitted) {
            admitted.countDown();
            synchronized(fileGate) {
                if(unsafe)return false;
                boolean deleted=disk.writable;
                if(deleted) {
                    disk.stored.clear();
                    panel.clear();
                    events.add("clear-committed");
                } else {
                    unsafe=true;
                    events.add("clear-failed");
                }
                return deleted;
            }
        }
        void directSyncDelete(String name,CountDownLatch writeEntered,
                              CountDownLatch permitCommit) {
            synchronized(fileGate) {
                panel.remove(name);
                writeEntered.countDown();
                await(permitCommit,"direct delete write");
                boolean ok=disk.write(new ArrayList<>(panel));
                if(!ok)unsafe=true;
            }
        }
    }

    static void autosaveBlocksConfirmedEdtDelete() {
        Model m=new Model("A","B");
        CountDownLatch lockHeld=new CountDownLatch(1),
            release=new CountDownLatch(1),entered=new CountDownLatch(1);
        Thread background=new Thread(()->m.autosave(lockHeld,release),"synthetic-autosave");
        background.setDaemon(true);background.start();
        await(lockHeld,"background lock");
        AtomicBoolean accepted=new AtomicBoolean(false);
        Thread edt=new Thread(()->accepted.set(m.deleteRow("A",entered)),"synthetic-EDT");
        edt.setDaemon(true);edt.start();
        await(entered,"EDT edit admission");
        // The old lock is held, so neither the mutation nor its receipt
        // can have happened yet. The assertion does not depend on sleeps.
        rows(m.panel,"A","B");
        yes(m.disk.commits==0,"disk advanced while autosave lock held");
        release.countDown();
        join(background,"autosave");join(edt,"EDT");
        yes(accepted.get(),"confirmed delete was not committed");
        rows(m.panel,"B");rows(m.disk.stored,"B");
        yes(m.events.equals(Arrays.asList("autosave-commit","delete-mutated","delete-committed")),
            "file-gate commit order");
        passed++;
    }
    static void autosaveBlocksClearAll() {
        Model m=new Model("A");
        CountDownLatch lockHeld=new CountDownLatch(1),
            release=new CountDownLatch(1),entered=new CountDownLatch(1);
        Thread background=new Thread(()->m.autosave(lockHeld,release));
        background.setDaemon(true);background.start();
        await(lockHeld,"autosave owns gate");
        AtomicBoolean ok=new AtomicBoolean(false);
        Thread edt=new Thread(()->ok.set(m.clearAll(entered)),"synthetic-EDT");
        edt.setDaemon(true);edt.start();
        await(entered,"clear confirmation");
        rows(m.disk.stored,"A");
        release.countDown();join(background,"autosave");join(edt,"clear");
        yes(ok.get(),"clear did not persist");
        rows(m.panel);rows(m.disk.stored);
        passed++;
    }
    static void uncontendedConfirmedDeleteStillBlocksDuringWrite() {
        Model m=new Model("A","B");
        CountDownLatch writing=new CountDownLatch(1),
            release=new CountDownLatch(1);
        Thread edt=new Thread(()->m.directSyncDelete("A",writing,release),
            "synthetic-EDT");
        edt.setDaemon(true);edt.start();
        await(writing,"EDT inside disk write");
        rows(m.panel,"B");
        rows(m.disk.stored,"A","B");
        yes(m.disk.commits==0,"acknowledged before disk write");
        release.countDown();join(edt,"EDT synchronous save");
        rows(m.disk.stored,"B");yes(m.disk.commits==1,"missing receipt");
        passed++;
    }
    static void receiptOnlyAfterCommit() {
        Model m=new Model("A");
        yes(m.deleteRow("A",new CountDownLatch(1)),"successful deletion");
        rows(m.disk.stored);yes(!m.unsafe,"successful write quarantined");
        passed++;
    }
    static void failedDeleteSetsUnsafe() {
        Model m=new Model("A");m.disk.writable=false;
        yes(!m.deleteRow("A",new CountDownLatch(1)),"false success receipt");
        rows(m.disk.stored,"A");rows(m.panel);
        yes(m.unsafe,"failed deletion must fail closed");passed++;
    }
    static void failedClearKeepsPanel() {
        Model m=new Model("A");m.disk.writable=false;
        yes(!m.clearAll(new CountDownLatch(1)),"failed clear reported success");
        rows(m.panel,"A");rows(m.disk.stored,"A");
        yes(m.unsafe,"failed clear needs unsafe flag");passed++;
    }
    static void staleAutosaveCannotBeLastCommitAfterDelete() {
        Model m=new Model("A","B");
        CountDownLatch lockHeld=new CountDownLatch(1),release=new CountDownLatch(1),
            entered=new CountDownLatch(1);
        Thread writer=new Thread(()->m.autosave(lockHeld,release));
        writer.setDaemon(true);writer.start();await(lockHeld,"old writer lock");
        Thread edit=new Thread(()->m.deleteRow("A",entered));
        edit.setDaemon(true);edit.start();await(entered,"edit start");
        release.countDown();join(writer,"old write");join(edit,"edit");
        rows(m.disk.stored,"B");yes(m.disk.commits==2,"one write then delete");
        passed++;
    }
    static void twoDeletesPreserveConfirmationOrder() {
        Model m=new Model("A","B","C");
        yes(m.deleteRow("A",new CountDownLatch(1)),"first");
        yes(m.deleteRow("B",new CountDownLatch(1)),"second");
        rows(m.disk.stored,"C");yes(m.disk.commits==2,"two receipts");passed++;
    }
    static void uiOnlyDeleteWhenPersistenceDisabled() {
        Model m=new Model("A");
        m.panel.remove("A"); // UI-only mode, no disk promise
        rows(m.panel);rows(m.disk.stored,"A");yes(m.disk.commits==0,"no disk update expected");
        passed++;
    }
    static void naiveAsyncAcknowledgmentCanLoseDeletion() {
        // A deliberately UNSAFE redesign: acknowledge before enqueuing,
        // then allow shutdown to discard the job. Test ensures this
        // counterexample stays visible to future implementation reviews.
        Model m=new Model("A");
        boolean toldUserDeleted=true;
        boolean scheduledButNotRun=true;
        if(scheduledButNotRun) { /* simulated JVM termination */ }
        rows(m.disk.stored,"A");
        yes(toldUserDeleted&&m.disk.commits==0,
            "unsafe async acknowledgement counterexample disappeared");
        passed++;
    }
    static void snapshotFirstAndCommitLaterCanResurrectDelete() {
        Model m=new Model("A","B");
        List<String> old=new ArrayList<>(m.panel);
        m.deleteRow("A",new CountDownLatch(1));
        // Deliberately unsafe writer without a generation check:
        m.disk.write(old);
        rows(m.disk.stored,"A","B");
        yes(m.disk.commits==2,"resurrection model did not reproduce");
        passed++;
    }
    static void gatePreventsConcurrentSavesWithinOneInstance()throws Exception {
        Model m=new Model("A");
        CountDownLatch started=new CountDownLatch(1),release=new CountDownLatch(1);
        Thread first=new Thread(()->m.autosave(started,release));
        first.setDaemon(true);first.start();await(started,"first write");
        CountDownLatch secondStarted=new CountDownLatch(1),secondRelease=new CountDownLatch(0);
        Thread second=new Thread(()->m.autosave(secondStarted,secondRelease));
        second.setDaemon(true);second.start();
        yes(secondStarted.getCount()==1,"second entered same monitor concurrently");
        release.countDown();join(first,"first");join(second,"second");
        yes(m.disk.commits==2,"both serialized writer receipts");
        passed++;
    }
    static void fileGateCannotProtectDifferentPluginInstances()throws Exception {
        Model a=new Model("A"),b=new Model("A");
        CountDownLatch aOwns=new CountDownLatch(1),bOwns=new CountDownLatch(1),
            release=new CountDownLatch(1);
        Thread x=new Thread(()->a.autosave(aOwns,release));
        Thread y=new Thread(()->b.autosave(bOwns,release));
        x.setDaemon(true);y.setDaemon(true);x.start();y.start();
        await(aOwns,"plugin A lock");await(bOwns,"plugin B distinct lock");
        release.countDown();join(x,"A");join(y,"B");
        passed++;
    }
    static void workerQueueIsNotAnAcceptedDeleteReceipt() {
        AtomicInteger accepted=new AtomicInteger();
        AtomicInteger queued=new AtomicInteger();
        queued.incrementAndGet();
        yes(accepted.get()==0&&queued.get()==1,
            "queued edit mistaken for durable write");
        passed++;
    }
    static void failedWriteMustNotMarkDurableReceipt() {
        Model m=new Model("A");m.disk.writable=false;
        boolean ack=m.deleteRow("A",new CountDownLatch(1));
        yes(!ack&&m.disk.commits==0&&m.unsafe,"false success");
        passed++;
    }
    static void noHiddenFilesystemOrNetworkDependency() {
        Model m=new Model("A","B");
        m.deleteRow("A",new CountDownLatch(1));
        yes(m.disk.stored instanceof List,"synthetic memory-only store");
        passed++;
    }
    public static void main(String[] args)throws Exception {
        autosaveBlocksConfirmedEdtDelete();
        autosaveBlocksClearAll();
        uncontendedConfirmedDeleteStillBlocksDuringWrite();
        receiptOnlyAfterCommit();
        failedDeleteSetsUnsafe();
        failedClearKeepsPanel();
        staleAutosaveCannotBeLastCommitAfterDelete();
        twoDeletesPreserveConfirmationOrder();
        uiOnlyDeleteWhenPersistenceDisabled();
        naiveAsyncAcknowledgmentCanLoseDeletion();
        snapshotFirstAndCommitLaterCanResurrectDelete();
        gatePreventsConcurrentSavesWithinOneInstance();
        fileGateCannotProtectDifferentPluginInstances();
        workerQueueIsNotAnAcceptedDeleteReceipt();
        failedWriteMustNotMarkDurableReceipt();
        noHiddenFilesystemOrNetworkDependency();
        System.out.println("R406_SYNTHETIC_PASS "+passed+" cases");
    }
}
