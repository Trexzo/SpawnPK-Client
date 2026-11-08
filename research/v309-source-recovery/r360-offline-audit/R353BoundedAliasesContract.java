import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.file.Paths;
import java.util.Map;

/** Synthetic-only stress test. No original JAR, DNS, sockets or game launches. */
public final class R353BoundedAliasesContract {
    private static void require(boolean b, String reason) {
        if (!b) throw new AssertionError(reason);
    }
    public static void main(String[] ignored) throws Exception {
        R351DeniedEndpointAudit guard = new R351DeniedEndpointAudit(Paths.get("r353-scratch"));
        for (int i=0;i<20000;i++) {
            try { guard.checkConnect("test-host-"+i+".example.invalid",443); }
            catch (SecurityException expected) { continue; }
            throw new AssertionError("NETWORK_GUARD_FAILED");
        }
        Field field=R351DeniedEndpointAudit.class.getDeclaredField("anonymized");
        field.setAccessible(true);
        Map<?,?> names=(Map<?,?>) field.get(guard);
        require(names.size()==128,"UNBOUNDED_HOST_ALIAS_MAP");
        Method classify=R351DeniedEndpointAudit.class.getDeclaredMethod("classify",String.class);
        classify.setAccessible(true);
        String label=(String)classify.invoke(guard,"test-host-20001.example.invalid");
        require("OTHER_OVERFLOW".equals(label),"UNKNOWN_ALIAS_EXHAUSTION");
        String huge="a".repeat(100000);
        label=(String)classify.invoke(guard,huge);
        require("OTHER_OVERFLOW".equals(label),"OVERSIZE_HOST_REDACTION");
        String receipt=guard.receiptJson();
        require(!receipt.contains("example.invalid"),"RAW_UNKNOWN_HOST_EXPOSED");
        require(receipt.contains("\"overflow_checks\":19872"),"UNCAPPED_RECEIPT_EVENTS");
        require(receipt.contains("\"socket_checks\":20000"),"LOST_COUNT");
        System.out.println("R353_BOUNDED_ALIASES_CONTRACT_PASS");
    }
}
