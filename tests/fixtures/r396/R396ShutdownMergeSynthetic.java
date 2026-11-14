import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

/**
 * R396 public synthetic-only model, not SpawnPK source.
 * Deterministic scheduling: no client, network, filesystem or private code.
 * A model passing does NOT validate the modified private Java runtime.
 */
public final class R396ShutdownMergeSynthetic {
    static int passed = 0;
    static void assertTrue(boolean ok, String why) {
        if (!ok) throw new AssertionError(why);
    }
    static void expect(List<String> got, String... names) {
        assertTrue(got.equals(Arrays.asList(names)), "Unexpected records: " + got);
    }
    static final class FakeStore {
        final List<String> disk = new ArrayList<>();
        boolean invalidRead;
        boolean commitFailure;
        int reads, writes;
        List<String> loadStrict() {
            reads++;
            return invalidRead ? null : new ArrayList<>(disk);
        }
        boolean saveVerified(List<String> next) {
            if (commitFailure) return false;
            disk.clear();
            disk.addAll(next);
            writes++;
            return true;
        }
    }
    static final class Model {
        final Object gate = new Object();
        final FakeStore store = new FakeStore();
        final ArrayDeque<Runnable> workers = new ArrayDeque<>();
        final ArrayDeque<Runnable> edt = new ArrayDeque<>();
        final List<String> panel = new ArrayList<>();
        final List<String> pending = new ArrayList<>();
        final List<String> preload = new ArrayList<>();
        boolean active, loaded, inflight, writeDeferred, resetOnRestart, lastCommit;
        int generation, shutdownSuccess;

        void start() {
            synchronized (gate) {
                generation++;
                active = true;
                loaded = false;
                inflight = false;
                writeDeferred = false;
                lastCommit = false;
                if (resetOnRestart) {
                    panel.clear();
                    resetOnRestart = false;
                }
            }
            requestRestore();
        }
        void requestRestore() {
            synchronized (gate) {
                if (!active || loaded || inflight) return;
                inflight = true;
                int ticket = ++generation;
                workers.add(() -> {
                    List<String> restored = store.loadStrict();
                    if (restored == null) {
                        edt.add(() -> {
                            synchronized (gate) {
                                if (ticket == generation) inflight = false;
                            }
                        });
                        return;
                    }
                    edt.add(() -> {
                        synchronized (gate) {
                            if (ticket != generation || !active || loaded) return;
                            panel.addAll(restored);
                            loaded = true;
                            inflight = false;
                            if (writeDeferred) {
                                writeDeferred = false;
                                persist();
                            }
                        }
                    });
                });
            }
        }
        void drop(String id) {
            synchronized (gate) {
                pending.add(id);
                lastCommit = false;
                if (!loaded) preload.add(id);
            }
            edt.add(() -> {
                panel.add(id);
                pending.remove(id);
            });
        }
        boolean persist() {
            if (!loaded) {
                writeDeferred = true;
                return false;
            }
            List<String> next = new ArrayList<>(panel);
            next.addAll(pending);
            if (!store.saveVerified(next)) return false;
            preload.clear();
            lastCommit = true;
            return true;
        }
        boolean finishStopMerge() {
            List<String> old = store.loadStrict();
            if (old == null) return false;
            List<String> next = new ArrayList<>(old);
            synchronized (gate) {
                next.addAll(preload);
            }
            if (!store.saveVerified(next)) return false;
            synchronized (gate) {
                loaded = true;
                inflight = false;
                writeDeferred = false;
                preload.clear();
                resetOnRestart = true;
                shutdownSuccess++;
            }
            return true;
        }
        void stop() {
            active = false;
            synchronized (gate) {
                generation++;
                inflight = false;
            }
            boolean merged = !loaded && finishStopMerge();
            if (!merged) {
                lastCommit = false;
                persist();
                resetOnRestart = lastCommit;
            }
        }
        void clear() {
            synchronized (gate) {
                generation++;
                loaded = true;
                inflight = false;
                writeDeferred = false;
                preload.clear();
                lastCommit = false;
            }
            pending.clear();
            panel.clear();
            store.disk.clear();
        }
        void runWorker() {
            assertTrue(!workers.isEmpty(), "No worker available");
            workers.removeFirst().run();
        }
        void runUi() {
            assertTrue(!edt.isEmpty(), "No EDT task available");
            edt.removeFirst().run();
        }
    }

