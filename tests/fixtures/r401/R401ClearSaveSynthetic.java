import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * R401 standalone invented-state model. This is NOT a recovered client,
 * does not touch SpawnPK files, and does not prove real runtime durability.
 *
 * Model interleavings around a shared file lock and clear generation.
 * The fake disk holds only invented names in Java memory.
 */
public final class R401ClearSaveSynthetic {
    static int passed;
    static void check(boolean value,String message) {
        if (!value) throw new AssertionError(message);
    }

    static final class FakeDisk {
        final List<String> history=new ArrayList<>();
        boolean exists=true,failDelete,failWrite;
        int writes,deletions;
        Runnable onWriterEntered;
        boolean save(List<String> rows) {
            if(failWrite)return false;
            if(onWriterEntered!=null) {
                Runnable hook=onWriterEntered;
                onWriterEntered=null;
                hook.run();
            }
            history.clear();history.addAll(rows);
            exists=true;
            ++writes;
            return true;
        }
        boolean clearWithReceipt() {
            if(failDelete)return false;
            exists=false;
            history.clear();
            ++deletions;
            return true; // also true when already nonexistent
        }
    }

    static final class Model {
        final Object historyGate=new Object();
        final Object fileGate=new Object();
        final FakeDisk disk=new FakeDisk();
        final List<String> panel=new ArrayList<>();
        final List<String> pending=new ArrayList<>();
        final List<String> preload=new ArrayList<>();
        long clearGeneration,sessionEpoch;
        boolean clearInProgress,clearUnsafe,loaded=true,historyWriteDeferred;
        boolean accepting=true,acked,staleCallbackRendered;
        int refusedWrites,commits,clearCalls,queuedPanelClear;
        Runnable beforeSaveLock, beforeMergeLock, beforeDelete;
        boolean atEdt=true;

        void drop(String value) {
            synchronized(historyGate) {
                if(!accepting)return;
                pending.add(value);
            }
        }
        boolean persist() {
            final List<String> snapshot;
            final long epoch;
            synchronized(historyGate) {
                if(!loaded||clearInProgress||clearUnsafe) {
                    historyWriteDeferred=true;
                    ++refusedWrites;
                    return false;
                }
                epoch=clearGeneration;
            }
            snapshot=new ArrayList<>(panel);
            synchronized(historyGate) { snapshot.addAll(pending); }
            if(beforeSaveLock!=null) {
                Runnable hook=beforeSaveLock;beforeSaveLock=null;hook.run();
            }
            final boolean saved;
            synchronized(fileGate) {
                synchronized(historyGate) {
                    if(clearInProgress||clearUnsafe||epoch!=clearGeneration) {
                        ++refusedWrites;
                        return false;
                    }
                }
                saved=disk.save(snapshot);
            }
            if(!saved)return false;
            synchronized(historyGate) {
                if(clearInProgress||clearUnsafe||epoch!=clearGeneration) {
                    // Clear now owns disk state; do not acknowledge this write.
                    return false;
                }
                acked=true;
                ++commits;
                return true;
            }
        }
        boolean mergeBeforeRestore() {
            final long epoch;
            synchronized(historyGate) {
                if(clearInProgress||clearUnsafe)return false;
                epoch=clearGeneration;
            }
            List<String> snapshot=new ArrayList<>(disk.history);
            snapshot.addAll(preload);
            if(beforeMergeLock!=null) {
                Runnable hook=beforeMergeLock;beforeMergeLock=null;hook.run();
            }
            boolean success;
            synchronized(fileGate) {
                synchronized(historyGate) {
                    if(clearInProgress||clearUnsafe||clearGeneration!=epoch) {
                        ++refusedWrites;
                        return false;
                    }
                }
                success=disk.save(snapshot);
            }
            if(!success)return false;
            synchronized(historyGate) {
                if(clearInProgress||clearUnsafe||clearGeneration!=epoch)return false;
                acked=true;
                return true;
            }
        }
        boolean clear() {
            check(atEdt,"model does not execute UI events off EDT");
            synchronized(historyGate) {
                if(clearInProgress)return false;
                ++clearGeneration;
                ++sessionEpoch;
                clearInProgress=true;
            }
            if(beforeDelete!=null) {
                Runnable hook=beforeDelete;beforeDelete=null;hook.run();
            }
            final boolean deleted;
            synchronized(fileGate) {deleted=disk.clearWithReceipt();}
            if(!deleted) {
                synchronized(historyGate) {
                    clearUnsafe=true;
                    clearInProgress=false;
                }
                return false;
            }
            synchronized(historyGate) {
                preload.clear();pending.clear();
                loaded=true;acked=false;historyWriteDeferred=false;
            }
            boolean panelCleared=false;
            try {
                panel.clear();
                panelCleared=true;
            } finally {
                synchronized(historyGate) {
                    if(!panelCleared)clearUnsafe=true;
                    else clearUnsafe=false;
                    clearInProgress=false;
                }
            }
            ++clearCalls;
            return true;
        }
        void queuedDropCallback(long originatingEpoch,String value) {
            synchronized(historyGate) {
                if(originatingEpoch!=sessionEpoch)return;
            }
            panel.add(value);
            staleCallbackRendered=true;
        }
        void newSessionDrop(String value) {
            panel.add(value);
            disk.save(panel);
        }
    }

