import java.io.File;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.Permission;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * R351 - isolated diagnostic guard. All socket attempts are denied, including localhost.
 * NEVER use this class in the live game: only in a scratch JVM with an external supervisor.
 * This is a source-only audit component; it does not execute any game binary.
 */
@SuppressWarnings("removal")
public final class R351DeniedEndpointAudit extends SecurityManager {
    private final Path scratch;
    private final int cap;
    private static final int MAX_UNKNOWN_ALIASES = 128;
    private static final int MAX_HOST_CHARS = 253;
    private final List<Attempt> observations = new ArrayList<>();
    private final Map<String, String> anonymized = new LinkedHashMap<>();
    private int overflow;
    private int dnsChecks;
    private int socketChecks;

    private static final class Attempt {
        final String destination;
        final int port;
        final String kind;
        Attempt(String destination, int port, String kind) {
            this.destination = destination;
            this.port = port;
            this.kind = kind;
        }
    }

    public R351DeniedEndpointAudit(Path scratch) {
        this(scratch, 128);
    }

    R351DeniedEndpointAudit(Path scratch, int cap) {
        if (scratch == null || cap < 1 || cap > 1024) {
            throw new IllegalArgumentException("INVALID_R351_GUARD_INPUT");
        }
        this.scratch = scratch.toAbsolutePath().normalize();
        this.cap = cap;
    }

    private String classify(String host) {
        // Bound memory before allocating a normalized copy of an untrusted name.
        if (host != null && host.length() > MAX_HOST_CHARS) return "OTHER_OVERFLOW";
        String normalized = host == null ? "" : host.toLowerCase(Locale.ROOT).trim();
        if (normalized.equals("www.spawnpk.org")) return "KNOWN_GAME_HOST";
        if (normalized.equals("localhost") || normalized.equals("127.0.0.1")
            || normalized.equals("::1") || normalized.equals("0:0:0:0:0:0:0:1")) {
            return "LOOPBACK";
        }
        if (normalized.isEmpty()) return "UNKNOWN_EMPTY";
        String alias = anonymized.get(normalized);
        if (alias == null) {
            if (anonymized.size() >= MAX_UNKNOWN_ALIASES) return "OTHER_OVERFLOW";
            alias = "OTHER_" + (anonymized.size() + 1);
            anonymized.put(normalized, alias);
        }
        return alias;
    }

    @Override public synchronized void checkConnect(String host, int port) {
        String label = classify(host);
        String kind = port == -1 ? "DNS_RESOLVE_CHECK" : "SOCKET_CONNECT_CHECK";
        if (port == -1) dnsChecks++;
        else socketChecks++;
        if (observations.size() < cap) observations.add(new Attempt(label, port, kind));
        else overflow++;
        throw new SecurityException("R351_DENY_ALL_NETWORK");
    }

    @Override public void checkListen(int port) {
        throw new SecurityException("R351_NO_LISTENERS");
    }

    @Override public void checkAccept(String host, int port) {
        throw new SecurityException("R351_NO_INBOUND_CLIENTS");
    }

    @Override public void checkExec(String command) {
        throw new SecurityException("R351_NO_CHILD_EXEC");
    }

    @Override public void checkWrite(String file) {
        Path destination = Paths.get(file).toAbsolutePath().normalize();
        if (!destination.startsWith(scratch)) {
            throw new SecurityException("R351_NO_WRITES_OUTSIDE_SCRATCH");
        }
    }

    @Override public void checkDelete(String file) {
        checkWrite(file);
    }

    @Override public void checkPermission(Permission permission) {
        if (permission instanceof RuntimePermission) {
            String name = permission.getName();
            if ("setSecurityManager".equals(name) || name.startsWith("exitVM")) {
                throw new SecurityException("R351_SECURITY_GUARD_CANNOT_BE_REMOVED");
            }
        }
    }

    /** Sanitized, schema-limited evidence; never includes unknown raw hostnames. */
    public synchronized String receiptJson() {
        StringBuilder out = new StringBuilder(512);
        out.append("{\"status\":\"R351_DENIED_ENDPOINT_DIAGNOSTIC_ONLY\"");
        out.append(",\"policy\":\"DENY_ALL_NETWORK\"");
        out.append(",\"dns_checks\":").append(dnsChecks);
        out.append(",\"socket_checks\":").append(socketChecks);
        out.append(",\"overflow_checks\":").append(overflow);
        out.append(",\"attempts\":[");
        for (int i = 0; i < observations.size(); i++) {
            Attempt a = observations.get(i);
            if (i > 0) out.append(',');
            out.append("{\"kind\":\"").append(a.kind).append("\"");
            out.append(",\"destination\":\"").append(a.destination).append("\"");
            out.append(",\"port\":").append(a.port).append('}');
        }
        out.append("]");
        out.append(",\"authenticated_login\":\"NOT_TESTED\"");
        out.append(",\"original_same_pid_reconnect\":\"NOT_TESTED\"");
        out.append(",\"original_inventory_recovery\":\"NOT_TESTED\"");
        out.append('}');
        return out.toString();
    }
}
