import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * R400 standalone, synthetic-only snapshot/handoff model.
 * No proprietary client source, no real history, no game process or files.
 * Deterministic injected interleavings show why R399's two independent
 * snapshots may both miss or double-count one transfer.
 */
public final class R400HandoffSnapshotSynthetic {
    static int passed;
    static void ok(boolean condition, String why) {
        if (!condition) throw new AssertionError(why);
    }
    static final class Drop {
        final int id;
        final String name;
        Drop(int id,String name) {this.id=id;this.name=name;}
        // Intentionally equal by title: only object identity is reliable.
        @Override public boolean equals(Object o) {
            return o instanceof Drop && name.equals(((Drop)o).name);
        }
        @Override public int hashCode() {return name.hashCode();}
    }
    static final class FakeStore {
        final List<Drop> disk = new ArrayList<>();
        boolean writable=true;
        int writes;
        boolean save(List<Drop> next) {
            if (!writable) return false;
            disk.clear();
            disk.addAll(next);
            writes++;
            return true;
        }
    }
    static final class Model {
        final Object gate=new Object();
        final List<Drop> panel=new ArrayList<>();
        final List<Drop> pending=new ArrayList<>();
        final List<Drop> preload=new ArrayList<>();
        final FakeStore store=new FakeStore();
        long handoffVersion,mutation;
        boolean unsafe,loaded=true,savePending,acknowledged;
        boolean inHandoff;
        int attempts,admitted;
        Runnable afterPanelRead, beforeCommit;

