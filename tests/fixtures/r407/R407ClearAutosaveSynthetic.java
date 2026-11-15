import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * R407 standalone invented autosave-admission and Clear-all interleaving model.
 * No original client code, private classes, history files or network access.
 */
public final class R407ClearAutosaveSynthetic {
    static int passed;
    static void ok(boolean value,String why) {
        if(!value) throw new AssertionError(why);
    }
    static void await(CountDownLatch latch,String label) {
        try {ok(latch.await(4,TimeUnit.SECONDS),"timeout: "+label);}
        catch(InterruptedException e) {Thread.currentThread().interrupt();throw new AssertionError(e);}
    }
    static void join(Thread t,String label) {
        try {t.join(4000);}
        catch(InterruptedException e) {Thread.currentThread().interrupt();throw new AssertionError(e);}
        ok(!t.isAlive(),"thread remained blocked: "+label);
    }
    static void rows(List<String> actual,String... expected) {
        ok(actual.equals(Arrays.asList(expected)),
            "actual="+actual+" expected="+Arrays.asList(expected));
    }
    static final class Work {
        final long epoch;
        boolean started;
        Work(long e) {epoch=e;}
    }
    static final class M {
        final Object historyGate=new Object();
        final Object fileGate=new Object();
        final List<String> panel=new ArrayList<>();
        final List<String> disk=new ArrayList<>();
        long epoch=10L;
        boolean accepting=true,queued,dirty,pending,clearInProgress,unsafe;
        boolean lastCommit;
        int attempts,successfulCommits,failedClears,cleanups;
        M(String... initial) {
            panel.addAll(Arrays.asList(initial));
            disk.addAll(Arrays.asList(initial));
        }
        Work request() {
            synchronized(historyGate) {
                if(!accepting||clearInProgress||unsafe) {
                    pending=true;
                    return null;
                }
                if(queued) {
                    dirty=true;
                    return null;
                }
                queued=true;
                dirty=false;
                pending=false;
                return new Work(epoch);
            }
        }
        boolean start(Work w) {
            synchronized(historyGate) {
                if(w.epoch!=epoch||!accepting)return false;
                // R407: check epoch and reset attempt receipt atomically.
                lastCommit=false;
                w.started=true;
                return true;
            }
        }
        boolean commit(Work w,List<String> snapshot) {
            synchronized(fileGate) {
                synchronized(historyGate) {
                    if(w.epoch!=epoch||!accepting||unsafe||clearInProgress)
                        return false;
                }
                disk.clear();disk.addAll(snapshot);
                successfulCommits++;
                synchronized(historyGate) {lastCommit=true;}
                return true;
            }
        }
        void complete(Work w,boolean threw) {
            synchronized(historyGate) {
                if(threw && w.epoch==epoch && accepting &&
                   !clearInProgress && !unsafe) {
                    pending=true;
                }
                // Old worker may not undo new session's queue state.
                if(w.epoch==epoch) {
                    if(dirty)pending=true;
                    queued=false;
                    dirty=false;
                    cleanups++;
                }
            }
        }
        boolean clear(boolean diskDeleteSucceeded) {
            return clear(diskDeleteSucceeded,()->{});
        }
        boolean clear(boolean diskDeleteSucceeded,Runnable afterEpochAdvance) {
            synchronized(historyGate) {
                if(clearInProgress)return false;
                clearInProgress=true;
                epoch++;
                queued=false;
                dirty=false;
                afterEpochAdvance.run();
            }
            synchronized(fileGate) {
                if(!diskDeleteSucceeded) {
                    synchronized(historyGate) {
                        unsafe=true;
                        clearInProgress=false;
                        failedClears++;
                    }
                    return false;
                }
                disk.clear();
                successfulCommits++;
            }
            synchronized(historyGate) {
                panel.clear();
                pending=false;
                unsafe=false;
                clearInProgress=false;
                lastCommit=false;
            }
            return true;
        }
        void add(String item) {
            synchronized(historyGate) {
                panel.add(item);
                pending=true;
            }
        }
        void restart() {
            synchronized(historyGate) {
                epoch++;
                queued=false;
                dirty=false;
                accepting=true;
                pending=false;
            }
        }
        void stop() {
            synchronized(historyGate) {
                epoch++;
                accepting=false;
            }
        }
        List<String> panelCopy(){synchronized(historyGate){return new ArrayList<>(panel);}}
        List<String> diskCopy(){synchronized(fileGate){return new ArrayList<>(disk);}}
    }