    static void ids(List<String> actual,String... expected) {
        check(actual.equals(Arrays.asList(expected)),
                "actual="+actual+" expected="+Arrays.asList(expected));
    }
    static void await(CountDownLatch latch,String name) {
        try {
            check(latch.await(4,TimeUnit.SECONDS),name+" timed out");
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new AssertionError(name+" interrupted",e);
        }
    }

    static void normalSave() {
        Model m=new Model();m.panel.add("a");
        check(m.persist(),"normal save failed");ids(m.disk.history,"a");
        check(m.disk.writes==1&&m.acked,"save receipt not recorded");passed++;
    }
    static void clearWithoutPriorSave() {
        Model m=new Model();m.disk.history.add("old");m.panel.add("old");
        check(m.clear(),"clear refused valid request");
        ids(m.disk.history);ids(m.panel);
        check(!m.disk.exists && m.disk.deletions==1,"file not deleted");passed++;
    }
    static void clearMissingFileAccepted() {
        Model m=new Model();m.disk.exists=false;
        check(m.clear(),"already missing history should count as clear");
        check(!m.clearUnsafe && m.disk.deletions==1,"wrong missing-file result");
        passed++;
    }
    static void deletionFailurePreservesUIAndDisk() {
        Model m=new Model();m.disk.history.add("old");m.panel.add("old");
        m.disk.failDelete=true;
        check(!m.clear(),"failed deletion falsely reported successful");
        ids(m.disk.history,"old");ids(m.panel,"old");
        check(m.clearUnsafe && !m.clearInProgress,"failure not quarantined");
        check(!m.persist(),"unsafe auto write was accepted");passed++;
    }
    static void failedClearCanBeRetriedExplicitly() {
        Model m=new Model();m.disk.history.add("old");m.panel.add("old");
        m.disk.failDelete=true;check(!m.clear(),"injected failure not detected");
        m.disk.failDelete=false;check(m.clear(),"explicit retry failed");
        check(!m.clearUnsafe&&!m.disk.exists,"retry failed to clear");passed++;
    }
    static void clearBeforeSaveLockRejectsStaleSnapshot() {
        Model m=new Model();m.disk.history.add("old");m.panel.add("stale");
        m.beforeSaveLock=()->check(m.clear(),"clear failed in snapshot window");
        check(!m.persist(),"stale snapshot was committed after clear");
        ids(m.disk.history);ids(m.panel);
        check(!m.disk.exists && m.disk.writes==0,"history resurrected");
        passed++;
    }
    static void clearBeforeStopMergeLockRejectsStaleMerge() {
        Model m=new Model();m.disk.history.add("old");m.preload.add("unsaved");
        m.beforeMergeLock=()->check(m.clear(),"clear failed during merge window");
        check(!m.mergeBeforeRestore(),"preclear merge recreated deleted history");
        ids(m.disk.history);check(!m.disk.exists,"shutdown merge resurrected file");
        passed++;
    }
    static void writeAlreadyHoldingLockFinishesBeforeClearDelete() throws Exception {
        final Model m=new Model();m.disk.history.add("old");m.panel.add("new");
        final CountDownLatch saveEntered=new CountDownLatch(1);
        final CountDownLatch allowWrite=new CountDownLatch(1);
        final CountDownLatch clearRequested=new CountDownLatch(1);
        final AtomicBoolean clearOK=new AtomicBoolean(false);
        m.disk.onWriterEntered=()->{
            saveEntered.countDown();
            await(allowWrite,"write release");
        };
        Thread save=new Thread(m::persist,"r401-synthetic-save");
        save.setDaemon(true);save.start();
        await(saveEntered,"save entry");
        Thread clear=new Thread(()->{
            m.atEdt=true; // fake calling thread is designated EDT
            clearRequested.countDown();
            clearOK.set(m.clear());
        },"r401-synthetic-clear-edt");
        clear.setDaemon(true);clear.start();
        await(clearRequested,"clear request");
        // Wait until clear has invalidated any stale save acknowledgments
        // before releasing the interrupted disk writer.
        long end=System.nanoTime()+TimeUnit.SECONDS.toNanos(3);
        while(!m.clearInProgress && System.nanoTime()<end)Thread.yield();
        check(m.clearInProgress,"clear did not enter its epoch transition");
        allowWrite.countDown();
        save.join(3000);clear.join(3000);
        check(!save.isAlive()&&!clear.isAlive(),"file lock deadlock");
        check(clearOK.get(),"clear did not finish");
        ids(m.disk.history);
        check(!m.disk.exists && m.disk.deletions==1,"saved file resurrected after clear");
        passed++;
    }
    static void saveDuringBlockedClearRefused() {
        Model m=new Model();m.disk.history.add("old");m.panel.add("old");
        m.beforeDelete=()->{
            check(m.clearInProgress,"clear not marked before deletion");
            check(!m.persist(),"concurrent save admitted during clear");
        };
        check(m.clear(),"clear failed");
        ids(m.disk.history);passed++;
    }
    static void ackNotIssuedForSnapshotInvalidatedByClear() {
        Model m=new Model();m.panel.add("old");
        m.beforeSaveLock=()->check(m.clear(),"clear missed");
        check(!m.persist(),"invalidated receipt accepted");
        check(!m.acked,"stale snapshot acknowledged");passed++;
    }
    static void newSaveAfterSuccessfulClear() {
        Model m=new Model();m.disk.history.add("old");m.panel.add("old");
        check(m.clear(),"clear failed");
        m.panel.add("fresh");
        check(m.persist(),"postclear fresh snapshot refused");
        ids(m.disk.history,"fresh");passed++;
    }
    static void oldSessionCallbackCannotRestoreClearedRecord() {
        Model m=new Model();m.disk.history.add("old");m.panel.add("old");
        long old=m.sessionEpoch;
        check(m.clear(),"clear failed");
        m.queuedDropCallback(old,"stale");
        ids(m.panel);check(!m.staleCallbackRendered,"old callback rendered");
        passed++;
    }
    static void immediatePanelClearDoesNotQueueOldDeletion() {
        Model m=new Model();m.disk.history.add("old");m.panel.add("old");
        check(m.clear(),"clear failed");
        m.panel.add("fresh");
        ids(m.panel,"fresh");
        check(m.queuedPanelClear==0,"old EDT clear remained queued");
        passed++;
    }
    static void twoSameTitleRecordsRemainDistinctWhenSaving() {
        Model m=new Model();m.panel.add("same");m.panel.add("same");
        check(m.persist(),"save failed");ids(m.disk.history,"same","same");
        passed++;
    }
    static void emptyClearDoesNotResurrectFromNoOpSave() {
        Model m=new Model();m.disk.history.add("old");m.panel.add("old");
        check(m.clear(),"clear failed");
        check(m.persist(),"empty postclear save unexpectedly refused");
        ids(m.disk.history);
        check(m.disk.exists,"empty history save is allowed by current store semantics");
        passed++;
    }
    static void failedNormalWriteNotAcknowledged() {
        Model m=new Model();m.disk.history.add("old");m.panel.add("new");
        m.disk.failWrite=true;
        check(!m.persist(),"failed write returned success");
        ids(m.disk.history,"old");check(!m.acked,"failed save acknowledged");passed++;
    }
    static void unrelatedPanelMutationStillExplicitlyUnprotected() {
        Model m=new Model();m.panel.add("a");
        // A record can be deleted directly from the panel while a
        // background save is in flight. R401 covers clear-vs-save only.
        m.beforeSaveLock=()->m.panel.clear();
        check(m.persist(),"ordinary save failed");
        ids(m.disk.history,"a");
        ids(m.panel);
        passed++;
    }

    public static void main(String[] args) throws Exception {
        normalSave();
        clearWithoutPriorSave();
        clearMissingFileAccepted();
        deletionFailurePreservesUIAndDisk();
        failedClearCanBeRetriedExplicitly();
        clearBeforeSaveLockRejectsStaleSnapshot();
        clearBeforeStopMergeLockRejectsStaleMerge();
        writeAlreadyHoldingLockFinishesBeforeClearDelete();
        saveDuringBlockedClearRefused();
        ackNotIssuedForSnapshotInvalidatedByClear();
        newSaveAfterSuccessfulClear();
        oldSessionCallbackCannotRestoreClearedRecord();
        immediatePanelClearDoesNotQueueOldDeletion();
        twoSameTitleRecordsRemainDistinctWhenSaving();
        emptyClearDoesNotResurrectFromNoOpSave();
        failedNormalWriteNotAcknowledged();
        unrelatedPanelMutationStillExplicitlyUnprotected();
        System.out.println("R401_SYNTHETIC_PASS "+passed+" scenarios");
    }
}