        Drop admit(int id,String name) {
            Drop d=new Drop(id,name);
            synchronized(gate) {
                mutation++;
                pending.add(d);
                admitted++;
                acknowledged=false;
            }
            return d;
        }
        boolean dropPendingByIdentity(Drop target) {
            synchronized(gate) {
                for (int i=0;i<pending.size();i++) {
                    if (pending.get(i)==target) {
                        pending.remove(i);
                        return true;
                    }
                }
            }
            return false;
        }
        void startHandoff() {
            synchronized(gate) {
                ok(!inHandoff,"nested synthetic handoff");
                inHandoff=true;
                ++handoffVersion; // odd
            }
        }
        void render(Drop d) {
            ok(!Thread.holdsLock(gate),"panel rendered while holding gate");
            panel.add(d);
        }
        void completeHandoff(Drop d) {
            dropPendingByIdentity(d);
            synchronized(gate) {
                ok(inHandoff,"handoff not started");
                inHandoff=false;
                ++handoffVersion; // even
            }
        }
        void fullHandoff(Drop d) {
            startHandoff();
            render(d);
            completeHandoff(d);
        }
        List<Drop> naiveSnapshot(Runnable midRead) {
            List<Drop> fromPanel=new ArrayList<>(panel);
            if (midRead!=null)midRead.run();
            fromPanel.addAll(pending);
            return fromPanel;
        }
        List<Drop> optimisticSnapshot() {
            for (int attempt=0;attempt<5;attempt++) {
                attempts++;
                final long begin;
                synchronized(gate) {
                    if (unsafe)return null;
                    begin=handoffVersion;
                }
                if ((begin&1L)!=0L) continue;
                ok(!Thread.holdsLock(gate),"panel snapshot under history gate");
                List<Drop> fromPanel=new ArrayList<>(panel);
                if (afterPanelRead!=null) {
                    Runnable hook=afterPanelRead;
                    afterPanelRead=null;
                    hook.run();
                }
                final List<Drop> fromPending;
                synchronized(gate) {
                    if (unsafe || begin!=handoffVersion ||
                            (handoffVersion&1L)!=0L)continue;
                    fromPending=new ArrayList<>(pending);
                }
                fromPanel.addAll(fromPending);
                return fromPanel;
            }
            savePending=true;
            return null;
        }
        boolean persist() {
            if (!loaded || unsafe) return false;
            List<Drop> snap=optimisticSnapshot();
            if (snap==null)return false;
            long snapMutation;
            synchronized(gate){snapMutation=mutation;}
            if (beforeCommit!=null) {
                Runnable hook=beforeCommit;beforeCommit=null;hook.run();
            }
            if (!store.save(snap))return false;
            synchronized(gate) {
                boolean unchanged=mutation==snapMutation;
                acknowledged=unchanged;
            }
            return true;
        }
        void unsafeHandoff() {
            startHandoff();
            try {
                throw new IllegalStateException("synthetic panel rendering failure");
            } catch(IllegalStateException expected) {
                synchronized(gate) {unsafe=true;}
            } finally {
                synchronized(gate) {
                    inHandoff=false;
                    ++handoffVersion;
                }
            }
        }
        void clear() {
            synchronized(gate) {
                unsafe=false;
                handoffVersion+=2L;
                pending.clear();
                preload.clear();
            }
            panel.clear();
            store.disk.clear();
        }
    }
    static void ids(List<Drop> actual,int... expected) {
        List<Integer> got=new ArrayList<>();
        for(Drop d:actual)got.add(d.id);
        List<Integer> want=new ArrayList<>();
        for(int id:expected)want.add(id);
        ok(got.equals(want),"got "+got+" expected "+want);
    }
    static void scenarioOriginalDoubleCount() {
        Model m=new Model();Drop d=m.admit(1,"same");
        // panel render happens between panel read and pending capture;
        // old algorithm sees the same logical drop twice.
        List<Drop> old=m.naiveSnapshot(()->{
            m.startHandoff();m.render(d);
        });
        ids(old,1); // panel read was before render, pending still contains it
        m.completeHandoff(d);
        // Reverse ordering can double-count: already rendered, pending
        // removal has not completed when both are read.
        Model n=new Model();Drop e=n.admit(2,"same");
        n.startHandoff();n.render(e);
        ids(n.naiveSnapshot(null),2,2);
        n.completeHandoff(e);
        passed++;
    }
    static void originalCanMissCompletedHandoff() {
        Model m=new Model();Drop d=m.admit(3,"missed");
        List<Drop> old=m.naiveSnapshot(()->m.fullHandoff(d));
        ok(old.isEmpty(),"reference interleaving did not miss row");
        passed++;
    }
    static void completeHandoffDuringSnapshotRetries() {
        Model m=new Model();Drop d=m.admit(4,"new");
        m.afterPanelRead=()->m.fullHandoff(d);
        ids(m.optimisticSnapshot(),4);
        ok(m.attempts==2,"missing optimistic retry");
        passed++;
    }
    static void unfinishedHandoffRetriesWithoutDoubleCount() {
        Model m=new Model();Drop d=m.admit(5,"half");
        m.afterPanelRead=()->{m.startHandoff();m.render(d);};
        List<Drop> snap=m.optimisticSnapshot();
        ok(snap==null && m.savePending,"in-flight handoff incorrectly saved");
        m.completeHandoff(d);
        ids(m.optimisticSnapshot(),5);
        passed++;
    }
    static void oddHandoffStartPreventsWrite() {
        Model m=new Model();Drop d=m.admit(6,"odd");
        m.startHandoff();
        ok(!m.persist() && m.store.writes==0,"odd handoff accepted");
        ok(m.savePending,"did not defer retry");
        m.render(d);m.completeHandoff(d);
        ok(m.persist(),"stable retry after completed handoff failed");
        ids(m.store.disk,6);
        passed++;
    }
    static void unchangedPanelAndPendingSnapshot() {
        Model m=new Model();m.admit(7,"pending");
        ok(m.persist(),"stable pending save failed");
        ids(m.store.disk,7);
        passed++;
    }
    static void panelOnlySnapshot() {
        Model m=new Model();m.panel.add(new Drop(8,"panel"));
        ok(m.persist(),"panel only save failed");
        ids(m.store.disk,8);
        passed++;
    }
    static void sameTitleDistinctIdsRemainDistinct() {
        Model m=new Model();Drop a=m.admit(9,"same"),b=m.admit(10,"same");
        ok(a.equals(b)&&a!=b,"identity contrast invalid");
        m.fullHandoff(a);
        ok(m.persist(),"commit rejected stable split panel/pending");
        ids(m.store.disk,9,10);
        passed++;
    }
    static void noHistoryWriteOnFiveFailedAttempts() {
        Model m=new Model();m.store.disk.add(new Drop(11,"original"));
        Drop d=m.admit(12,"volatile");
        m.startHandoff();
        ok(!m.persist()&&m.attempts==5,"retry budget not enforced");
        ids(m.store.disk,11);
        m.render(d);m.completeHandoff(d);
        passed++;
    }
    static void failureQuarantinesPartiallyRenderedHandoff() {
        Model m=new Model();m.store.disk.add(new Drop(13,"old"));
        m.admit(14,"new");
        m.unsafeHandoff();
        ok(m.unsafe && !m.persist() && m.store.writes==0,
            "failed handoff allowed disk overwrite");
        ids(m.store.disk,13);
        passed++;
    }
    static void explicitClearResetsQuarantineAndVersion() {
        Model m=new Model();m.unsafeHandoff();
        long before=m.handoffVersion;
        m.clear();
        ok(!m.unsafe && m.handoffVersion==before+2L,"clear did not invalidate snapshot");
        m.admit(15,"fresh");
        ok(m.persist(),"clear did not unblock valid save");
        ids(m.store.disk,15);
        passed++;
    }
    static void diskWriteFailureLeavesPreviousSnapshot() {
        Model m=new Model();m.store.disk.add(new Drop(16,"existing"));
        m.admit(17,"unsaved");m.store.writable=false;
        ok(!m.persist(),"disk failure incorrectly acknowledged");
        ids(m.store.disk,16);
        passed++;
    }
    static void newAdmissionAfterSnapshotRequiresLaterSave() {
        Model m=new Model();m.admit(18,"first");
        m.beforeCommit=()->m.admit(19,"newer");
        ok(m.persist(),"first commit should still finish");
        ok(!m.acknowledged,"newer drop incorrectly marked covered");
        ids(m.store.disk,18);
        ok(m.persist()&&m.acknowledged,"later snapshot not acknowledged");
        ids(m.store.disk,18,19);
        passed++;
    }
    static void handoffDuringWriteDoesNotDuplicate() {
        Model m=new Model();Drop d=m.admit(20,"during-write");
        m.beforeCommit=()->m.fullHandoff(d);
        ok(m.persist(),"initial stable snapshot failed");
        ids(m.store.disk,20);
        ok(m.persist(),"subsequent panel read failed");
        ids(m.store.disk,20);
        passed++;
    }
    static void realThreadSnapshotHandoffUsesNoNestedGate() throws Exception {
        final Model m=new Model();
        final Drop d=m.admit(21,"two-threads");
        final CountDownLatch sawPanelRead=new CountDownLatch(1);
        final CountDownLatch callbackDone=new CountDownLatch(1);
        final AtomicBoolean unsafeResult=new AtomicBoolean(false);
        m.afterPanelRead=()->{
            sawPanelRead.countDown();
            try {ok(callbackDone.await(3,TimeUnit.SECONDS),"callback thread timed out");}
            catch(InterruptedException error){Thread.currentThread().interrupt();throw new AssertionError(error);}
        };
        Thread callback=new Thread(()->{
            try {if(!sawPanelRead.await(3,TimeUnit.SECONDS))return;}
            catch(InterruptedException error){Thread.currentThread().interrupt();return;}
            m.fullHandoff(d);
            callbackDone.countDown();
        },"R400-synthetic-EDT");
        callback.setDaemon(true);callback.start();
        List<Drop> snap=m.optimisticSnapshot();
        callback.join(3000);
        unsafeResult.set(callback.isAlive());
        ok(!unsafeResult.get(),"handoff deadlocked with snapshot");
        ids(snap,21);
        ok(m.attempts==2,"cross-thread handoff was not retried");
        passed++;
    }
    static void multipleIndependentHandoffsYieldConsistentSnapshot() {
        Model m=new Model();
        Drop one=m.admit(22,"first");
        Drop two=m.admit(23,"second");
        m.fullHandoff(one);
        m.afterPanelRead=()->m.fullHandoff(two);
        ids(m.optimisticSnapshot(),22,23);
        passed++;
    }
    public static void main(String[] args) throws Exception {
        scenarioOriginalDoubleCount();
        originalCanMissCompletedHandoff();
        completeHandoffDuringSnapshotRetries();
        unfinishedHandoffRetriesWithoutDoubleCount();
        oddHandoffStartPreventsWrite();
        unchangedPanelAndPendingSnapshot();
        panelOnlySnapshot();
        sameTitleDistinctIdsRemainDistinct();
        noHistoryWriteOnFiveFailedAttempts();
        failureQuarantinesPartiallyRenderedHandoff();
        explicitClearResetsQuarantineAndVersion();
        diskWriteFailureLeavesPreviousSnapshot();
        newAdmissionAfterSnapshotRequiresLaterSave();
        handoffDuringWriteDoesNotDuplicate();
        realThreadSnapshotHandoffUsesNoNestedGate();
        multipleIndependentHandoffsYieldConsistentSnapshot();
        System.out.println("R400_SYNTHETIC_PASS "+passed+" cases");
    }
}
