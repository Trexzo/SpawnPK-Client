import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Independent invented R412 model. No game source or user history, all data
 * is fabricated. Models synchronous confirmed mutation with a preflight
 * stage check acquired under the same LOCAL file lock as save.
 *
 * The deliberately failing postmutation-commit scenario is a known blocker.
 * It is not proof of complete rollback or interprocess lock safety.
 */
public final class R412DeletePreflightSynthetic {
    static int count;
    static void ok(boolean b,String reason) {if(!b)throw new AssertionError(reason);}
    static void rows(List<Integer> got,Integer... expected) {
        ok(got.equals(Arrays.asList(expected)),
            "got="+got+" expected="+Arrays.asList(expected));
    }
    static void await(CountDownLatch latch,String label) {
        try {ok(latch.await(5,TimeUnit.SECONDS),"timed out "+label);}
        catch(InterruptedException e){Thread.currentThread().interrupt();throw new AssertionError(e);}
    }
    enum Stage {CLEAR,ORPHAN,UNSAFE}
    static final class M {
        final Object fileGate=new Object(),historyGate=new Object();
        final List<Integer> panel=new ArrayList<>(),disk=new ArrayList<>();
        boolean remember=true,edt=true,loaded=true,active=true,
            clear=false,unsafe=false,handoffUnsafe=false,retainedUnsafe=false,
            transaction=false,writeReceipt=false,saveFails=false;
        int probeCount,uiMutations,diskCommits,refusals;
        Stage stage=Stage.CLEAR;
        Runnable afterPreflight=()->{};
        M(Integer... data) {
            panel.addAll(Arrays.asList(data));
            disk.addAll(Arrays.asList(data));
        }
        Stage state() {probeCount++;return stage;}
        boolean confirmDelete(int target) {
            if(!edt||!active)return false;
            if(!remember) {panel.remove(Integer.valueOf(target));uiMutations++;return true;}
            synchronized(fileGate) {
                if(state()!=Stage.CLEAR) {
                    synchronized(historyGate) {
                        unsafe=true;
                        writeReceipt=false;
                    }
                    refusals++;
                    return false;
                }
                synchronized(historyGate) {
                    if(!loaded||clear||unsafe||handoffUnsafe||
                       retainedUnsafe||transaction) {
                        refusals++;
                        return false;
                    }
                    transaction=true;
                    writeReceipt=false;
                }
                boolean finished=false;
                try {
                    afterPreflight.run();
                    panel.remove(Integer.valueOf(target));
                    uiMutations++;
                    finished=true;
                }finally{
                    synchronized(historyGate) {
                        if(!finished)unsafe=true;
                    }
                }
                try {
                    if(stage==Stage.CLEAR&&!saveFails) {
                        disk.clear();disk.addAll(panel);
                        diskCommits++;
                        writeReceipt=true;
                    }
                }finally{
                    synchronized(historyGate) {
                        if(!writeReceipt)unsafe=true;
                        transaction=false;
                    }
                }
                return writeReceipt;
            }
        }
        List<Integer> panelSnapshot(){return new ArrayList<>(panel);}
        List<Integer> diskSnapshot(){return new ArrayList<>(disk);}
    }
    static void cleanDeleteAndAck() {
        M m=new M(1,2,3);
        ok(m.confirmDelete(2),"clean transaction refused");
        rows(m.panelSnapshot(),1,3);rows(m.diskSnapshot(),1,3);
        ok(!m.unsafe&&m.writeReceipt&&m.uiMutations==1&&m.diskCommits==1,"clean receipt");
        count++;
    }
    static void orphanRefusesBeforeMutation() {
        M m=new M(1,2);m.stage=Stage.ORPHAN;
        ok(!m.confirmDelete(1),"orphan accepted");
        rows(m.panelSnapshot(),1,2);rows(m.diskSnapshot(),1,2);
        ok(m.unsafe&&!m.writeReceipt&&m.uiMutations==0&&m.diskCommits==0,"no preflight block");
        count++;
    }
    static void unsafeTypeRefusesBeforeMutation() {
        M m=new M(1);m.stage=Stage.UNSAFE;
        ok(!m.confirmDelete(1),"unsafe stage accepted");
        rows(m.panelSnapshot(),1);rows(m.diskSnapshot(),1);
        ok(m.unsafe&&m.uiMutations==0,"unsafe stage mutated panel");
        count++;
    }
    static void emptyPanelStillRefusesOrphan() {
        M m=new M();m.stage=Stage.ORPHAN;
        ok(!m.confirmDelete(88),"orphan with no match accepted");
        ok(m.uiMutations==0&&m.diskCommits==0,"false empty edit");
        count++;
    }
    static void nonPersistentUiOnlyModeUnchanged() {
        M m=new M(1,2);m.remember=false;m.stage=Stage.ORPHAN;
        ok(m.confirmDelete(1),"UI-only edit incorrectly refused");
        rows(m.panelSnapshot(),2);rows(m.diskSnapshot(),1,2);
        ok(m.probeCount==0&&m.diskCommits==0&&!m.writeReceipt,"UI-only wrote history");
        count++;
    }
    static void notEdtDoesNotMutate() {
        M m=new M(1);m.edt=false;
        ok(!m.confirmDelete(1),"non EDT accepted");
        rows(m.panelSnapshot(),1);rows(m.diskSnapshot(),1);
        ok(m.probeCount==0,"non-EDT inspected private stage");
        count++;
    }
    static void pluginInactiveRefused() {
        M m=new M(1);m.active=false;
        ok(!m.confirmDelete(1),"inactive session accepted");
        rows(m.panelSnapshot(),1);count++;
    }
    static void incompleteLoadRefused() {
        M m=new M(1);m.loaded=false;
        ok(!m.confirmDelete(1),"unloaded panel accepted edit");
        rows(m.panelSnapshot(),1);rows(m.diskSnapshot(),1);count++;
    }
    static void clearInProgressRefused() {
        M m=new M(1);m.clear=true;
        ok(!m.confirmDelete(1),"edit while clear accepted");
        rows(m.panelSnapshot(),1);count++;
    }
    static void unsafeHistoryRefused() {
        M m=new M(1);m.unsafe=true;
        ok(!m.confirmDelete(1),"unsafe accepted");
        rows(m.panelSnapshot(),1);count++;
    }
    static void pendingHandoffRefused() {
        M m=new M(1);m.handoffUnsafe=true;
        ok(!m.confirmDelete(1),"panel handoff accepted");
        rows(m.panelSnapshot(),1);count++;
    }
    static void retainedPanelRefused() {
        M m=new M(1);m.retainedUnsafe=true;
        ok(!m.confirmDelete(1),"retained panel accepted");
        rows(m.panelSnapshot(),1);count++;
    }
    static void existingTransactionRefused() {
        M m=new M(1);m.transaction=true;
        ok(!m.confirmDelete(1),"nested edit accepted");
        rows(m.panelSnapshot(),1);count++;
    }
    static void stageRefusalPersistsUnsafeQuarantine() {
        M m=new M(1);m.stage=Stage.ORPHAN;
        m.confirmDelete(1);
        m.stage=Stage.CLEAR;
        ok(!m.confirmDelete(1),"unsafe state silently reset after stage disappearance");
        rows(m.panelSnapshot(),1);rows(m.diskSnapshot(),1);
        count++;
    }
    static void failedWriteAfterMutationStillUnsafeNotRolledBack() {
        M m=new M(1,2);m.saveFails=true;
        ok(!m.confirmDelete(1),"failed write called success");
        rows(m.panelSnapshot(),2);rows(m.diskSnapshot(),1,2);
        ok(m.unsafe&&!m.writeReceipt,"known unacknowledged UI mutation not quarantined");
        count++;
    }
    static void stageAppearsAfterPreflightStillUnresolved() {
        M m=new M(1,2);
        m.afterPreflight=()->m.stage=Stage.ORPHAN; // foreign writer, not local FileGate
        ok(!m.confirmDelete(1),"foreign after-guard stage reported success");
        rows(m.panelSnapshot(),2);rows(m.diskSnapshot(),1,2);
        ok(m.unsafe,"post-precheck race not quarantined");
        count++;
    }
    static void activeSameGateWorkerFinishesBeforeDeletePreflight() {
        M m=new M(1,2);
        CountDownLatch entered=new CountDownLatch(1),release=new CountDownLatch(1);
        Thread worker=new Thread(()->{
            synchronized(m.fileGate) {
                m.stage=Stage.ORPHAN;
                entered.countDown();
                await(release,"release worker");
                m.stage=Stage.CLEAR;
            }
        });
        worker.setDaemon(true);worker.start();
        await(entered,"local save entered gate");
        AtomicBoolean success=new AtomicBoolean(false);
        Thread deleter=new Thread(()->success.set(m.confirmDelete(1)));
        deleter.setDaemon(true);deleter.start();
        release.countDown();
        try{worker.join(5000);deleter.join(5000);}
        catch(InterruptedException e){throw new AssertionError(e);}
        ok(!worker.isAlive()&&!deleter.isAlive(),"local gate test hung");
        ok(success.get(),"local worker completed but delete not admitted");
        rows(m.panelSnapshot(),2);rows(m.diskSnapshot(),2);
        count++;
    }
    static void workerLeavingOrphanRefusesOnceLockReleased() {
        M m=new M(1,2);
        CountDownLatch entered=new CountDownLatch(1),release=new CountDownLatch(1);
        Thread worker=new Thread(()->{
            synchronized(m.fileGate) {
                m.stage=Stage.ORPHAN;
                entered.countDown();
                await(release,"release failed writer");
            }
        });
        worker.setDaemon(true);worker.start();await(entered,"failed writer entered");
        AtomicBoolean result=new AtomicBoolean(true);
        Thread deleter=new Thread(()->result.set(m.confirmDelete(1)));
        deleter.setDaemon(true);deleter.start();
        release.countDown();
        try{worker.join(5000);deleter.join(5000);}
        catch(InterruptedException e){throw new AssertionError(e);}
        ok(!result.get(),"leftover stage did not block edit");
        rows(m.panelSnapshot(),1,2);rows(m.diskSnapshot(),1,2);
        ok(m.unsafe,"failed writer did not quarantine");
        count++;
    }
    static void orphanRefusalNoFileOrUiWrite() {
        M m=new M(1,2,3);m.stage=Stage.ORPHAN;
        m.confirmDelete(2);
        ok(m.probeCount==1&&m.uiMutations==0&&m.diskCommits==0,"preflight not first");
        count++;
    }
    static void twoSequentialEditsAllowedAfterCleanReceipt() {
        M m=new M(1,2,3);
        ok(m.confirmDelete(1),"first");
        ok(m.confirmDelete(2),"second");
        rows(m.panelSnapshot(),3);rows(m.diskSnapshot(),3);
        ok(m.diskCommits==2&&!m.unsafe,"clean subsequent edits broken");
        count++;
    }
    public static void main(String[] args) {
        cleanDeleteAndAck();
        orphanRefusesBeforeMutation();
        unsafeTypeRefusesBeforeMutation();
        emptyPanelStillRefusesOrphan();
        nonPersistentUiOnlyModeUnchanged();
        notEdtDoesNotMutate();
        pluginInactiveRefused();
        incompleteLoadRefused();
        clearInProgressRefused();
        unsafeHistoryRefused();
        pendingHandoffRefused();
        retainedPanelRefused();
        existingTransactionRefused();
        stageRefusalPersistsUnsafeQuarantine();
        failedWriteAfterMutationStillUnsafeNotRolledBack();
        stageAppearsAfterPreflightStillUnresolved();
        activeSameGateWorkerFinishesBeforeDeletePreflight();
        workerLeavingOrphanRefusesOnceLockReleased();
        orphanRefusalNoFileOrUiWrite();
        twoSequentialEditsAllowedAfterCleanReceipt();
        System.out.println("R412_SYNTHETIC_DELETE_PREFLIGHT_PASS "+count+" cases");
        System.out.println("R412_FOREIGN_PROCESS_RACE_AND_POSTEDIT_ROLLBACK_NOT_SOLVED");
    }
}
