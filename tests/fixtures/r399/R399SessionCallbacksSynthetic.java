import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * R399 standalone synthetic model. Does not link to or run recovered game code.
 * Models queued EDT callbacks, stop/restart epoch, object identity, and commit
 * acknowledgment. It cannot prove production disk durability or all races.
 */
public final class R399SessionCallbacksSynthetic {
    static int passed;

    static final class Drop {
        final int identity;
        final String label;
        Drop(int identity, String label) {
            this.identity = identity;
            this.label = label;
        }
        @Override public boolean equals(Object o) {
            // Deliberately mirror the risk of equality by apparent title.
            return o instanceof Drop && label.equals(((Drop)o).label);
        }
        @Override public int hashCode() { return label.hashCode(); }
        @Override public String toString() { return identity + ":" + label; }
    }

    static final class FakeDisk {
        final List<Drop> records = new ArrayList<>();
        boolean readable=true, writable=true;
        int reads,writes;
        List<Drop> read() {
            ++reads;
            return readable ? new ArrayList<>(records) : null;
        }
        boolean save(List<Drop> written) {
            if (!writable) return false;
            records.clear();
            records.addAll(written);
            ++writes;
            return true;
        }
    }

    static final class SyntheticPlugin {
        final Object gate = new Object();
        final FakeDisk disk = new FakeDisk();
        final List<Drop> panel = new ArrayList<>();
        final List<Drop> pending = new ArrayList<>();
        final List<Drop> preload = new ArrayList<>();
        final ArrayDeque<Runnable> edt = new ArrayDeque<>();
        long sessionEpoch, mutation;
        boolean active, loaded, unresolved, resetAfterVerified;
        boolean lastCommitSucceeded;
        int nextIdentity, suppressedCallbacks, deliveredCallbacks, saveRequests, rejectedAdmissions;
        Runnable beforeSaveReceiptHook;

        void start() {
            synchronized(gate) {
                ++sessionEpoch;
                active=true;
                loaded=false;
                lastCommitSucceeded=false;
                if (resetAfterVerified) {
                    panel.clear();
                    resetAfterVerified=false;
                }
                unresolved=!panel.isEmpty()||!pending.isEmpty()||!preload.isEmpty();
            }
            if (!unresolved) restore();
        }

        void restore() {
            if (unresolved || !active) return;
            List<Drop> old=disk.read();
            if (old==null) return;
            panel.addAll(old);
            loaded=true;
        }

        Drop drop(String label) {
            final Drop entry;
            final long issued;
            synchronized(gate) {
                if (!active) {
                    ++rejectedAdmissions;
                    return null;
                }
                issued=sessionEpoch;
                entry=new Drop(++nextIdentity,label);
                ++mutation;
                lastCommitSucceeded=false;
                pending.add(entry);
                if (!loaded) preload.add(entry);
            }
            edt.add(()->{
                synchronized(gate) {
                    if (!active || issued!=sessionEpoch) {
                        ++suppressedCallbacks;
                        return;
                    }
                }
                panel.add(entry);
                synchronized(gate) { removeIdentity(pending,entry); }
                ++deliveredCallbacks;
                ++saveRequests;
            });
            return entry;
        }

        static boolean removeIdentity(List<Drop> records, Drop target) {
            for (int i=0;i<records.size();i++) {
                if (records.get(i)==target) {
                    records.remove(i);
                    return true;
                }
            }
            return false;
        }

        boolean persist() {
            if (!loaded) return false;
            List<Drop> output=new ArrayList<>(panel);
            final List<Drop> pendingSnapshot;
            final long snapMutation;
            synchronized(gate) {
                pendingSnapshot=new ArrayList<>(pending);
                snapMutation=mutation;
            }
            output.addAll(pendingSnapshot);
            if (beforeSaveReceiptHook!=null) {
                Runnable hook=beforeSaveReceiptHook;
                beforeSaveReceiptHook=null;
                hook.run();
            }
            if (!disk.save(output)) return false;
            synchronized(gate) {
                for (Drop written:pendingSnapshot) removeIdentity(pending,written);
                boolean unchanged=(mutation==snapMutation);
                if (unchanged) preload.clear();
                lastCommitSucceeded=unchanged;
            }
            return true;
        }

        boolean mergePreloadAtStop() {
            if (unresolved) return false;
            if (panel.isEmpty() && pending.isEmpty() && preload.isEmpty()) return true;
            List<Drop> original=disk.read();
            if (original==null) return false;
            final List<Drop> snapshot;
            synchronized(gate) {
                snapshot=new ArrayList<>(preload);
                original.addAll(snapshot);
            }
            if (!disk.save(original)) return false;
            synchronized(gate) {
                for (Drop written:snapshot) removeIdentity(pending,written);
                preload.clear();
                loaded=true;
                resetAfterVerified=true;
            }
            return true;
        }

