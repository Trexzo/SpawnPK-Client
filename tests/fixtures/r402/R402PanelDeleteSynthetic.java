import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/** R402 standalone invented Java model: no game client, history files or networking. */
public final class R402PanelDeleteSynthetic {
    static int pass;
    static void yes(boolean condition,String why) {if(!condition)throw new AssertionError(why);}
    static final class Drop {
        final int id;final String group;final String type;
        Drop(int i,String g,String t){id=i;group=g;type=t;}
        @Override public boolean equals(Object x){
            return x instanceof Drop && group.equals(((Drop)x).group)
                && type.equals(((Drop)x).type);
        }
        @Override public int hashCode(){return group.hashCode()+type.hashCode();}
    }
    static final class FakeDisk {
        final List<Drop> records=new ArrayList<>();
        boolean writable=true;
        int commits;
        Runnable onWriteStarted;
        boolean write(List<Drop> data) {
            if(!writable)return false;
            if(onWriteStarted!=null){
                Runnable run=onWriteStarted;onWriteStarted=null;run.run();
            }
            records.clear();records.addAll(data);
            ++commits;return true;
        }
    }
    static final class M {
        final Object historyGate=new Object(),fileGate=new Object();
        final List<Drop> panel=new ArrayList<>(),pending=new ArrayList<>();
        final FakeDisk disk=new FakeDisk();
        long editGeneration,dropMutation;
        boolean editedInProgress,transactionOpen,writeReceipt,unsafe,
            loaded=true,saveDeferred,remember=true,onEdt=true,active=true;
        int refused,edits,saveAttempts;
        Runnable beforeWriterLock;
        void add(Drop x){
            synchronized(historyGate){pending.add(x);dropMutation++;}
        }
        boolean persist(){
            final long epoch;
            final List<Drop> copy;
            synchronized(historyGate){
                if(!loaded||unsafe||editedInProgress){++refused;saveDeferred=true;return false;}
                epoch=editGeneration;
            }
            copy=new ArrayList<>(panel);
            synchronized(historyGate){copy.addAll(pending);}
            if(beforeWriterLock!=null) {
                Runnable run=beforeWriterLock;beforeWriterLock=null;run.run();
            }
            boolean committed;
            synchronized(fileGate){
                synchronized(historyGate) {
                    if(unsafe||editedInProgress||epoch!=editGeneration){
                        ++refused;return false;
                    }
                }
                ++saveAttempts;
                committed=disk.write(copy);
            }
            if(committed) {
                synchronized(historyGate){
                    if(transactionOpen)writeReceipt=true;
                }
            }
            return committed;
        }
        boolean edit(Runnable mutation) {
            if(!onEdt||mutation==null||!active){++refused;return false;}
            if(!remember){mutation.run();return true;}
            synchronized(fileGate){
                synchronized(historyGate){
                    if(!loaded||unsafe||editedInProgress||transactionOpen){
                        ++refused;return false;
                    }
                    ++editGeneration;editedInProgress=true;transactionOpen=true;
                    writeReceipt=false;
                }
                boolean done=false;
                try {
                    mutation.run();
                    done=true;
                } finally {
                    synchronized(historyGate){
                        ++editGeneration;editedInProgress=false;
                        if(!done){unsafe=true;transactionOpen=false;}
                    }
                }
                try {
                    persist();
                } finally {
                    synchronized(historyGate){
                        if(!writeReceipt)unsafe=true;
                        transactionOpen=false;
                    }
                }
                ++edits;
                return writeReceipt;
            }
        }
        boolean deleteOne(Drop x){
            return edit(()->panel.removeIf(row->row==x));
        }
        boolean deleteGroup(String group){
            return edit(()->panel.removeIf(row->row.group.equals(group)));
        }
        boolean deleteType(String type){
            return edit(()->panel.removeIf(row->row.type.equals(type)));
        }
        void clearAll() {
            synchronized(fileGate){
                synchronized(historyGate){editGeneration++;unsafe=false;transactionOpen=false;}
                panel.clear();pending.clear();disk.records.clear();
            }
        }
    }
    static Drop d(int id,String group,String type){return new Drop(id,group,type);}
    static void ids(List<Drop> rows,int... expected){
        List<Integer> actual=new ArrayList<>();
        for(Drop x:rows)actual.add(x.id);
        List<Integer> want=new ArrayList<>();
        for(int x:expected)want.add(x);
        yes(actual.equals(want),"actual="+actual+" wanted="+want);
    }
    static void latch(CountDownLatch l,String name) {
        try{yes(l.await(3,TimeUnit.SECONDS),"timeout "+name);}
        catch(InterruptedException ex){Thread.currentThread().interrupt();throw new AssertionError(ex);}
    }
    static void deleteSinglePreservesDuplicateIdentity(){
        M m=new M();Drop a=d(1,"same","npc"),b=d(2,"same","npc");
        m.panel.add(a);m.panel.add(b);
        yes(a.equals(b)&&a!=b,"identity test setup");
        yes(m.deleteOne(b),"single delete failed");
        ids(m.panel,1);ids(m.disk.records,1);pass++;
    }
    static void groupDeletionSelective(){
        M m=new M();m.panel.add(d(1,"A","npc"));m.panel.add(d(2,"A","player"));
        m.panel.add(d(3,"B","npc"));
        yes(m.deleteGroup("A"),"group delete failed");
        ids(m.disk.records,3);pass++;
    }
    static void typeDeletionSelective(){
        M m=new M();m.panel.add(d(1,"A","npc"));m.panel.add(d(2,"B","npc"));
        m.panel.add(d(3,"B","player"));
        yes(m.deleteType("npc"),"type delete failed");
        ids(m.disk.records,3);pass++;
    }
    static void oldSnapshotInvalidatedByEdit(){
        M m=new M();Drop a=d(1,"A","npc"),b=d(2,"B","npc");
        m.panel.add(a);m.panel.add(b);
        m.beforeWriterLock=()->yes(m.deleteOne(a),"delete failed in save window");
        yes(!m.persist(),"predelete save resurrected removed record");
        ids(m.disk.records,2);pass++;
    }
    static void oldWriterFinishesBeforeDeletion() throws Exception {
        M m=new M();Drop a=d(1,"A","npc"),b=d(2,"B","npc");
        m.panel.add(a);m.panel.add(b);
        CountDownLatch writerEntered=new CountDownLatch(1),
                       writerRelease=new CountDownLatch(1),
                       deletionStarted=new CountDownLatch(1);
        m.disk.onWriteStarted=()->{writerEntered.countDown();latch(writerRelease,"writer release");};
        Thread save=new Thread(m::persist,"r402-synthetic-prior-save");save.setDaemon(true);save.start();
        latch(writerEntered,"prior save entry");
        AtomicBoolean success=new AtomicBoolean(false);
        Thread delete=new Thread(()->{deletionStarted.countDown();success.set(m.deleteOne(a));},
                                  "r402-synthetic-edt-delete");
        delete.setDaemon(true);delete.start();latch(deletionStarted,"delete entered");
        writerRelease.countDown();
        save.join(3000);delete.join(3000);
        yes(!save.isAlive()&&!delete.isAlive(),"deadlock");
        yes(success.get(),"delete failed");
        ids(m.disk.records,2);pass++;
    }
    static void saveDuringMutationIsRefused(){
        M m=new M();m.panel.add(d(1,"A","npc"));
        boolean edited=m.edit(()->{
            m.panel.clear();
            yes(!m.persist(),"save ran against mid-edit state");
        });
        yes(edited&&m.refused==1,"edit gate did not reject partial snapshot");
        ids(m.disk.records);pass++;
    }
    static void failedWriteQuarantines(){
        M m=new M();m.panel.add(d(1,"A","npc"));m.disk.records.addAll(m.panel);
        m.disk.writable=false;
        yes(!m.deleteGroup("A"),"failed disk write falsely succeeded");
        ids(m.disk.records,1);ids(m.panel);
        yes(m.unsafe&&!m.persist(),"automatic write not quarantined");pass++;
    }
    static void userClearRecoversAfterFailure(){
        M m=new M();m.panel.add(d(1,"A","npc"));m.disk.writable=false;
        m.deleteGroup("A");yes(m.unsafe,"missing unsafe flag");
        m.disk.writable=true;m.clearAll();m.panel.add(d(2,"B","npc"));
        yes(m.deleteGroup("A"),"clear did not reset unsafe gate");
        ids(m.disk.records,2);pass++;
    }
    static void disabledPersistenceKeepsUiOnly(){
        M m=new M();m.remember=false;m.panel.add(d(1,"A","npc"));
        yes(m.deleteGroup("A"),"UI-only delete refused");
        ids(m.panel);yes(m.disk.commits==0&&!m.unsafe,"UI-only mode wrote/quarantined");
        pass++;
    }
    static void noEdtMutationRefused(){
        M m=new M();m.onEdt=false;m.panel.add(d(1,"A","npc"));
        yes(!m.deleteType("npc"),"off-EDT deletion accepted");
        ids(m.panel,1);pass++;
    }
    static void notLoadedMutationRefused(){
        M m=new M();m.loaded=false;m.panel.add(d(1,"A","npc"));
        yes(!m.deleteGroup("A"),"unloaded mutation accepted");
        ids(m.panel,1);pass++;
    }
    static void nestedMutationRefused(){
        M m=new M();m.panel.add(d(1,"A","npc"));
        yes(m.edit(()->{
            yes(!m.edit(()->m.panel.clear()),"nested edit accepted");
            ids(m.panel,1);
        }),"outer edit failed");
        ids(m.disk.records,1);pass++;
    }
    static void mutationExceptionQuarantines(){
        M m=new M();m.panel.add(d(1,"A","npc"));
        try {
            m.edit(()->{m.panel.clear();throw new IllegalArgumentException("synthetic");});
            throw new AssertionError("expected exception");
        } catch(IllegalArgumentException expected){}
        yes(m.unsafe&&!m.transactionOpen,"exception did not quarantine and close");
        yes(m.disk.commits==0,"partial mutation written");pass++;
    }
    static void pendingDropSurvivesGroupDelete(){
        M m=new M();m.panel.add(d(1,"A","npc"));m.add(d(2,"new","npc"));
        yes(m.deleteGroup("A"),"delete failed");
        ids(m.disk.records,2);pass++;
    }
    static void sequentialDeletesDoNotResurrect(){
        M m=new M();m.panel.add(d(1,"A","npc"));m.panel.add(d(2,"B","npc"));
        m.panel.add(d(3,"C","player"));
        yes(m.deleteOne(m.panel.get(0)),"first delete failed");
        yes(m.deleteType("npc"),"second delete failed");
        ids(m.disk.records,3);pass++;
    }
    static void panelDeleteDoesNotBlockOnHistoryGateWhileMutating(){
        M m=new M();m.panel.add(d(1,"A","npc"));
        yes(m.edit(()->{
            yes(!Thread.holdsLock(m.historyGate),"EDT mutation under historyGate");
            m.panel.clear();
        }),"edit failed");
        ids(m.disk.records);pass++;
    }
    public static void main(String[] args)throws Exception{
        deleteSinglePreservesDuplicateIdentity();
        groupDeletionSelective();typeDeletionSelective();
        oldSnapshotInvalidatedByEdit();oldWriterFinishesBeforeDeletion();
        saveDuringMutationIsRefused();failedWriteQuarantines();
        userClearRecoversAfterFailure();disabledPersistenceKeepsUiOnly();
        noEdtMutationRefused();notLoadedMutationRefused();
        nestedMutationRefused();mutationExceptionQuarantines();
        pendingDropSurvivesGroupDelete();sequentialDeletesDoNotResurrect();
        panelDeleteDoesNotBlockOnHistoryGateWhileMutating();
        System.out.println("R402_SYNTHETIC_PASS "+pass+" cases");
    }
}