    static void clearQueuedOldWorkResetsAdmission() {
        M m=new M("A");
        Work old=m.request();
        ok(old!=null&&m.queued,"old work not queued");
        ok(m.clear(true),"clear refused");
        ok(!m.queued&&!m.dirty&&!m.pending,"clear retained old queue");
        rows(m.diskCopy());
        passed++;
    }
    static void staleCompletionDoesNotRestoreFlagAfterClear() {
        M m=new M("A");Work old=m.request();m.clear(true);
        m.complete(old,false);
        ok(!m.queued&&!m.pending&&!m.dirty,"old completion changed fresh session");
        passed++;
    }
    static void postClearNewDropCanEnqueue() {
        M m=new M("A");Work old=m.request();m.clear(true);
        m.add("new");
        Work fresh=m.request();
        ok(fresh!=null&&fresh.epoch!=old.epoch,"new drop still stranded");
        ok(m.start(fresh),"new worker start");
        ok(m.commit(fresh,m.panelCopy()),"new worker write");
        m.complete(old,false);
        ok(m.queued,"old worker cleared new worker flag");
        m.complete(fresh,false);
        rows(m.diskCopy(),"new");
        ok(!m.queued&&!m.pending,"new work not finalized");
        passed++;
    }
    static void staleExceptionDoesNotDirtySuccessfulClear() {
        M m=new M("A");Work old=m.request();m.clear(true);
        m.complete(old,true);
        ok(!m.pending&&!m.queued,"stale exception dirtied cleared history");
        rows(m.diskCopy());passed++;
    }
    static void currentExceptionPreservesRetry() {
        M m=new M("A");Work w=m.request();
        ok(m.start(w),"start failed");
        m.complete(w,true);
        ok(m.pending&&!m.queued,"current exception was lost");
        passed++;
    }
    static void oldWorkerCannotStartAfterClear() {
        M m=new M("A");Work old=m.request();
        m.clear(true);
        ok(!m.start(old),"stale worker reset new receipt");
        rows(m.diskCopy());passed++;
    }
    static void oldWorkerCannotCommitAfterClear() {
        M m=new M("A");Work old=m.request();
        ok(m.start(old),"start");
        List<String> stale=m.panelCopy();
        m.clear(true);
        ok(!m.commit(old,stale),"stale worker recreated deleted history");
        rows(m.diskCopy());passed++;
    }
    static void failedClearPreservesHistoryAndQuarantines() {
        M m=new M("A");Work old=m.request();
        ok(!m.clear(false),"failed clear acknowledged success");
        rows(m.panelCopy(),"A");rows(m.diskCopy(),"A");
        ok(m.unsafe&&!m.queued&&!m.dirty&&m.failedClears==1,
            "failed clear queue or unsafe state wrong");
        m.complete(old,true);
        ok(!m.pending,"old failed worker may not dirty quarantine");
        passed++;
    }
    static void failedClearRefusesAutomaticWrites() {
        M m=new M("A");m.request();m.clear(false);
        ok(m.request()==null,"unsafe history accepted autosave");
        Work stale=new Work(m.epoch);
        ok(!m.commit(stale,m.panelCopy()),"unsafe history committed");
        rows(m.diskCopy(),"A");
        passed++;
    }
    static void explicitSuccessfulRetryRecoversFromFailedClear() {
        M m=new M("A");m.request();m.clear(false);
        ok(m.clear(true),"explicit retry failed");
        ok(!m.unsafe&&!m.queued&&!m.pending,"retry not recovered");
        m.add("B");Work w=m.request();
        ok(w!=null&&m.start(w)&&m.commit(w,m.panelCopy()),"postretry save failed");
        m.complete(w,false);
        rows(m.diskCopy(),"B");
        passed++;
    }
    static void successfulClearDoesNotRecreateEmptyFile() {
        M m=new M("A");Work old=m.request();m.clear(true);m.complete(old,false);
        ok(m.successfulCommits==1,"unrequested post-clear write");
        rows(m.diskCopy());passed++;
    }
    static void burstCoalescingPreserved() {
        M m=new M("A");Work first=m.request();
        for(int i=0;i<30;i++)ok(m.request()==null,"extra autosave admitted");
        ok(first!=null&&m.queued&&m.dirty,"burst not coalesced");
        m.complete(first,false);
        ok(!m.queued&&m.pending,"trailing save not preserved");
        passed++;
    }
    static void clearWhileWorkerDirtyDropsOldDirtyFlag() {
        M m=new M("A");Work old=m.request();m.request();
        ok(m.dirty,"setup");
        m.clear(true);m.complete(old,false);
        ok(!m.dirty&&!m.pending&&!m.queued,"old dirty request survived");
        passed++;
    }
    static void oldWorkerCannotClearNewCoalescedQueue() {
        M m=new M("A");Work old=m.request();m.clear(true);
        m.add("N");Work newer=m.request();m.request();
        ok(m.queued&&m.dirty,"new queue setup");
        m.complete(old,false);
        ok(m.queued&&m.dirty,"old worker modified new dirty/queued flags");
        m.complete(newer,false);
        ok(m.pending&&!m.queued&&!m.dirty,"new worker trailing request lost");
        passed++;
    }
    static void stopPreventsNewWork() {
        M m=new M("A");m.stop();
        ok(m.request()==null,"stopped session admitted work");
        passed++;
    }
    static void restartFencesPriorWorker() {
        M m=new M("A");Work old=m.request();m.stop();m.restart();
        Work fresh=m.request();
        ok(fresh!=null&&fresh.epoch!=old.epoch,"restart did not fence old worker");
        m.complete(old,true);
        ok(m.queued&&!m.pending,"old worker modified restarted queue");
        m.complete(fresh,false);passed++;
    }
    static void currentReceiptResetCannotBeMadeByStaleWorker() {
        M m=new M("A");Work old=m.request();m.clear(true);
        m.lastCommit=true;
        ok(!m.start(old),"stale worker accepted");
        ok(m.lastCommit,"stale worker reset new receipt");
        passed++;
    }
    static void clearDoesNotInterruptInFlightWrite() throws Exception {
        M m=new M("A");
        Work old=m.request();ok(m.start(old),"old worker");
        CountDownLatch owner=new CountDownLatch(1),release=new CountDownLatch(1),
            epochMoved=new CountDownLatch(1);
        Thread writer=new Thread(()->{
            synchronized(m.fileGate) {
                owner.countDown();
                await(release,"release blocked disk writer");
                m.disk.clear();m.disk.add("A");
                m.successfulCommits++;
            }
            m.complete(old,false);
        },"R407-synthetic-autosave");
        writer.setDaemon(true);writer.start();await(owner,"old file gate");
        AtomicBoolean cleared=new AtomicBoolean(false);
        Thread clear=new Thread(()->cleared.set(m.clear(true,epochMoved::countDown)),
                                "R407-synthetic-EDT-clear");
        clear.setDaemon(true);clear.start();
        await(epochMoved,"clear advanced epoch");
        ok(!m.queued&&!m.dirty,"clear did not reset queue while file gate busy");
        release.countDown();
        join(writer,"worker");join(clear,"clear");
        ok(cleared.get(),"clear not committed");
        rows(m.diskCopy());rows(m.panelCopy());
        ok(!m.queued&&!m.pending&&!m.unsafe,"stale cleanup after clear changed state");
        passed++;
    }
    static void newWorkQueuedBehindOldWorkerAfterClear() {
        // Executor ordering is separate from logical admission. New
        // post-clear requests may queue behind an old, stale worker.
        M m=new M("A");Work old=m.request();m.clear(true);
        m.add("B");Work fresh=m.request();
        ok(fresh!=null&&fresh.epoch!=old.epoch,"new admission blocked");
        ok(!m.start(old),"old queued task started after epoch changed");
        m.complete(old,false);
        ok(m.queued,"old final cleared new task");
        ok(m.start(fresh)&&m.commit(fresh,m.panelCopy()),"fresh work failed");
        m.complete(fresh,false);rows(m.diskCopy(),"B");passed++;
    }
    static void repeatedClearMaintainsFreshEpoch() {
        M m=new M("A");Work old=m.request();
        long before=m.epoch;
        m.clear(true);m.clear(true);
        ok(m.epoch==before+2,"clear epochs not monotonic");
        m.complete(old,true);
        ok(!m.queued&&!m.pending,"double clear got dirty");
        passed++;
    }
    static void admissionDuringClearIsDeferred() {
        M m=new M("A");
        synchronized(m.historyGate) {
            m.clearInProgress=true;
            ok(m.request()==null&&m.pending,"new request during clear not deferred");
            m.clearInProgress=false;
        }
        passed++;
    }
    static void failedWriteInNewEpochRetryRemainsPending() {
        M m=new M("A");m.request();m.clear(true);
        m.add("B");Work w=m.request();ok(m.start(w),"new epoch start");
        // Simulate failed storage without a positive commit receipt.
        m.complete(w,true);
        ok(m.pending&&!m.queued&&!m.unsafe,"new epoch failure not retryable");
        rows(m.diskCopy());passed++;
    }
    public static void main(String[] args) throws Exception {
        clearQueuedOldWorkResetsAdmission();
        staleCompletionDoesNotRestoreFlagAfterClear();
        postClearNewDropCanEnqueue();
        staleExceptionDoesNotDirtySuccessfulClear();
        currentExceptionPreservesRetry();
        oldWorkerCannotStartAfterClear();
        oldWorkerCannotCommitAfterClear();
        failedClearPreservesHistoryAndQuarantines();
        failedClearRefusesAutomaticWrites();
        explicitSuccessfulRetryRecoversFromFailedClear();
        successfulClearDoesNotRecreateEmptyFile();
        burstCoalescingPreserved();
        clearWhileWorkerDirtyDropsOldDirtyFlag();
        oldWorkerCannotClearNewCoalescedQueue();
        stopPreventsNewWork();
        restartFencesPriorWorker();
        currentReceiptResetCannotBeMadeByStaleWorker();
        clearDoesNotInterruptInFlightWrite();
        newWorkQueuedBehindOldWorkerAfterClear();
        repeatedClearMaintainsFreshEpoch();
        admissionDuringClearIsDeferred();
        failedWriteInNewEpochRetryRemainsPending();
        System.out.println("R407_SYNTHETIC_PASS "+passed+" scenarios");
    }
}