        void stop() {
            synchronized(gate) {
                ++sessionEpoch;
                active=false;
            }
            boolean success=loaded ? persist() : mergePreloadAtStop();
            if (loaded && success) resetAfterVerified=lastCommitSucceeded;
        }
        void clearHistory() {
            synchronized(gate) {
                ++sessionEpoch;
                pending.clear();
                preload.clear();
                unresolved=false;
            }
            panel.clear();
            disk.records.clear();
            loaded=true;
        }
        void drain() {
            while (!edt.isEmpty()) edt.removeFirst().run();
        }
    }

    static void assertTrue(boolean value, String why) {
        if (!value) throw new AssertionError(why);
    }
    static void expectIds(List<Drop> actual,int... identities) {
        List<Integer> ids=new ArrayList<>();
        for(Drop d:actual) ids.add(d.identity);
        List<Integer> expected=new ArrayList<>();
        for(int id:identities) expected.add(id);
        assertTrue(ids.equals(expected),"actual="+ids+" expected="+expected);
    }

    static void oldCallbackSkippedAfterVerifiedStopAndRestart() {
        SyntheticPlugin p=new SyntheticPlugin();
        p.start();
        Drop old=p.drop("duplicate");
        p.stop();
        expectIds(p.disk.records,old.identity);
        p.start();
        p.drain(); // old EDT callback queued before restart
        expectIds(p.panel,old.identity);
        assertTrue(p.deliveredCallbacks==0 && p.suppressedCallbacks==1
                   && p.saveRequests==0,"old callback was delivered");
        passed++;
    }

    static void oldCallbackSkippedWhileStopped() {
        SyntheticPlugin p=new SyntheticPlugin();
        p.start();p.drop("old");p.stop();p.drain();
        assertTrue(p.deliveredCallbacks==0 && p.suppressedCallbacks==1,
                   "old callback mutated stopped panel");
        passed++;
    }

    static void currentCallbackDeliveredOnlyOnce() {
        SyntheticPlugin p=new SyntheticPlugin();
        p.start();
        Drop d=p.drop("current");
        p.drain();
        expectIds(p.panel,d.identity);
        assertTrue(p.deliveredCallbacks==1 && p.saveRequests==1
                   && p.pending.isEmpty(),"active callback not delivered once");
        passed++;
    }

    static void saveAcknowledgementDrainsOnlyIdentity() {
        SyntheticPlugin p=new SyntheticPlugin();
        p.start();
        Drop a=p.drop("same");
        Drop b=p.drop("same");
        assertTrue(a.equals(b) && a!=b,"test does not model equality alias");
        p.stop();
        expectIds(p.disk.records,a.identity,b.identity);
        assertTrue(p.pending.isEmpty(),"committed identity not drained");
        p.start();p.drain();
        expectIds(p.panel,a.identity,b.identity);
        passed++;
    }

    static void failedStopRetainsPendingAndBlocksRestore() {
        SyntheticPlugin p=new SyntheticPlugin();
        p.start();
        p.disk.writable=false;
        Drop d=p.drop("retained");
        p.stop();
        assertTrue(p.pending.size()==1 && p.pending.get(0)==d,"failed drop discarded");
        p.start();
        assertTrue(p.unresolved && p.disk.reads==2,"unverified pending allowed reread");
        p.drain();
        assertTrue(p.suppressedCallbacks==1 && p.panel.isEmpty(),"stale UI rendered");
        passed++;
    }

    static void pendingWithEmptyPanelStillBlocksReread() {
        SyntheticPlugin p=new SyntheticPlugin();
        p.start();p.disk.writable=false;p.drop("pending");p.stop();
        p.start();
        assertTrue(p.unresolved && p.panel.isEmpty(),"empty panel hid pending records");
        passed++;
    }

    static void newSessionCallbackSurvivesOldCallback() {
        SyntheticPlugin p=new SyntheticPlugin();
        p.start();Drop old=p.drop("old");p.stop();p.start();
        Drop next=p.drop("new");
        p.drain();
        expectIds(p.panel,old.identity,next.identity);
        assertTrue(p.suppressedCallbacks==1 && p.deliveredCallbacks==1,
                   "incorrect epoch made active callback stale");
        passed++;
    }

    static void admissionAfterShutdownRefused() {
        SyntheticPlugin p=new SyntheticPlugin();
        p.start();p.stop();
        assertTrue(p.drop("late")==null && p.rejectedAdmissions==1,
                   "post-stop admission permitted");
        assertTrue(p.pending.isEmpty() && p.preload.isEmpty(),
                   "post-stop record leaked into persistence");
        passed++;
    }

    static void failedCommitDoesNotDrain() {
        SyntheticPlugin p=new SyntheticPlugin();
        p.start();p.disk.writable=false;Drop d=p.drop("new");
        p.stop();expectIds(p.pending,d.identity);
        assertTrue(!p.resetAfterVerified,"false commit receipt allowed reset");
        passed++;
    }

