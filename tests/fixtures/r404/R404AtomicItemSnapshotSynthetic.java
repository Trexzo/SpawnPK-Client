import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * R404 synthetic standalone item snapshot model. No original client source,
 * files, credentials, private data, networking or disk writes.
 */
public final class R404AtomicItemSnapshotSynthetic {
    static int passed;
    static void ok(boolean valid,String why) {
        if(!valid)throw new AssertionError(why);
    }
    static void await(CountDownLatch latch,String label) {
        try {ok(latch.await(4,TimeUnit.SECONDS),"timeout "+label);}
        catch(InterruptedException e) {Thread.currentThread().interrupt();throw new AssertionError(label,e);}
    }
    static final class Snapshot {
        final int id,quantity;
        final String name;
        final long price;
        final boolean ignored;
        Snapshot(int i,String n,int q,long p,boolean h) {
            id=i;name=n;quantity=q;price=p;ignored=h;
        }
    }
    static final class Item {
        final int id,quantity;
        private String name;
        private long price;
        private boolean ignored;
        Item(int i,String n,int q,long p,boolean h) {
            id=i;name=n;quantity=q;price=p;ignored=h;
        }
        synchronized void setName(String n){name=n;}
        synchronized void setPrice(long p){price=p;}
        synchronized void setIgnored(boolean h){ignored=h;}
        synchronized void definition(String newName,long candidatePrice) {
            if(newName!=null)name=newName;
            if(candidatePrice>0 || price<=0)price=candidatePrice;
        }
        synchronized Snapshot copy() {
            return new Snapshot(id,name,quantity,price,ignored);
        }
    }
    static final class Record {
        final String title;
        Item[] items;
        Record(String t,Item... rows) {title=t;items=rows;}
        Snapshot[] writeSnapshot() {
            Item[] references=items.clone();
            Snapshot[] result=new Snapshot[references.length];
            for(int i=0;i<references.length;i++) result[i]=references[i].copy();
            return result;
        }
    }
    static void stableSnapshot() {
        Snapshot d=new Item(1,"old",2,100,false).copy();
        ok(d.id==1&&d.quantity==2&&d.name.equals("old")&&d.price==100&&!d.ignored,"stable");
        passed++;
    }
    static void nameAndPriceUpdateTogether() {
        Item a=new Item(1,"old",1,1,false);
        a.definition("new",200);
        Snapshot s=a.copy();
        ok(s.name.equals("new")&&s.price==200,"atomic name and price");
        passed++;
    }
    static void positiveOriginalPriceSurvivesNominal() {
        Item a=new Item(1,"old",1,500,false);
        a.definition("new",0);
        Snapshot s=a.copy();
        ok(s.price==500&&s.name.equals("new"),"positive pricing fallback");
        passed++;
    }
    static void zeroCanRemainZero() {
        Item a=new Item(1,"old",1,0,false);
        a.definition("new",0);
        ok(a.copy().price==0,"zero fallback");
        passed++;
    }
    static void zeroCanBeUpgraded() {
        Item a=new Item(1,"old",1,0,false);
        a.definition("new",210);
        ok(a.copy().price==210,"zero price update");
        passed++;
    }
    static void missingNameKeepsOld() {
        Item a=new Item(1,"kept",1,500,false);
        a.definition(null,800);
        Snapshot s=a.copy();
        ok(s.name.equals("kept")&&s.price==800,"missing name policy");
        passed++;
    }
    static void hiddenSetterAppearsInSnapshot() {
        Item a=new Item(1,"a",2,90,false);
        a.setIgnored(true);
        ok(a.copy().ignored,"hidden state");
        passed++;
    }
    static void visibleTogglePreservesAmount() {
        Item a=new Item(1,"a",2,90,true);
        a.setIgnored(false);
        Snapshot s=a.copy();
        ok(!s.ignored&&s.quantity==2&&s.price==90,"unhide");
        passed++;
    }
    static void immutableSnapshotAfterMutation() {
        Item a=new Item(1,"a",1,10,false);
        Snapshot before=a.copy();
        a.definition("b",20);
        a.setIgnored(true);
        ok(before.name.equals("a")&&before.price==10&&!before.ignored,"snapshot aliased live object");
        Snapshot after=a.copy();
        ok(after.name.equals("b")&&after.price==20&&after.ignored,"later state");
        passed++;
    }
    static void twoEqualLookingItemsStillIndependent() {
        Item a=new Item(1,"same",1,10,false);
        Item b=new Item(2,"same",1,10,false);
        a.definition("updated",30);
        ok(b.copy().name.equals("same")&&b.copy().price==10,"identity collapsed");
        passed++;
    }
    static void shallowArrayCloneDoesNotChangeRecordOrder() {
        Item a=new Item(1,"A",1,10,false),b=new Item(2,"B",1,20,false);
        Record r=new Record("x",a,b);
        Snapshot[] snap=r.writeSnapshot();
        ok(snap.length==2&&snap[0].id==1&&snap[1].id==2,"order");
        passed++;
    }
    static void priorRecordArrayReassignmentCannotChangeCapturedValues() {
        Item a=new Item(1,"a",1,10,false),b=new Item(2,"b",1,20,false);
        Record r=new Record("x",a);
        Snapshot[] first=r.writeSnapshot();
        r.items=new Item[]{b};
        ok(first.length==1&&first[0].id==1,"array capture aliased future values");
        passed++;
    }
    static void deterministicNaiveReadWouldTear() {
        Item a=new Item(1,"v1",1,1,false);
        // Original independent getters could see these two values from
        // different mutation epochs if a UI callback ran between reads.
        String name=a.copy().name;
        a.definition("v2",2);
        long price=a.copy().price;
        ok(name.equals("v1")&&price==2,"torn-value fixture invalid");
        Snapshot stable=a.copy();
        ok(stable.name.equals("v2")&&stable.price==2,"single-lock DTO torn");
        passed++;
    }
    static void writerAndSerializerShareAnItemMonitor() throws Exception {
        Item item=new Item(1,"v0",1,1,false);
        final CountDownLatch blockedWriter=new CountDownLatch(1);
        final CountDownLatch writerDone=new CountDownLatch(1);
        Thread writer;
        synchronized(item) {
            writer=new Thread(()->{
                blockedWriter.countDown();
                item.definition("v1",2);
                writerDone.countDown();
            },"r404-synthetic-edt");
            writer.setDaemon(true);writer.start();
            await(blockedWriter,"synthetic writer thread entered");
            Snapshot during=item.copy();
            ok(during.name.equals("v0")&&during.price==1,"mutated during snapshot lock");
            ok(writerDone.getCount()==1,"writer crossed item monitor");
        }
        await(writerDone,"writer completion");
        writer.join(3000);
        Snapshot after=item.copy();
        ok(after.name.equals("v1")&&after.price==2,"writer visibility");
        passed++;
    }
    static void repeatedConcurrentDefinitionsNeverTear() throws Exception {
        final Item item=new Item(1,"n0",1,1,false);
        final AtomicBoolean broken=new AtomicBoolean(false);
        Thread writer=new Thread(()->{
            for(int i=1;i<=5000;i++) item.definition("n"+i,i);
        },"r404-synthetic-mutator");
        writer.setDaemon(true);writer.start();
        for(int i=0;i<5000;i++) {
            Snapshot s=item.copy();
            long generation=Long.parseLong(s.name.substring(1));
            if(s.price!=Math.max(1,generation)) {
                broken.set(true);
                break;
            }
        }
        writer.join(3000);
        ok(!writer.isAlive()&&!broken.get(),"torn concurrent name/price pair");
        passed++;
    }
    static void hiddenFlagConcurrentMutationsAreVisible() throws Exception {
        final Item item=new Item(1,"n",1,100,false);
        CountDownLatch done=new CountDownLatch(1);
        Thread writer=new Thread(()->{
            for(int i=0;i<1000;i++)item.setIgnored((i&1)==0);
            done.countDown();
        });
        writer.setDaemon(true);writer.start();
        for(int i=0;i<1000;i++)item.copy();
        await(done,"ignored updates");
        ok(item.copy().ignored==false,"final hidden value");
        passed++;
    }
    static void originalRecordArrayCanStillMixIndependentItems() {
        // Explicit limitation: no single global transaction across items.
        Item a=new Item(1,"v1",1,1,false);
        Item b=new Item(2,"v1",1,1,false);
        Snapshot first=a.copy();
        a.definition("v2",2);
        b.definition("v2",2);
        Snapshot second=b.copy();
        ok(first.price==1&&second.price==2,"cross-item limitation not modeled");
        passed++;
    }
    static void unchangedQuantityAndIdSurviveDefinitionUpdate() {
        Item a=new Item(42,"old",Integer.MAX_VALUE,10,false);
        a.definition("new",20);
        Snapshot snap=a.copy();
        ok(snap.id==42&&snap.quantity==Integer.MAX_VALUE,"identity/quantity drift");
        passed++;
    }
    public static void main(String[] args)throws Exception {
        stableSnapshot();nameAndPriceUpdateTogether();
        positiveOriginalPriceSurvivesNominal();zeroCanRemainZero();
        zeroCanBeUpgraded();missingNameKeepsOld();
        hiddenSetterAppearsInSnapshot();visibleTogglePreservesAmount();
        immutableSnapshotAfterMutation();twoEqualLookingItemsStillIndependent();
        shallowArrayCloneDoesNotChangeRecordOrder();
        priorRecordArrayReassignmentCannotChangeCapturedValues();
        deterministicNaiveReadWouldTear();
        writerAndSerializerShareAnItemMonitor();
        repeatedConcurrentDefinitionsNeverTear();
        hiddenFlagConcurrentMutationsAreVisible();
        originalRecordArrayCanStillMixIndependentItems();
        unchangedQuantityAndIdSurviveDefinitionUpdate();
        System.out.println("R404_SYNTHETIC_PASS "+passed+" scenarios");
    }
}
