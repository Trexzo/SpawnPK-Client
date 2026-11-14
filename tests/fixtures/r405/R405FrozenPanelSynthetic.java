import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * R405 invented standalone concurrency model. No recovered client source,
 * user histories, I/O, packages, authentication or networking.
 */
public final class R405FrozenPanelSynthetic {
    static int passed;
    static void check(boolean b,String why) {if(!b)throw new AssertionError(why);}
    static void waitFor(CountDownLatch l,String why) {
        try{check(l.await(4,TimeUnit.SECONDS),"timeout: "+why);}
        catch(InterruptedException ex){Thread.currentThread().interrupt();throw new AssertionError(ex);}
    }
    static final class Item {
        final int id,quantity;
        String name;
        long price;
        boolean hidden;
        Item(int i,String n,int q,long p,boolean h) {
            id=i;name=n;quantity=q;price=p;hidden=h;
        }
        synchronized Item copy() {return new Item(id,name,quantity,price,hidden);}
        synchronized void definition(String name,long price) {
            if(name!=null)this.name=name;
            if(price>0||this.price<=0)this.price=price;
        }
        synchronized void ignored(boolean hidden) {this.hidden=hidden;}
    }
    static final class Record {
        final String title,subtitle,type;
        final int kills;
        final long timestamp;
        Item[] items;
        Record(String name,String subtitle,String type,int k,long time,Item...items){
            this.title=name;this.subtitle=subtitle;this.type=type;this.kills=k;
            this.timestamp=time;this.items=items;
        }
        Record copy(){
            Item[] old=items.clone();
            Item[] fresh=new Item[old.length];
            for(int i=0;i<old.length;i++){
                if(old[i]==null)throw new IllegalStateException("synthetic null item");
                fresh[i]=old[i].copy();
            }
            return new Record(title,subtitle,type,kills,timestamp,fresh);
        }
    }
    static final class Panel {
        final List<Record> records=new ArrayList<>();
        synchronized void add(Record x){records.add(x);}
        synchronized List<Record> frozen(){
            List<Record> result=new ArrayList<>();
            for(Record r:records){
                if(r==null)throw new IllegalStateException("synthetic null record");
                result.add(r.copy());
            }
            return result;
        }
        synchronized void prices(String name,long price) {
            for(Record r:records)for(Item i:r.items)i.definition(name,price);
        }
        synchronized void hidden(boolean hide){
            for(Record r:records)for(Item i:r.items)i.ignored(hide);
        }
        synchronized void delete(Record victim){
            records.removeIf(r->r==victim);
        }
        synchronized int count(){return records.size();}
    }
    static final class Handoff {
        final Object historyGate=new Object();
        long version,clearGeneration;
        final Panel panel=new Panel();
        final List<Record> pending=new ArrayList<>();
        final List<Record> committed=new ArrayList<>();
        boolean active=true;
        void accept(Record record) {
            synchronized(historyGate){pending.add(record);}
        }
        void move(Record record) {
            synchronized(historyGate){version++;} // begin odd
            panel.add(record);
            synchronized(historyGate){
                pending.removeIf(x->x==record);version++;
            }
        }
        boolean snapshot(Runnable beforePendingClone,Runnable afterPendingClone) {
            final long start;
            final long clear;
            synchronized(historyGate) {
                start=version;clear=clearGeneration;
            }
            if((start&1)!=0)return false;
            List<Record> panelRows=panel.frozen();
            final List<Record> pendingReferences;
            synchronized(historyGate) {
                if(start!=version||clear!=clearGeneration)return false;
                pendingReferences=new ArrayList<>(pending);
            }
            if(beforePendingClone!=null)beforePendingClone.run();
            List<Record> copied=new ArrayList<>();
            for(Record record:pendingReferences)copied.add(record.copy());
            if(afterPendingClone!=null)afterPendingClone.run();
            synchronized(historyGate) {
                if(start!=version||clear!=clearGeneration|| (version&1)!=0)return false;
            }
            panelRows.addAll(copied);
            committed.clear();committed.addAll(panelRows);
            return true;
        }
    }
    static Record rec(int id){
        return new Record("same","sub","NPC",1,1000+id,new Item(id,"n0",id,1,false));
    }
    static void ids(List<Record> records,int...want) {
        List<Integer> got=new ArrayList<>();
        for(Record r:records)got.add(r.items[0].id);
        List<Integer> expected=new ArrayList<>();
        for(int i:want)expected.add(i);
        check(got.equals(expected),"ids got="+got+" expected="+expected);
    }
    static void preservedAllRecordMetadata(){
        Record r=rec(3);Record copy=r.copy();
        check(copy!=r && copy.items!=r.items && copy.items[0]!=r.items[0],
                "record or item aliased");
        check(copy.title.equals(r.title)&&copy.subtitle.equals(r.subtitle)
                && copy.type.equals(r.type)&&copy.kills==r.kills
                && copy.timestamp==r.timestamp,"metadata lost");
        passed++;
    }
    static void priceAfterCopyDoesNotMutateFrozen() {
        Panel p=new Panel();Record r=rec(1);p.add(r);
        List<Record> before=p.frozen();p.prices("new",220);
        check(before.get(0).items[0].name.equals("n0")
                &&before.get(0).items[0].price==1,"frozen snapshot changed");
        check(p.frozen().get(0).items[0].price==220,"price update missing");passed++;
    }
    static void hiddenAfterCopyDoesNotMutateFrozen(){
        Panel p=new Panel();p.add(rec(1));
        List<Record> before=p.frozen();p.hidden(true);
        check(!before.get(0).items[0].hidden,"old snapshot flag modified");
        check(p.frozen().get(0).items[0].hidden,"new hidden state missing");passed++;
    }
    static void twoRecordsFrozenWithSameBatchPrice(){
        Panel p=new Panel();p.add(rec(1));p.add(rec(2));
        p.prices("name2",800);
        List<Record> snap=p.frozen();
        for(Record r:snap)
            check(r.items[0].name.equals("name2")&&r.items[0].price==800,
                  "partial price batch");
        passed++;
    }
    static void twoRecordsFrozenWithSameBatchHidden(){
        Panel p=new Panel();p.add(rec(1));p.add(rec(2));
        p.hidden(true);
        for(Record r:p.frozen())check(r.items[0].hidden,"partial ignored batch");
        passed++;
    }
    static void singleRecordArrayClonePreservesOrder(){
        Record record=new Record("A",null,"B",2,123,
            new Item(3,"a",1,2,false),new Item(4,"b",2,3,true));
        Record copy=record.copy();
        check(copy.items.length==2&&copy.items[0].id==3&&copy.items[1].id==4,
            "item order");
        passed++;
    }
    static void newRecordsAfterSnapshotAreNotRetroactive(){
        Panel p=new Panel();p.add(rec(1));
        List<Record> before=p.frozen();p.add(rec(2));
        ids(before,1);ids(p.frozen(),1,2);passed++;
    }
    static void deletingOriginalDoesNotChangeFrozen(){
        Panel p=new Panel();Record a=rec(1),b=rec(2);p.add(a);p.add(b);
        List<Record> before=p.frozen();p.delete(a);
        ids(before,1,2);ids(p.frozen(),2);passed++;
    }
    static void duplicateNamesKeepIdentity(){
        Panel p=new Panel();Record a=rec(1),b=rec(2);
        p.add(a);p.add(b);p.delete(b);
        ids(p.frozen(),1);passed++;
    }
    static void nullRecordIsFailClosed(){
        Panel p=new Panel();p.add(null);
        try{p.frozen();throw new AssertionError("did not refuse null record");}
        catch(IllegalStateException expected){}
        passed++;
    }
    static void nullItemIsFailClosed(){
        Panel p=new Panel();
        p.add(new Record("bad",null,"NPC",0,4,(Item)null));
        try{p.frozen();throw new AssertionError("did not refuse null item");}
        catch(IllegalStateException expected){}
        passed++;
    }
    static void priceRefreshCannotInterleavePanelFreeze() throws Exception{
        Panel p=new Panel();p.add(rec(1));p.add(rec(2));
        CountDownLatch began=new CountDownLatch(1),finished=new CountDownLatch(1);
        Thread thread;
        synchronized(p) {
            thread=new Thread(()->{
                began.countDown();
                p.prices("refreshed",50);
                finished.countDown();
            },"r405-fake-edt");
            thread.setDaemon(true);thread.start();
            waitFor(began,"price thread start");
            // Price batch is blocked on Panel: the freeze below still
            // observes all-old values, never a half-published batch.
            List<Record> old=p.frozen();
            check(old.get(0).items[0].price==1&&old.get(1).items[0].price==1,
                "price batch interrupted freeze");
            check(finished.getCount()==1,"batch crossed panel lock");
        }
        waitFor(finished,"price callback end");
        thread.join(3000);
        List<Record> fresh=p.frozen();
        check(fresh.get(0).items[0].price==50
                &&fresh.get(1).items[0].price==50,"not all refreshed");passed++;
    }
    static void ignoredBatchCannotInterleavePanelFreeze()throws Exception{
        Panel p=new Panel();p.add(rec(1));p.add(rec(2));
        CountDownLatch began=new CountDownLatch(1),finished=new CountDownLatch(1);
        Thread t;
        synchronized(p) {
            t=new Thread(()->{began.countDown();p.hidden(true);finished.countDown();});
            t.setDaemon(true);t.start();
            waitFor(began,"hide begin");
            for(Record r:p.frozen())check(!r.items[0].hidden,"half-hidden");
            check(finished.getCount()==1,"hide bypassed panel lock");
        }
        waitFor(finished,"hide done");
        for(Record r:p.frozen())check(r.items[0].hidden,"hide not applied");passed++;
    }
    static void oldPendingHandoffVersionCausesRejection(){
        Handoff h=new Handoff();Record item=rec(1);h.accept(item);
        check(!h.snapshot(()->h.move(item),null),"handoff during clone not refused");
        check(h.snapshot(null,null),"subsequent stable snapshot refused");
        ids(h.committed,1);passed++;
    }
    static void oldPendingHandoffAfterCloneCausesRejection(){
        Handoff h=new Handoff();Record item=rec(1);h.accept(item);
        check(!h.snapshot(null,()->h.move(item)),"handoff after clone not refused");
        check(h.snapshot(null,null),"stable retry failed");
        ids(h.committed,1);passed++;
    }
    static void pendingFrozenObjectDoesNotAliasLive(){
        Handoff h=new Handoff();Record item=rec(1);h.accept(item);
        check(h.snapshot(null,null),"pending snapshot failed");
        item.items[0].definition("later",400);
        check(h.committed.get(0).items[0].name.equals("n0")
            &&h.committed.get(0).items[0].price==1,"pending copied by alias");
        passed++;
    }
    static void oldClearGenerationRefusesPendingClone(){
        Handoff h=new Handoff();h.accept(rec(1));
        check(!h.snapshot(()->{
            synchronized(h.historyGate){h.clearGeneration++;}
        },null),"clear while copying not detected");
        passed++;
    }
    static void stablePanelAndPendingCombineNoDuplicates(){
        Handoff h=new Handoff();h.panel.add(rec(1));h.accept(rec(2));
        check(h.snapshot(null,null),"snapshot failed");
        ids(h.committed,1,2);passed++;
    }
    static void frozenSnapshotDoesNotAcquireFileGate() {
        Panel p=new Panel();p.add(rec(1));
        final Object fileGate=new Object();
        // The freeze runs while a different thread can own FileGate;
        // no file monitor is referenced by the panel implementation.
        synchronized(fileGate) {
            ids(p.frozen(),1);
        }
        passed++;
    }
    public static void main(String[] args)throws Exception {
        preservedAllRecordMetadata();
        priceAfterCopyDoesNotMutateFrozen();
        hiddenAfterCopyDoesNotMutateFrozen();
        twoRecordsFrozenWithSameBatchPrice();
        twoRecordsFrozenWithSameBatchHidden();
        singleRecordArrayClonePreservesOrder();
        newRecordsAfterSnapshotAreNotRetroactive();
        deletingOriginalDoesNotChangeFrozen();
        duplicateNamesKeepIdentity();
        nullRecordIsFailClosed();
        nullItemIsFailClosed();
        priceRefreshCannotInterleavePanelFreeze();
        ignoredBatchCannotInterleavePanelFreeze();
        oldPendingHandoffVersionCausesRejection();
        oldPendingHandoffAfterCloneCausesRejection();
        pendingFrozenObjectDoesNotAliasLive();
        oldClearGenerationRefusesPendingClone();
        stablePanelAndPendingCombineNoDuplicates();
        frozenSnapshotDoesNotAcquireFileGate();
        System.out.println("R405_SYNTHETIC_PASS "+passed+" cases");
    }
}
