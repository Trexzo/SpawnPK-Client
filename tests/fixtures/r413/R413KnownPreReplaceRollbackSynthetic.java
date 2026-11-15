import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.stream.Stream;

/**
 * R413: invented independent actual TEMP filesystem + UI-record identity
 * rollback model. Never loads real game source, history, configuration or JAR.
 * No power loss, cross-process lock, actual Swing runtime or recovery claim.
 */
public final class R413KnownPreReplaceRollbackSynthetic {
    static int passed;
    static void yes(boolean condition,String reason){
        if(!condition)throw new AssertionError(reason);
    }
    static void eq(Object actual,Object expected,String reason){
        if(!java.util.Objects.equals(actual,expected))
            throw new AssertionError(reason+": "+actual+" != "+expected);
    }
    static void await(CountDownLatch latch,String reason) {
        try{yes(latch.await(5,TimeUnit.SECONDS),"timeout "+reason);}
        catch(InterruptedException e){Thread.currentThread().interrupt();throw new AssertionError(reason,e);}
    }
    enum WriteState {NOT_ATTEMPTED,FAILED_BEFORE_REPLACE,REPLACE_ATTEMPTED,COMMITTED}
    enum Failure {NONE,ORPHAN_AFTER_PREFLIGHT,STAGE_WRITE_IO,UNSUPPORTED_ATOMIC,
                  MOVE_THEN_THROW,NO_WRITE_ATTEMPT,REFUSED_STAGING_BEFORE_EDIT}
    static final class Row {
        final int id;
        final String name,category;
        Row(int id,String name,String category) {
            this.id=id;this.name=name;this.category=category;
        }
    }
    static final class Snapshot {
        final List<Row> identities;
        final String filterName;
        final int page;
        final boolean grouped,overall;
        Snapshot(List<Row> identities,String filterName,int page,
                 boolean grouped,boolean overall){
            this.identities=identities;this.filterName=filterName;
            this.page=page;this.grouped=grouped;this.overall=overall;
        }
    }
    static final class Panel {
        final List<Row> records=new ArrayList<>();
        String filterName;
        int page=0;
        boolean grouped=true,overall=false;
        int rebuilds,rollbacks,aggregateRecounts;
        Panel(Row... rows){records.addAll(Arrays.asList(rows));}
        Snapshot capture(){
            return new Snapshot(new ArrayList<>(records),filterName,page,grouped,overall);
        }
        void removeOne(Row identity){records.removeIf(r->r==identity);rebuilds++;}
        void removeGroup(String group){
            records.removeIf(r->r.name.equals(group));
            if(group.equals(filterName)){
                filterName=null;page=0;grouped=true;overall=false;
            }
            rebuilds++;
        }
        void removeType(String type){
            records.removeIf(r->r.category.equals(type));rebuilds++;
        }
        void restore(Snapshot snapshot){
            records.clear();
            records.addAll(snapshot.identities);
            filterName=snapshot.filterName;
            page=snapshot.page;
            grouped=snapshot.grouped;
            overall=snapshot.overall;
            aggregateRecounts++;
            rebuilds++;
            rollbacks++;
        }
        List<Integer> ids(){
            List<Integer> result=new ArrayList<>();
            for(Row r:records)result.add(r.id);
            return result;
        }
    }
    static final class Model {
        final Object fileGate=new Object();
        final Path history,stage;
        final Panel panel;
        boolean unsafe,editOpen,writeReceipt;
        boolean rememberHistory=true,loaded=true,isEdt=true;
        int preflightCount,writeAttempts,stageForces,moveAttempts;
        WriteState state=WriteState.NOT_ATTEMPTED;
        Failure failure=Failure.NONE;
        Runnable afterPreflight=()->{};
        Model(Path dir,Row... rows)throws IOException{
            history=dir.resolve("invented-history.txt");
            stage=dir.resolve("invented-history.txt.tmp");
            panel=new Panel(rows);
            Files.write(history,encode(panel.ids()),StandardOpenOption.CREATE_NEW);
        }
        static byte[] encode(List<Integer> values) {
            StringBuilder s=new StringBuilder("synthetic-history-v1\n");
            for(int id:values)s.append(id).append('\n');
            return s.toString().getBytes(StandardCharsets.US_ASCII);
        }
        List<Integer> diskIds()throws IOException {
            String doc=new String(Files.readAllBytes(history),StandardCharsets.US_ASCII);
            yes(doc.startsWith("synthetic-history-v1\n"),"invalid invented history");
            List<Integer> ids=new ArrayList<>();
            for(String line:doc.substring("synthetic-history-v1\n".length()).split("\n"))
                if(!line.isEmpty())ids.add(Integer.parseInt(line));
            return ids;
        }
        void seedOrphan()throws IOException{
            Files.write(stage,new byte[]{1,2,3},StandardOpenOption.CREATE_NEW);
        }
        boolean save()throws IOException {
            writeAttempts++;
            state=WriteState.FAILED_BEFORE_REPLACE;
            if(Files.exists(stage))return false;
            byte[] body=encode(panel.ids());
            if(failure==Failure.STAGE_WRITE_IO)return false;
            try(FileChannel channel=FileChannel.open(stage,
                    StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE)){
                ByteBuffer b=ByteBuffer.wrap(body);
                while(b.hasRemaining())channel.write(b);
                channel.force(true);
                stageForces++;
            }catch(IOException e){return false;}
            state=WriteState.REPLACE_ATTEMPTED;
            moveAttempts++;
            if(failure==Failure.UNSUPPORTED_ATOMIC)return false;
            Files.move(stage,history,
                StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);
            if(failure==Failure.MOVE_THEN_THROW)return false;
            state=WriteState.COMMITTED;
            return true;
        }
        boolean deleteOne(Row r)throws IOException{
            return edit(()->panel.removeOne(r));
        }
        boolean deleteGroup(String name)throws IOException {
            return edit(()->panel.removeGroup(name));
        }
        boolean deleteType(String type)throws IOException {
            return edit(()->panel.removeType(type));
        }
        boolean edit(Runnable edit)throws IOException {
            if(!isEdt||!loaded)return false;
            if(!rememberHistory) {edit.run();return true;}
            synchronized(fileGate) {
                preflightCount++;
                if(Files.exists(stage)) {
                    unsafe=true;
                    writeReceipt=false;
                    return false;
                }
                if(unsafe||editOpen)return false;
                final Snapshot original=panel.capture();
                editOpen=true;
                state=WriteState.NOT_ATTEMPTED;
                writeReceipt=false;
                try{
                    edit.run();
                    afterPreflight.run();
                    if(failure!=Failure.NO_WRITE_ATTEMPT)
                        writeReceipt=save();
                    return writeReceipt;
                } finally{
                    boolean shouldRestore=false;
                    try{
                        if(!writeReceipt){
                            unsafe=true;
                            shouldRestore=state==WriteState.FAILED_BEFORE_REPLACE;
                        }
                        if(shouldRestore)panel.restore(original);
                    } finally{
                        editOpen=false;
                    }
                }
            }
        }
    }
    interface Scenario {void run(Model m)throws Exception;}
    static Row r(int id){return new Row(id,"same","mobs");}
    static Row x(int id){return new Row(id,"other","raids");}
    static void test(String name,Scenario fn)throws Exception{
        Path temp=Files.createTempDirectory("r413-invented-");
        try {
            fn.run(new Model(temp,r(1),r(2),x(3)));
            passed++;
        }catch(Throwable e){throw new AssertionError(name,e);}
        finally {
            try(Stream<Path> entries=Files.walk(temp)){
                entries.sorted(Comparator.reverseOrder()).forEach(p->{
                    try{Files.deleteIfExists(p);}
                    catch(IOException e){throw new IllegalStateException(e);}
                });
            }
        }
    }
    static void ids(Panel p,Integer... id){eq(p.ids(),Arrays.asList(id),"panel order");}
    static void disk(Model m,Integer... id)throws IOException {
        eq(m.diskIds(),Arrays.asList(id),"disk order");
    }
    static void cleanConfirmedSingleRecord()throws Exception {
        test("single commit",m->{
            Row row=m.panel.records.get(0);
            yes(m.deleteOne(row),"clean single delete");
            ids(m.panel,2,3);disk(m,2,3);
            eq(m.state,WriteState.COMMITTED,"writer state");
            yes(m.writeReceipt&&!m.unsafe&&m.panel.rollbacks==0,"false failure");
        });
    }
    static void exactIdentityPreservedWithDuplicates()throws Exception {
        test("identities",m->{
            Row first=m.panel.records.get(0),second=m.panel.records.get(1);
            m.failure=Failure.STAGE_WRITE_IO;
            yes(!m.deleteOne(first),"failed write accepted");
            yes(m.panel.records.get(0)==first&&m.panel.records.get(1)==second,
                "original identity lost");
            ids(m.panel,1,2,3);disk(m,1,2,3);
        });
    }
    static void stageAppearsAfterPreflightRollsBack()throws Exception {
        test("raced stage",m->{
            Row old=m.panel.records.get(0);
            m.afterPreflight=()->{
                try{m.seedOrphan();}
                catch(IOException e){throw new RuntimeException(e);}
            };
            yes(!m.deleteOne(old),"stage race treated as commit");
            ids(m.panel,1,2,3);disk(m,1,2,3);
            yes(m.panel.records.get(0)==old&&m.panel.rollbacks==1,
                "raced-stage rollback missing");
            eq(m.state,WriteState.FAILED_BEFORE_REPLACE,"wrong failure phase");
            yes(m.unsafe&&Files.exists(m.stage),"orphan evidence lost");
        });
    }
    static void stageBeforePreflightRefusesNoMutation()throws Exception {
        test("stage preflight",m->{
            m.seedOrphan();
            yes(!m.deleteType("mobs"),"orphan precheck accepted");
            ids(m.panel,1,2,3);disk(m,1,2,3);
            yes(m.panel.rebuilds==0&&m.panel.rollbacks==0,
                "preflight performed UI work");
            eq(m.writeAttempts,0,"staging writer admitted");
        });
    }
    static void stagedWriteIoBeforeRenameRollsBack()throws Exception {
        test("pre-stage io",m->{
            m.failure=Failure.STAGE_WRITE_IO;
            yes(!m.deleteType("mobs"),"staging IO failure treated success");
            ids(m.panel,1,2,3);disk(m,1,2,3);
            eq(m.panel.rollbacks,1,"rollback");
            eq(m.moveAttempts,0,"move attempted");
            yes(m.unsafe,"failed history write unquarantined");
        });
    }
    static void unsupportedAtomicMoveIsConservativeAmbiguity()throws Exception {
        test("unsupported atomic",m->{
            m.failure=Failure.UNSUPPORTED_ATOMIC;
            yes(!m.deleteType("mobs"),"unsupported move treated success");
            ids(m.panel,3);disk(m,1,2,3);
            eq(m.state,WriteState.REPLACE_ATTEMPTED,"write phase");
            yes(m.unsafe&&m.panel.rollbacks==0&&Files.exists(m.stage),
                "unsafe ambiguous write was rolled back");
        });
    }
    static void actualMoveThenExceptionNoRollback()throws Exception {
        test("post-rename error",m->{
            m.failure=Failure.MOVE_THEN_THROW;
            yes(!m.deleteOne(m.panel.records.get(0)),"postmove exception claimed success");
            ids(m.panel,2,3);disk(m,2,3);
            yes(m.unsafe&&m.panel.rollbacks==0,"false precommit rollback");
            eq(m.state,WriteState.REPLACE_ATTEMPTED,"postrename state");
            yes(!Files.exists(m.stage),"renamed stage remained");
        });
    }
    static void noWriteAttemptIsNotProofOfUncommitted()throws Exception {
        test("early skip",m->{
            m.failure=Failure.NO_WRITE_ATTEMPT;
            yes(!m.deleteOne(m.panel.records.get(0)),"no-write claimed success");
            ids(m.panel,2,3);disk(m,1,2,3);
            eq(m.state,WriteState.NOT_ATTEMPTED,"unknown transaction state");
            yes(m.unsafe&&m.panel.rollbacks==0,"guessed rollback without receipt");
        });
    }
    static void rollbackPreservesFilterAndPaging()throws Exception {
        test("grouped navigation",m->{
            m.panel.filterName="same";m.panel.page=4;
            m.panel.grouped=false;m.panel.overall=true;
            m.failure=Failure.STAGE_WRITE_IO;
            yes(!m.deleteGroup("same"),"failed group mutation treated success");
            ids(m.panel,1,2,3);disk(m,1,2,3);
            eq(m.panel.filterName,"same","filter retained");
            eq(m.panel.page,4,"page retained");
            yes(!m.panel.grouped&&m.panel.overall,"view flags lost");
            eq(m.panel.aggregateRecounts,1,"aggregate repair");
            eq(m.panel.rollbacks,1,"navigation rollback");
        });
    }
    static void groupWriteSuccessCanChangeFilter()throws Exception {
        test("successful group edit",m->{
            m.panel.filterName="same";m.panel.page=2;
            yes(m.deleteGroup("same"),"valid group delete refused");
            ids(m.panel,3);disk(m,3);
            eq(m.panel.filterName,null,"filter not cleared");
            eq(m.panel.page,0,"page not reset");
        });
    }
    static void typeWriteSuccessRemovesOnlyMatching()throws Exception {
        test("successful type delete",m->{
            yes(m.deleteType("mobs"),"valid type delete refused");
            ids(m.panel,3);disk(m,3);
            yes(!m.unsafe,"clean result quarantined");
        });
    }
    static void stagePreflightPreservesNavigation()throws Exception {
        test("preflight navigation",m->{
            m.panel.filterName="same";m.panel.page=5;
            m.seedOrphan();
            yes(!m.deleteGroup("same"),"unsafe stage accepted");
            eq(m.panel.filterName,"same","preflight cleared filter");
            eq(m.panel.page,5,"preflight cleared page");
        });
    }
    static void rollbackDoesNotClearUnsafeFlag()throws Exception {
        test("unsafe remains",m->{
            m.failure=Failure.STAGE_WRITE_IO;
            m.deleteOne(m.panel.records.get(0));
            yes(m.unsafe&&!m.writeReceipt,"rolled-back failed write marked safe");
            eq(m.panel.rollbacks,1,"no rollback");
        });
    }
    static void laterEditRefusedWithoutExplicitRecovery()throws Exception {
        test("no automatic retry",m->{
            m.failure=Failure.STAGE_WRITE_IO;
            m.deleteOne(m.panel.records.get(0));
            m.failure=Failure.NONE;
            yes(!m.deleteOne(m.panel.records.get(1)),"unsafe edit accepted later");
            ids(m.panel,1,2,3);disk(m,1,2,3);
        });
    }
    static void exactSourceAndTypeSelection()throws Exception {
        test("name and group",m->{
            m.failure=Failure.STAGE_WRITE_IO;
            m.deleteGroup("same");
            ids(m.panel,1,2,3);
            yes(m.panel.records.get(0)!=m.panel.records.get(1),
                "duplicate names lost independent identity");
        });
    }
    static void noUnexpectedAutosaveDuringRollback()throws Exception {
        test("no extra write",m->{
            m.failure=Failure.STAGE_WRITE_IO;
            m.deleteOne(m.panel.records.get(0));
            eq(m.writeAttempts,1,"rollback queued a second write");
            eq(m.panel.rebuilds,2,"mutation+restore redraw count");
            eq(m.moveAttempts,0,"rollback performed file replacement");
        });
    }
    static void plainUiOnlyModeDoesNotTouchPersistence()throws Exception {
        test("ui-only",m->{
            m.rememberHistory=false;m.seedOrphan();
            yes(m.deleteOne(m.panel.records.get(0)),"ui-only deletion blocked");
            ids(m.panel,2,3);disk(m,1,2,3);
            eq(m.preflightCount,0,"ui-only checked persistent stage");
            eq(m.writeAttempts,0,"ui-only wrote history");
        });
    }
    static void nonEdtEditRefused()throws Exception {
        test("non EDT",m->{
            m.isEdt=false;
            yes(!m.deleteOne(m.panel.records.get(0)),"non-EDT edit allowed");
            ids(m.panel,1,2,3);disk(m,1,2,3);
        });
    }
    static void unloadedPanelEditRefused()throws Exception {
        test("not restored",m->{
            m.loaded=false;
            yes(!m.deleteType("mobs"),"edit before load");
            ids(m.panel,1,2,3);disk(m,1,2,3);
        });
    }
    static void ordinaryClearStageWithoutStagingRestoresOneRow()throws Exception {
        test("known failure one",m->{
            m.failure=Failure.STAGE_WRITE_IO;
            Row first=m.panel.records.get(0);
            m.deleteOne(first);
            yes(m.panel.records.contains(first),"original record not restored");
            disk(m,1,2,3);
        });
    }
    static void actualRenameWithoutErrorNoUnnecessaryRollback()throws Exception {
        test("rename successful",m->{
            yes(m.deleteOne(m.panel.records.get(1)),"valid move failed");
            ids(m.panel,1,3);disk(m,1,3);
            eq(m.panel.rollbacks,0,"success restored deletion");
        });
    }
    static void lockedFileGateSerializesPanelTransactions()throws Exception {
        test("filegate",m->{
            CountDownLatch entered=new CountDownLatch(1),release=new CountDownLatch(1);
            Thread worker=new Thread(()->{synchronized(m.fileGate){
                entered.countDown();await(release,"release");
            }},"invented-worker");
            worker.setDaemon(true);worker.start();
            await(entered,"entered");
            final boolean[] result={false};
            Thread deleter=new Thread(()->{
                try{result[0]=m.deleteOne(m.panel.records.get(0));}
                catch(IOException e){throw new RuntimeException(e);}
            },"invented-edit");
            deleter.setDaemon(true);deleter.start();
            release.countDown();
            worker.join(5000);deleter.join(5000);
            yes(!worker.isAlive()&&!deleter.isAlive()&&result[0],"file gate deadlocked");
            ids(m.panel,2,3);disk(m,2,3);
        });
    }
    public static void main(String[] args)throws Exception {
        cleanConfirmedSingleRecord();
        exactIdentityPreservedWithDuplicates();
        stageAppearsAfterPreflightRollsBack();
        stageBeforePreflightRefusesNoMutation();
        stagedWriteIoBeforeRenameRollsBack();
        unsupportedAtomicMoveIsConservativeAmbiguity();
        actualMoveThenExceptionNoRollback();
        noWriteAttemptIsNotProofOfUncommitted();
        rollbackPreservesFilterAndPaging();
        groupWriteSuccessCanChangeFilter();
        typeWriteSuccessRemovesOnlyMatching();
        stagePreflightPreservesNavigation();
        rollbackDoesNotClearUnsafeFlag();
        laterEditRefusedWithoutExplicitRecovery();
        exactSourceAndTypeSelection();
        noUnexpectedAutosaveDuringRollback();
        plainUiOnlyModeDoesNotTouchPersistence();
        nonEdtEditRefused();
        unloadedPanelEditRefused();
        ordinaryClearStageWithoutStagingRestoresOneRow();
        actualRenameWithoutErrorNoUnnecessaryRollback();
        lockedFileGateSerializesPanelTransactions();
        System.out.println("R413_SYNTHETIC_PROVEN_PRE_REPLACE_ROLLBACK_PASS "+passed+" cases");
        System.out.println("R413_AMBIGUOUS_COMMIT_CROSS_PROCESS_AND_REAL_CLIENT_UNPROVEN");
    }
}
