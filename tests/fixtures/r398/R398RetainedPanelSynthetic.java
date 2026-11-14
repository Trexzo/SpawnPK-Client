import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * R398 standalone model: NOT recovered SpawnPK, no disk I/O or client launch.
 * State/scheduling exercises the retained-panel refusal and copy-before-lock
 * contract. Successful tests cannot prove real private-client runtime safety.
 */
public final class R398RetainedPanelSynthetic {
    static int passes;
    static void check(boolean value,String message) {
        if (!value) throw new AssertionError(message);
    }
    static void eq(List<String> values,String... expected) {
        check(values.equals(Arrays.asList(expected)),
              "got="+values+" expected="+Arrays.asList(expected));
    }

    static final class MemoryDisk {
        final List<String> rows = new ArrayList<>();
        boolean readable=true, writable=true;
        int reads,writes;
        List<String> readStrict() {
            reads++;
            return readable?new ArrayList<>(rows):null;
        }
        boolean commit(List<String> next) {
            if (!writable) return false;
            rows.clear(); rows.addAll(next); writes++; return true;
        }
    }

    static final class Plugin {
        final Object historyGate=new Object();
        final Object panelMonitor=new Object();
        final MemoryDisk disk=new MemoryDisk();
        final List<String> panel=new ArrayList<>();
        final List<String> preload=new ArrayList<>();
        final List<String> pending=new ArrayList<>();
        final ArrayDeque<Runnable> callbacks=new ArrayDeque<>();
        boolean active,historyLoaded,restoreQueued,unreconciled,resetAfterVerifiedSave;
        int generation,blockedRestores,blockedStopMerges,successfulStopMerges;

        List<String> panelSnapshot() {
            synchronized(panelMonitor) {return new ArrayList<>(panel);}
        }
        void start() {
            synchronized(historyGate) {
                active=true;
                generation++;
                historyLoaded=false;
                restoreQueued=false;
            }
            boolean reset=resetAfterVerifiedSave;
            resetAfterVerifiedSave=false;
            if (reset) {
                synchronized(panelMonitor) {panel.clear();}
            }
            // Snapshot WITHOUT holding historyGate (matches R398 approach).
            boolean existing=!panelSnapshot().isEmpty();
            synchronized(historyGate) {unreconciled=existing;}
            requestRestore();
        }
        void requestRestore() {
            if (unreconciled) {
                blockedRestores++;
                return;
            }
            if (!active || historyLoaded || restoreQueued) return;
            restoreQueued=true;
            final int issued=++generation;
            callbacks.add(()->{
                List<String> restored=disk.readStrict();
                if (!active || generation!=issued || restored==null) {
                    restoreQueued=false;
                    return;
                }
                synchronized(panelMonitor) {panel.addAll(restored);}
                historyLoaded=true;
                restoreQueued=false;
            });
        }
        void drop(String id, boolean deliverToPanel) {
            synchronized(historyGate) {
                preload.add(id);
                pending.add(id);
            }
            if (deliverToPanel) {
                synchronized(panelMonitor) {panel.add(id);}
                pending.remove(id);
            }
        }
        boolean persistLoaded() {
            if (!historyLoaded) return false;
            List<String> collected=panelSnapshot();
            collected.addAll(pending);
            if (!disk.commit(collected)) return false;
            preload.clear();
            resetAfterVerifiedSave=true;
            return true;
        }
        boolean earlyStopMerge() {
            if (unreconciled) {
                blockedStopMerges++;
                return false;
            }
            // Take the panel snapshot separately from the history gate.
            boolean panelEmpty=panelSnapshot().isEmpty();
            synchronized(historyGate) {
                if (preload.isEmpty() && pending.isEmpty() && panelEmpty) {
                    return true;
                }
            }
            List<String> older=disk.readStrict();
            if (older==null) return false;
            synchronized(historyGate) {older.addAll(preload);}
            if (!disk.commit(older)) return false;
            preload.clear();
            historyLoaded=true;
            resetAfterVerifiedSave=true;
            successfulStopMerges++;
            return true;
        }
        void stop() {
            active=false;
            generation++;
            boolean saved = historyLoaded ? persistLoaded() : earlyStopMerge();
            if (!saved && !historyLoaded) {
                // No automatic overwrite of unverified panel or history.
            }
        }
        void clear() {
            generation++;
            restoreQueued=false;
            historyLoaded=true;
            synchronized(historyGate) {
                unreconciled=false;
                preload.clear();
                pending.clear();
            }
            synchronized(panelMonitor) {panel.clear();}
            disk.rows.clear();
        }
        void runNextRestore() {
            check(!callbacks.isEmpty(),"callback missing");
            callbacks.removeFirst().run();
        }
    }

