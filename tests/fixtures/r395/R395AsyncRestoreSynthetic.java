import javax.swing.SwingUtilities;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Queue;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Synthetic-only R395 test model. Not the recovered SpawnPK implementation.
 * No network, file I/O, private game code, client launch or real user data.
 */
public final class R395AsyncRestoreSynthetic {
    private R395AsyncRestoreSynthetic() {}

    static final class FakeGate {
        final Queue<Runnable> background = new ArrayDeque<Runnable>();
        final Queue<Runnable> edt = new ArrayDeque<Runnable>();
        final List<String> panel = new ArrayList<String>();
        final List<String> disk = new ArrayList<String>();
        final List<String> pending = new ArrayList<String>();

        int generation, reads, writes;
        boolean loaded, inFlight, writeDeferred, active, readFails;

        void start() {
            ++generation;
            active = true;
            loaded = false;
            inFlight = false;
            writeDeferred = false;
            panel.clear();
        }

        void requestRestore() {
            if (!active || loaded || inFlight) {
                return;
            }
            inFlight = true;
            final int issued = ++generation;
            ++reads;
            background.add(new Runnable() {
                @Override public void run() {
                    if (readFails) {
                        edt.add(new Runnable() {
                            @Override public void run() {
                                if (generation == issued) inFlight = false;
                            }
                        });
                        return;
                    }
                    final List<String> snapshot = new ArrayList<String>(disk);
                    edt.add(new Runnable() {
                        @Override public void run() {
                            if (!active || generation != issued || loaded) {
                                return;
                            }
                            panel.addAll(snapshot);
                            loaded = true;
                            inFlight = false;
                            final boolean deferred = writeDeferred;
                            writeDeferred = false;
                            if (deferred) save();
                        }
                    });
                }
            });
        }

        void save() {
            if (!loaded) {
                writeDeferred = true;
                return;
            }
            disk.clear();
            disk.addAll(panel);
            disk.addAll(pending);
            ++writes;
        }

        void drop(final String identifier) {
            pending.add(identifier);
            edt.add(new Runnable() {
                @Override public void run() {
                    panel.add(identifier);
                    pending.remove(identifier);
                }
            });
        }

        void clear() {
            ++generation;
            inFlight = false;
            writeDeferred = false;
            loaded = true;
            panel.clear();
            pending.clear();
            disk.clear();
        }

        void stop() {
            active = false;
            ++generation;
            inFlight = false;
            save();
        }

        void nextBackground() {
            check(!background.isEmpty(), "background queue unexpectedly empty");
            background.remove().run();
        }

        void nextEdt() {
            check(!edt.isEmpty(), "EDT queue unexpectedly empty");
            edt.remove().run();
        }
    }

    static int passed;

    static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    static void checkList(List<String> actual, String... expected) {
        check(actual.equals(Arrays.asList(expected)), "list mismatch: " + actual);
    }

    static void testNoWriteBeforeRestore() {
        FakeGate gate = new FakeGate();
        gate.disk.add("saved-record");
        gate.start();
        gate.requestRestore();
        gate.save();
        checkList(gate.disk, "saved-record");
        check(gate.writes == 0 && gate.writeDeferred, "early overwrite");
        gate.nextBackground();
        gate.nextEdt();
        checkList(gate.panel, "saved-record");
        checkList(gate.disk, "saved-record");
        check(gate.writes == 1 && gate.loaded, "deferred write not drained");
        ++passed;
    }

    static void testLiveDropDuringRestore() {
        FakeGate gate = new FakeGate();
        gate.disk.add("older-record");
        gate.start();
        gate.requestRestore();
        gate.drop("new-drop");
        gate.nextEdt(); // In-flight record delivery before disk read completes.
        gate.save();
        checkList(gate.disk, "older-record");
        gate.nextBackground();
        gate.nextEdt();
        checkList(gate.panel, "new-drop", "older-record");
        checkList(gate.disk, "new-drop", "older-record");
        check(gate.pending.isEmpty(), "live-drop buffer not drained");
        ++passed;
    }

    static void testPendingRecordIdentityPreserved() {
        FakeGate gate = new FakeGate();
        gate.disk.add("record-on-disk");
        gate.start();
        gate.requestRestore();
        gate.drop("pending-drop");
        gate.save();
        gate.nextBackground();
        // Applying restoration before the queued live-drop panel callback
        // must not discard the live pending record.
        Runnable restore = gate.edt.removeLast();
        restore.run();
        checkList(gate.disk, "record-on-disk", "pending-drop");
        gate.nextEdt();
        checkList(gate.panel, "record-on-disk", "pending-drop");
        ++passed;
    }

    static void testRepeatedLoadCoalesced() {
        FakeGate gate = new FakeGate();
        gate.start();
        gate.requestRestore();
        gate.requestRestore();
        gate.requestRestore();
        check(gate.reads == 1 && gate.background.size() == 1, "duplicate disk read");
        ++passed;
    }

