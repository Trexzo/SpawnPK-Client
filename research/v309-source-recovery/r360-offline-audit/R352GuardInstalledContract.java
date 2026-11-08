import java.nio.file.Paths;
/** Synthetic-only proof that an installed guard denies all checkConnect calls.
 * Does not create a socket or perform real DNS/network activity. */
@SuppressWarnings("removal")
public final class R352GuardInstalledContract {
    private static void require(boolean ok,String message) {
        if(!ok) throw new AssertionError(message);
    }
    private static boolean refused(Runnable action) {
        try {action.run(); return false;}
        catch (SecurityException expected) {return true;}
    }
    public static void main(String[] args) {
        R351DeniedEndpointAudit guard=new R351DeniedEndpointAudit(Paths.get("r352-scratch"));
        System.setSecurityManager(guard);
        require(System.getSecurityManager()==guard,"GUARD_NOT_INSTALLED");
        require(refused(()->System.getSecurityManager().checkConnect("www.spawnpk.org",-1)),"DNS_NOT_DENIED");
        require(refused(()->System.getSecurityManager().checkConnect("www.spawnpk.org",43594)),"CONNECT_NOT_DENIED");
        require(refused(()->System.setSecurityManager(null)),"GUARD_REMOVAL_NOT_DENIED");
        require(guard.receiptJson().contains("\"dns_checks\":1"),"DNS_NOT_RECORDED");
        require(guard.receiptJson().contains("\"socket_checks\":1"),"CONNECT_NOT_RECORDED");
        System.out.println("R352_INSTALLED_GUARD_CONTRACT_PASS");
    }
}