    static void initialRestore() {
        Plugin m=new Plugin();m.disk.rows.add("old");m.start();m.runNextRestore();
        eq(m.panel,"old");passes++;
    }
    static void earlyCleanStopNoIO() {
        Plugin m=new Plugin();m.disk.rows.add("old");m.start();m.stop();
        check(m.disk.reads==0 && m.disk.writes==0,"clean stop I/O");
        eq(m.disk.rows,"old");passes++;
    }
    static void normalDirtyStopCommits() {
        Plugin m=new Plugin();m.disk.rows.add("old");m.start();m.drop("new",true);m.stop();
        eq(m.disk.rows,"old","new");
        check(m.successfulStopMerges==1,"dirty merge skipped");
        passes++;
    }
    static void pendingDropIncluded() {
        Plugin m=new Plugin();m.disk.rows.add("old");m.start();m.drop("pending",false);m.stop();
        eq(m.disk.rows,"old","pending");passes++;
    }
    static void twoSameNameDropsPreserved() {
        Plugin m=new Plugin();m.disk.rows.add("old");m.start();
        m.drop("same",true);m.drop("same",true);m.stop();
        eq(m.disk.rows,"old","same","same");passes++;
    }
    static Plugin retainedAfterFailure() {
        Plugin m=new Plugin();m.disk.rows.add("committed");m.start();
        m.disk.writable=false;
        m.drop("unsaved",true);
        m.stop();
        eq(m.disk.rows,"committed");
        check(!m.resetAfterVerifiedSave,"failure incorrectly acknowledged");
        m.start();
        return m;
    }
    static void retainedPanelBlocksReload() {
        Plugin m=retainedAfterFailure();
        eq(m.panel,"unsaved");
        check(m.unreconciled && m.blockedRestores==1,
              "unverified panel was automatically restored");
        eq(m.disk.rows,"committed");
        passes++;
    }
    static void retainedPanelBlocksOverwrite() {
        Plugin m=retainedAfterFailure();m.disk.writable=true;
        int commits=m.disk.writes;
        m.stop();
        check(m.disk.writes==commits && m.blockedStopMerges==1,"unverified overwrite");
        eq(m.disk.rows,"committed");
        passes++;
    }
    static void retainedIdenticalDropCannotCollapse() {
        Plugin m=new Plugin();m.disk.rows.add("same");
        m.start();m.disk.writable=false;m.drop("same",true);m.stop();
        m.start();m.disk.writable=true;m.drop("same",true);m.stop();
        eq(m.disk.rows,"same");
        eq(m.panel,"same","same");
        check(m.blockedStopMerges>0,"ambiguous duplicate overwrite allowed");
        passes++;
    }
    static void retainedFurtherDropStillFailsClosed() {
        Plugin m=retainedAfterFailure();m.disk.writable=true;
        m.drop("later",true);m.stop();
        eq(m.disk.rows,"committed");
        eq(m.panel,"unsaved","later");
        passes++;
    }
    static void explicitClearAllowsRestart() {
        Plugin m=retainedAfterFailure();m.clear();
        check(!m.unreconciled && m.disk.rows.isEmpty(),"clear did not reset guard");
        m.disk.writable=true;
        m.drop("fresh",true);
        m.stop();
        eq(m.disk.rows,"fresh");passes++;
    }
    static void acknowledgedSaveResetsPanelNextStart() {
        Plugin m=new Plugin();m.disk.rows.add("old");m.start();m.runNextRestore();
        m.drop("new",true);m.stop();eq(m.disk.rows,"old","new");
        m.start();
        check(!m.unreconciled && m.panelSnapshot().isEmpty(),"saved panel not cleared");
        m.runNextRestore();eq(m.panel,"old","new");passes++;
    }
    static void corruptedInitialReadDoesNotOverwrite() {
        Plugin m=new Plugin();m.disk.rows.add("old");m.disk.readable=false;
        m.start();m.drop("new",true);m.stop();
        eq(m.disk.rows,"old");check(m.disk.writes==0,"corrupt history overwritten");
        passes++;
    }
    static void repeatedRestartDoesNotDuplicate() {
        Plugin m=retainedAfterFailure();m.start();m.start();
        eq(m.panel,"unsaved");
        check(m.blockedRestores==3,"stale panel did not block each restore");
        passes++;
    }
    static void separatePanelHistoryLocksDoNotDeadlock() throws Exception {
        final Object gate=new Object();
        final Object panel=new Object();
        final CountDownLatch panelHeld=new CountDownLatch(1);
        final CountDownLatch snapshotAttempted=new CountDownLatch(1);
        final AtomicBoolean acquiredGate=new AtomicBoolean(false);
        Thread panelThread=new Thread(()->{
            synchronized(panel) {
                panelHeld.countDown();
                try { check(snapshotAttempted.await(2,TimeUnit.SECONDS),"no snapshot thread"); }
                catch(InterruptedException e) { Thread.currentThread().interrupt(); return; }
                synchronized(gate) {acquiredGate.set(true);}
            }
        },"R398-Panel-Lock");
        Thread snapshotThread=new Thread(()->{
            try { check(panelHeld.await(2,TimeUnit.SECONDS),"no panel lock"); }
            catch(InterruptedException e) {Thread.currentThread().interrupt();return;}
            snapshotAttempted.countDown();
            synchronized(panel) { /* panel-only snapshot */ }
            synchronized(gate) { /* then read flags */ }
        },"R398-Snapshot");
        panelThread.setDaemon(true);snapshotThread.setDaemon(true);
        panelThread.start();snapshotThread.start();
        panelThread.join(3000);snapshotThread.join(3000);
        check(!panelThread.isAlive()&&!snapshotThread.isAlive()&&acquiredGate.get(),
              "lock-order regression deadlocked");
        passes++;
    }

    public static void main(String[] args) throws Exception {
        initialRestore();
        earlyCleanStopNoIO();
        normalDirtyStopCommits();
        pendingDropIncluded();
        twoSameNameDropsPreserved();
        retainedPanelBlocksReload();
        retainedPanelBlocksOverwrite();
        retainedIdenticalDropCannotCollapse();
        retainedFurtherDropStillFailsClosed();
        explicitClearAllowsRestart();
        acknowledgedSaveResetsPanelNextStart();
        corruptedInitialReadDoesNotOverwrite();
        repeatedRestartDoesNotDuplicate();
        separatePanelHistoryLocksDoNotDeadlock();
        System.out.println("R398_SYNTHETIC_PASS "+passes+" scenarios");
    }
}
