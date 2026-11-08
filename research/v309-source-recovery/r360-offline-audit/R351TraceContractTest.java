import java.nio.file.Paths;

/** Source-only test. Never launches game or performs network I/O. */
public final class R351TraceContractTest {
    private static void expectDenied(Runnable operation, String marker) {
        try { operation.run(); throw new AssertionError("DENIAL_NOT_ENFORCED:" + marker); }
        catch (SecurityException expected) { /* expected */ }
    }
    private static void check(boolean condition, String reason) {
        if (!condition) throw new AssertionError(reason);
    }
    public static void main(String[] args) {
        R351DeniedEndpointAudit guard = new R351DeniedEndpointAudit(Paths.get("r351-scratch"), 3);
        expectDenied(() -> guard.checkConnect("www.spawnpk.org", -1), "DNS");
        expectDenied(() -> guard.checkConnect("www.spawnpk.org", 43594), "SOCKET");
        expectDenied(() -> guard.checkConnect("analytics.example.invalid", 443), "OTHER");
        expectDenied(() -> guard.checkConnect("analytics.example.invalid", 443), "OVERFLOW");
        expectDenied(() -> guard.checkListen(43594), "LISTEN");
        expectDenied(() -> guard.checkAccept("127.0.0.1", 10000), "ACCEPT");
        expectDenied(() -> guard.checkExec("any"), "EXEC");
        expectDenied(() -> guard.checkWrite("outside-r351.txt"), "WRITE");
        expectDenied(() -> guard.checkDelete("outside-r351.txt"), "DELETE");
        expectDenied(() -> guard.checkPermission(new RuntimePermission("setSecurityManager")), "REMOVE_GUARD");
        expectDenied(() -> guard.checkPermission(new RuntimePermission("exitVM.0")), "EXIT");
        String r = guard.receiptJson();
        check(r.contains("\"dns_checks\":1"), "DNS_COUNT");
        check(r.contains("\"socket_checks\":3"), "SOCKET_COUNT");
        check(r.contains("\"overflow_checks\":1"), "OVERFLOW_COUNT");
        check(r.contains("\"destination\":\"KNOWN_GAME_HOST\""), "GAME_HOST_CLASS");
        check(r.contains("\"destination\":\"OTHER_1\""), "UNKNOWN_LABEL");
        check(!r.contains("analytics.example.invalid"), "RAW_HOSTNAME_LEAK");
        check(r.contains("\"original_same_pid_reconnect\":\"NOT_TESTED\""), "FALSE_RECONNECT_CLAIM");
        check(r.contains("\"policy\":\"DENY_ALL_NETWORK\""), "SAFETY_POLICY");
        System.out.println("R351_SOURCE_ONLY_CONTRACT_PASS");
        System.out.println(r);
    }
}
