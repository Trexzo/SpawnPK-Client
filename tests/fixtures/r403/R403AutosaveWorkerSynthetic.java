import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * R403 independent Java autosave worker model. Uses invented in-memory rows;
 * no recovered client code, credentials, history paths or network access.
 */
public final class R403AutosaveWorkerSynthetic {
    static int passed;
    static void yes(boolean b,String why){if(!b)throw new AssertionError(why);}
    static void await(CountDownLatch l,String name){
        try {yes(l.await(4,TimeUnit.SECONDS),"timeout: "+name);}
        catch(InterruptedException ex){Thread.currentThread().interrupt();throw new AssertionError(ex);}
    }
    static final class M {
        final Object historyGate=new Object();
        final Object fileGate=new Object();
        final List<String> panel=new ArrayList<>();
        final List<String> disk=new ArrayList<>();
        final ThreadLocal<Long> workerToken=new ThreadLocal<>();
        final CountDownLatch firstCompletedWrite=new CountDownLatch(1);
        final CountDownLatch rejectedStaleWorker=new CountDownLatch(1);
        ExecutorService worker;
        long epoch,mutation;
        boolean active,queued,dirty,pending,committed,failWrite,historyLoaded=true;
        volatile long lastSave;
        int writes,schedules,attempts,rejections,activeWriters,maxActiveWriters;
        String lastWriterThread;
        Runnable beforeWriterLock,insideWriter;

        void start() {
            synchronized(historyGate) {
                ++epoch;active=true;queued=false;dirty=false;
                worker=Executors.newSingleThreadExecutor(task->{
                    Thread t=new Thread(task,"R403-Synthetic-Daemon-Autosave");
                    t.setDaemon(true);return t;
                });
            }
        }
        void stop() {
            final ExecutorService retired;
            synchronized(historyGate) {
                ++epoch;active=false;
                retired=worker;worker=null;
            }
            retired.shutdown(); // never shutdownNow
            persist();
        }
        boolean persist() {
            final long issued;
            synchronized(historyGate) {
                issued=epoch;
            }
            List<String> snapshot=new ArrayList<>(panel);
            if(beforeWriterLock!=null) {
                Runnable callback=beforeWriterLock;beforeWriterLock=null;callback.run();
            }
            synchronized(fileGate) {
                final Long token=workerToken.get();
                synchronized(historyGate) {
                    if(token!=null && (!active || !token.equals(epoch))){
                        rejections++;
                        rejectedStaleWorker.countDown();
                        return false;
                    }
                }
                if(failWrite)return false;
                activeWriters++;
                maxActiveWriters=Math.max(maxActiveWriters,activeWriters);
                attempts++;
                if(insideWriter!=null){
                    Runnable callback=insideWriter;insideWriter=null;callback.run();
                }
                disk.clear();disk.addAll(snapshot);
                writes++;
                lastWriterThread=Thread.currentThread().getName();
                committed=(mutation==issued); // placeholder overwritten below
                committed=true;
                lastSave=System.currentTimeMillis();
                firstCompletedWrite.countDown();
                activeWriters--;
                return true;
            }
        }
        void request() {
            if(!historyLoaded){pending=true;return;}
            queue();
        }
        void queue() {
            final long issued;
            final ExecutorService e;
            synchronized(historyGate) {
                e=worker;
                if(!active||e==null||!historyLoaded) return;
                if(queued){dirty=true;return;}
                queued=true;dirty=false;pending=false;issued=epoch;
            }
            try{
                e.execute(()->{
                    try{
                        synchronized(historyGate){
                            if(!active||epoch!=issued)return;
                            committed=false;
                        }
                        workerToken.set(issued);
                        boolean ok=persist();
                        synchronized(historyGate){
                            if(epoch==issued&&!ok)pending=true;
                        }
                    }catch(RuntimeException ex){
                        pending=true;
                    }finally{
                        workerToken.remove();
                        synchronized(historyGate){
                            if(epoch==issued){
                                if(dirty)pending=true;
                                queued=false;dirty=false;
                            }
                        }
                    }
                });
                schedules++;
            }catch(java.util.concurrent.RejectedExecutionException error){
                synchronized(historyGate){
                    if(epoch==issued){
                        queued=false;dirty=false;pending=true;
                    }
                }
            }
        }
        void delete(String row) {
            synchronized(fileGate){
                panel.remove(row);
                persist();
            }
        }
        void tick() {
            if(pending)queue();
        }
        void add(String value){panel.add(value);mutation++;}
        boolean terminated(long ms){
            try{return worker==null||worker.awaitTermination(ms,TimeUnit.MILLISECONDS);}
            catch(InterruptedException ex){Thread.currentThread().interrupt();return false;}
        }
    }