    static void testStopBeforeRead() {
        Model m = new Model(); m.store.disk.add("old"); m.start(); m.drop("new");
        m.stop(); expect(m.store.disk, "old", "new");
        assertTrue(m.shutdownSuccess == 1, "No verified stop merge");
        passed++;
    }
    static void testStopAfterReadBeforeApply() {
        Model m = new Model(); m.store.disk.add("old"); m.start(); m.drop("new");
        m.runWorker(); m.stop(); m.runUi(); // drop panel callback may run first
        expect(m.store.disk, "old", "new");
        m.runUi(); // stale restoration callback
        expect(m.store.disk, "old", "new");
        passed++;
    }
    static void testStopAfterQueuedDropDelivery() {
        Model m = new Model(); m.store.disk.add("old"); m.start(); m.drop("new");
        m.runUi(); // new record is no longer pending
        m.stop(); expect(m.store.disk, "old", "new");
        passed++;
    }
    static void testIdenticalDropOccurrencesKept() {
        Model m = new Model(); m.store.disk.add("old"); m.start();
        m.drop("same"); m.drop("same"); m.runUi(); m.stop();
        expect(m.store.disk, "old", "same", "same");
        passed++;
    }
    static void testRepeatedRequestSingleWorker() {
        Model m = new Model(); m.start(); m.requestRestore(); m.requestRestore();
        assertTrue(m.workers.size() == 1, "Repeated request dispatched duplicate worker");
        passed++;
    }
    static void testReadFailurePreservesOriginal() {
        Model m = new Model(); m.store.disk.add("old"); m.store.invalidRead=true;
        m.start(); m.drop("new"); m.stop();
        expect(m.store.disk, "old");
        assertTrue(m.store.writes==0 && m.shutdownSuccess==0, "unsafe failure overwrite");
        passed++;
    }
    static void testSaveFailurePreservesOriginal() {
        Model m = new Model(); m.store.disk.add("old"); m.store.commitFailure=true;
        m.start(); m.drop("new"); m.stop();
        expect(m.store.disk, "old");
        assertTrue(!m.resetOnRestart && m.shutdownSuccess==0, "false save acknowledgement");
        passed++;
    }
    static void testRestartWithoutDuplicates() {
        Model m = new Model(); m.store.disk.add("old"); m.start(); m.drop("new");
        m.runUi(); m.stop(); m.start(); m.runWorker(); m.runUi();
        // Prior stale background worker is queued first and must not apply.
        m.runWorker(); m.runUi();
        expect(m.panel, "old", "new");
        expect(m.store.disk, "old", "new");
        passed++;
    }
    static void testClearMakesStaleReadInert() {
        Model m = new Model(); m.store.disk.add("old"); m.start();
        m.runWorker(); m.clear(); m.runUi();
        assertTrue(m.panel.isEmpty() && m.store.disk.isEmpty(), "clear resurrected loot");
        passed++;
    }
    static void testValidEmptyHistoryAndNewDrop() {
        Model m = new Model(); m.start(); m.drop("fresh"); m.stop();
        expect(m.store.disk, "fresh");
        passed++;
    }
    static void testSteadyStateShutdownSavesDeliveredLoot() {
        Model m = new Model(); m.store.disk.add("old"); m.start(); m.runWorker(); m.runUi();
        m.drop("fresh"); m.runUi(); m.stop();
        expect(m.store.disk, "old", "fresh");
        passed++;
    }
    static void testSteadyStateShutdownSavesPendingLoot() {
        Model m = new Model(); m.store.disk.add("old"); m.start(); m.runWorker(); m.runUi();
        m.drop("fresh"); m.stop();
        expect(m.store.disk, "old", "fresh");
        passed++;
    }
    static void testFailureDoesNotClaimDurability() {
        Model m = new Model(); m.store.disk.add("old"); m.store.invalidRead=true; m.start();
        m.drop("new"); m.stop();
        assertTrue(m.shutdownSuccess == 0 && m.preload.size() == 1,
            "failure should leave volatile preload pending, not assert durability");
        passed++;
    }
    public static void main(String[] args) {
        testStopBeforeRead();
        testStopAfterReadBeforeApply();
        testStopAfterQueuedDropDelivery();
        testIdenticalDropOccurrencesKept();
        testRepeatedRequestSingleWorker();
        testReadFailurePreservesOriginal();
        testSaveFailurePreservesOriginal();
        testRestartWithoutDuplicates();
        testClearMakesStaleReadInert();
        testValidEmptyHistoryAndNewDrop();
        testSteadyStateShutdownSavesDeliveredLoot();
        testSteadyStateShutdownSavesPendingLoot();
        testFailureDoesNotClaimDurability();
        System.out.println("R396_SYNTHETIC_PASS " + passed + " cases");
    }
}