    static void newArrivalDuringWritePreventsFalseCleanCommit() {
        SyntheticPlugin p=new SyntheticPlugin();
        p.start();
        final Drop a=p.drop("first");
        p.drain(); // panel has first
        p.beforeSaveReceiptHook=()->p.drop("arrived-after-snapshot");
        p.persist();
        expectIds(p.disk.records,a.identity);
        assertTrue(!p.lastCommitSucceeded,"mid-save mutation incorrectly marked clean");
        assertTrue(p.pending.size()==1,"new mid-save event dropped");
        p.drain();
        p.persist();
        assertTrue(p.lastCommitSucceeded,"subsequent complete save not acknowledged");
        expectIds(p.disk.records,1,2);
        passed++;
    }

    static void injectedWriteFailureNeverAcknowledged() {
        SyntheticPlugin p=new SyntheticPlugin();
        p.start();p.disk.writable=false;
        p.drop("first");p.drain();
        assertTrue(!p.persist(),"failed write returned success");
        assertTrue(!p.lastCommitSucceeded,"failed write acknowledged");
        passed++;
    }

    static void pendingRemainsDistinctFromCommittedSameTitle() {
        SyntheticPlugin p=new SyntheticPlugin();
        p.start();Drop first=p.drop("same");p.stop();p.start();
        Drop second=p.drop("same");
        p.drain();
        expectIds(p.panel,first.identity,second.identity);
        assertTrue(first.equals(second) && first!=second,"duplicate identity lost");
        p.stop();expectIds(p.disk.records,first.identity,second.identity);
        passed++;
    }

    static void explicitClearUnblocksReread() {
        SyntheticPlugin p=new SyntheticPlugin();
        p.start();p.disk.writable=false;p.drop("old");p.stop();p.start();
        assertTrue(p.unresolved,"test lacks unresolved status");
        p.clearHistory();
        p.start();
        assertTrue(!p.unresolved,"clear did not lift unresolved status");
        passed++;
    }

    static void callbackAfterFailedStopCannotRequestSave() {
        SyntheticPlugin p=new SyntheticPlugin();
        p.start();p.disk.writable=false;p.drop("unsaved");p.stop();
        int writes=p.disk.writes;
        p.drain();
        assertTrue(p.disk.writes==writes && p.saveRequests==0,
                   "late callback requested new save");
        passed++;
    }

    static void closeAdmissionBeforeMerge() {
        SyntheticPlugin p=new SyntheticPlugin();
        p.start();p.drop("saved");
        p.stop();
        checkAfterStop(p);
        passed++;
    }

    static void checkAfterStop(SyntheticPlugin p) {
        assertTrue(!p.active,"admission remained open");
        expectIds(p.disk.records,1);
        assertTrue(p.drop("late")==null,"post-stop drop accepted");
        expectIds(p.disk.records,1);
    }

    static void standaloneRealThreadEpochVisibility() throws Exception {
        // Synthetic concurrent admission uses the same gate for mutation.
        final SyntheticPlugin p=new SyntheticPlugin();
        p.start();
        final CountDownLatch workerReady=new CountDownLatch(1);
        final CountDownLatch release=new CountDownLatch(1);
        final AtomicBoolean admitted=new AtomicBoolean(false);
        Thread sender=new Thread(()->{
            workerReady.countDown();
            try {if (!release.await(3,TimeUnit.SECONDS)) return;}
            catch(InterruptedException ex){Thread.currentThread().interrupt();return;}
            admitted.set(p.drop("too-late")!=null);
        },"R399-Synthetic-Client-Thread");
        sender.setDaemon(true);sender.start();
        assertTrue(workerReady.await(2,TimeUnit.SECONDS),"sender did not start");
        p.stop();release.countDown();sender.join(3000);
        assertTrue(!sender.isAlive() && !admitted.get(),
                   "post-stop racing sender admitted loot");
        passed++;
    }

    public static void main(String[] args) throws Exception {
        oldCallbackSkippedAfterVerifiedStopAndRestart();
        oldCallbackSkippedWhileStopped();
        currentCallbackDeliveredOnlyOnce();
        saveAcknowledgementDrainsOnlyIdentity();
        failedStopRetainsPendingAndBlocksRestore();
        pendingWithEmptyPanelStillBlocksReread();
        newSessionCallbackSurvivesOldCallback();
        admissionAfterShutdownRefused();
        failedCommitDoesNotDrain();
        newArrivalDuringWritePreventsFalseCleanCommit();
        injectedWriteFailureNeverAcknowledged();
        pendingRemainsDistinctFromCommittedSameTitle();
        explicitClearUnblocksReread();
        callbackAfterFailedStopCannotRequestSave();
        closeAdmissionBeforeMerge();
        standaloneRealThreadEpochVisibility();
        System.out.println("R399_SYNTHETIC_PASS "+passed+" cases");
    }
}