    static void testClearInvalidatesQueuedRestore() {
        FakeGate gate = new FakeGate();
        gate.disk.add("must-not-reappear");
        gate.start();
        gate.requestRestore();
        gate.nextBackground();
        gate.clear();
        gate.nextEdt();
        check(gate.disk.isEmpty() && gate.panel.isEmpty(), "resurrected cleared data");
        ++passed;
    }

    static void testClearInvalidatesStillReading() {
        FakeGate gate = new FakeGate();
        gate.disk.add("must-not-reappear");
        gate.start();
        gate.requestRestore();
        gate.clear();
        gate.nextBackground();
        gate.nextEdt();
        check(gate.disk.isEmpty() && gate.panel.isEmpty(), "stale background apply");
        ++passed;
    }

    static void testStopInvalidatesOldGeneration() {
        FakeGate gate = new FakeGate();
        gate.disk.add("saved-record");
        gate.start();
        gate.requestRestore();
        gate.nextBackground();
        gate.stop();
        gate.nextEdt();
        check(gate.panel.isEmpty() && gate.disk.equals(Collections.singletonList("saved-record")),
              "stale plugin callback or unsafe overwrite");
        // Limitation: unsaved new drops on stop before load complete are not
        // guaranteed durable by the private experimental candidate.
        ++passed;
    }

    static void testRestartInvalidatesOldGeneration() {
        FakeGate gate = new FakeGate();
        gate.disk.add("saved-record");
        gate.start();
        gate.requestRestore();
        gate.nextBackground();
        gate.stop();
        gate.start();
        gate.nextEdt(); // stale callback from old plugin session
        check(gate.panel.isEmpty(), "cross-session restoration applied");
        gate.requestRestore();
        gate.nextBackground();
        gate.nextEdt();
        checkList(gate.panel, "saved-record");
        ++passed;
    }

    static void testFailedDiskReadPreservesOriginal() {
        FakeGate gate = new FakeGate();
        gate.disk.add("saved-record");
        gate.start();
        gate.readFails = true;
        gate.requestRestore();
        gate.save();
        gate.nextBackground();
        gate.nextEdt();
        checkList(gate.disk, "saved-record");
        check(gate.writes == 0 && !gate.loaded && !gate.inFlight,
              "failed read permitted overwrite");
        gate.readFails = false;
        gate.requestRestore();
        gate.nextBackground();
        gate.nextEdt();
        check(gate.loaded, "failed read prevented a controlled retry");
        ++passed;
    }

    static void testEmptyHistoryCompletes() {
        FakeGate gate = new FakeGate();
        gate.start();
        gate.requestRestore();
        gate.nextBackground();
        gate.nextEdt();
        check(gate.loaded && !gate.inFlight && gate.panel.isEmpty(),
              "empty disk history never completes");
        ++passed;
    }

    static void testHeadlessEdtStaysResponsiveDuringBlockedRead() throws Exception {
        System.setProperty("java.awt.headless", "true");
        final CountDownLatch loaderEntered = new CountDownLatch(1);
        final CountDownLatch releaseLoader = new CountDownLatch(1);
        final CountDownLatch uiExecuted = new CountDownLatch(1);
        final AtomicBoolean loaded = new AtomicBoolean(false);

        Thread simulatedDiskReader = new Thread(new Runnable() {
            @Override public void run() {
                loaderEntered.countDown();
                try {
                    if (!releaseLoader.await(3, TimeUnit.SECONDS)) {
                        return;
                    }
                    loaded.set(true);
                    SwingUtilities.invokeLater(new Runnable() {
                        @Override public void run() { /* apply complete */ }
                    });
                } catch (InterruptedException ignored) {
                    Thread.currentThread().interrupt();
                }
            }
        }, "R395-Synthetic-Background-Reader");
        simulatedDiskReader.setDaemon(true);
        simulatedDiskReader.start();
        check(loaderEntered.await(2, TimeUnit.SECONDS), "worker did not start");
        SwingUtilities.invokeLater(new Runnable() {
            @Override public void run() {
                uiExecuted.countDown();
            }
        });
        boolean responsive = uiExecuted.await(2, TimeUnit.SECONDS);
        releaseLoader.countDown();
        simulatedDiskReader.join(3000);
        check(responsive, "EDT stalled while background loader waited");
        check(loaded.get(), "background reader not released");
        ++passed;
    }

    public static void main(String[] args) throws Exception {
        testNoWriteBeforeRestore();
        testLiveDropDuringRestore();
        testPendingRecordIdentityPreserved();
        testRepeatedLoadCoalesced();
        testClearInvalidatesQueuedRestore();
        testClearInvalidatesStillReading();
        testStopInvalidatesOldGeneration();
        testRestartInvalidatesOldGeneration();
        testFailedDiskReadPreservesOriginal();
        testEmptyHistoryCompletes();
        testHeadlessEdtStaysResponsiveDuringBlockedRead();
        System.out.println("R395_SYNTHETIC_PASS " + passed + " cases");
        // Exit explicitly because Swing's EDT is a toolkit service.
        System.exit(0);
    }
}