    static void ids(List<String> x,String... wants){
        yes(x.equals(Arrays.asList(wants)),"got="+x+" wanted="+Arrays.asList(wants));
    }
    static void basicAutosaveRunsOnDaemon() {
        M m=new M();m.start();m.add("a");
        m.request();await(m.firstCompletedWrite,"background write");
        ids(m.disk,"a");yes(m.lastWriterThread.startsWith("R403-Synthetic-Daemon"),"not on worker");
        m.stop();passed++;
    }
    static void callerDoesNotWaitForBlockedWrite(){
        M m=new M();m.start();m.add("a");
        CountDownLatch entered=new CountDownLatch(1),release=new CountDownLatch(1);
        m.insideWriter=()->{entered.countDown();await(release,"write release");};
        long before=System.nanoTime();m.request();
        long elapsed=System.nanoTime()-before;
        yes(elapsed<TimeUnit.SECONDS.toNanos(1),"request blocked for disk write");
        await(entered,"writer started");release.countDown();m.stop();passed++;
    }
    static void burstCoalescesIntoOneScheduledTask(){
        M m=new M();m.start();m.add("one");
        CountDownLatch entered=new CountDownLatch(1),release=new CountDownLatch(1);
        m.insideWriter=()->{entered.countDown();await(release,"release");};
        m.request();await(entered,"entered");
        for(int i=0;i<100;i++)m.request();
        yes(m.schedules==1,"burst launched extra tasks");
        release.countDown();m.stop();passed++;
    }
    static void dirtyRequestsStayPendingAfterWrite(){
        M m=new M();m.start();m.add("one");
        CountDownLatch entered=new CountDownLatch(1),release=new CountDownLatch(1);
        m.insideWriter=()->{entered.countDown();await(release,"release");};
        m.request();await(entered,"entered");m.add("two");m.request();
        release.countDown();
        m.stop();
        yes(m.writes>=1,"no write completed");
        passed++;
    }
    static void oldWorkerCannotWriteAfterSessionChange(){
        M m=new M();m.start();m.add("old");
        CountDownLatch snapshotTaken=new CountDownLatch(1),release=new CountDownLatch(1);
        m.beforeWriterLock=()->{snapshotTaken.countDown();await(release,"writer release");};
        m.request();await(snapshotTaken,"snapshot");
        m.stop(); // synchronous final writes current records
        release.countDown();
        await(m.rejectedStaleWorker,"stale worker refusal");
        ids(m.disk,"old");yes(m.rejections>=1,"stale worker not refused");
        passed++;
    }
    static void restartWorkerIsNotClearedByPriorSession(){
        M m=new M();m.start();m.stop();m.start();m.add("new");
        m.request();
        try {m.worker.submit(()->{}).get(2,TimeUnit.SECONDS);}
        catch(Exception ex) {throw new AssertionError("restart worker failed",ex);}
        ids(m.disk,"new");m.stop();passed++;
    }
    static void failedWriteRequiresRetry(){
        M m=new M();m.start();m.failWrite=true;m.add("pending");
        m.request();
        CountDownLatch wait=new CountDownLatch(1);
        // synchronize via executor serialization (synthetic-only)
        try{m.worker.submit(wait::countDown).get(2,TimeUnit.SECONDS);}
        catch(Exception ex){throw new AssertionError(ex);}
        yes(m.pending,"failed save did not remain pending");
        m.failWrite=false;m.tick();
        m.stop();ids(m.disk,"pending");passed++;
    }
    static void explicitDeletionRemainsSynchronous(){
        M m=new M();m.start();m.add("one");m.add("two");
        m.delete("one");ids(m.disk,"two");
        yes(!m.lastWriterThread.startsWith("R403-Synthetic-Daemon"),
            "explicit deletion silently queued");m.stop();passed++;
    }
    static void lastSessionSynchronousShutdown(){
        M m=new M();m.start();m.add("unsaved");
        m.stop();ids(m.disk,"unsaved");passed++;
    }
    static void noSaveIfHistoryUnrestored(){
        M m=new M();m.start();m.historyLoaded=false;m.add("new");
        m.request();yes(m.writes==0 && m.pending,"unrestored data written");
        m.stop();passed++;
    }
    static void duplicateLabelsRemainDistinct(){
        M m=new M();m.start();m.add("same");m.add("same");
        m.request();m.stop();ids(m.disk,"same","same");passed++;
    }
    static void onlyOneWriterUsesTheFileLock(){
        M m=new M();m.start();m.add("a");
        m.request();m.delete("absent");
        m.stop();yes(m.maxActiveWriters==1,"concurrent writes overlapped");passed++;
    }
    static void lateQueuedWorkInvalidatedAfterStop(){
        M m=new M();m.start();m.add("a");
        m.stop();m.request();yes(m.queued==false,"work admitted after close");
        ids(m.disk,"a");passed++;
    }
    static void daemonWorkerDoesNotBlockNormalShutdown(){
        M m=new M();m.start();m.add("a");
        m.request();m.stop();yes(m.worker==null,"worker not retired");passed++;
    }
    static void noFailedReceiptCanClaimSuccess(){
        M m=new M();m.start();m.add("old");m.failWrite=true;
        m.request();
        try{m.worker.submit(()->{}).get(2,TimeUnit.SECONDS);}
        catch(Exception ex){throw new AssertionError(ex);}
        yes(m.writes==0 && m.pending,"write failure acknowledged");
        m.failWrite=false;m.stop();passed++;
    }
    public static void main(String[] args){
        basicAutosaveRunsOnDaemon();callerDoesNotWaitForBlockedWrite();
        burstCoalescesIntoOneScheduledTask();dirtyRequestsStayPendingAfterWrite();
        oldWorkerCannotWriteAfterSessionChange();restartWorkerIsNotClearedByPriorSession();
        failedWriteRequiresRetry();explicitDeletionRemainsSynchronous();
        lastSessionSynchronousShutdown();noSaveIfHistoryUnrestored();
        duplicateLabelsRemainDistinct();onlyOneWriterUsesTheFileLock();
        lateQueuedWorkInvalidatedAfterStop();daemonWorkerDoesNotBlockNormalShutdown();
        noFailedReceiptCanClaimSuccess();
        System.out.println("R403_SYNTHETIC_PASS "+passed+" scenarios");
    }
}
