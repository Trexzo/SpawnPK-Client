import java.awt.Window;
import java.io.InputStream;
import java.io.PrintStream;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.Locale;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.zip.ZipFile;

/**
 * R352 DIAGNOSTICS ONLY. Never used by a production client or updater.
 * Requires verified authentic original v309 jar and an ephemeral scratch home.
 * No game binary bundled or launched by CI. SecurityManager is NOT an OS sandbox.
 */
@SuppressWarnings("removal")
public final class R352OriginalLaunchTrace {
    static final String PIN="ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38";
    private static final PrintStream CONTROL_OUT=System.out;
    private static volatile String phase="NOT_INVOKED";
    private static volatile boolean verified=false, invoked=false, windowQueryFinished=false;
    private static volatile int windowsShowing=0;
    private static final AtomicInteger windowQueries=new AtomicInteger();
    private static volatile String failure="NONE";

    private R352OriginalLaunchTrace(){}

    private static void require(boolean value, String reason) {
        if (!value) throw new IllegalArgumentException(reason);
    }
    private static String sha(Path path) throws Exception {
        MessageDigest md=MessageDigest.getInstance("SHA-256");
        try (InputStream in=Files.newInputStream(path)) {
            byte[] buffer=new byte[65536];
            for (int n;(n=in.read(buffer))!=-1;) md.update(buffer,0,n);
        }
        StringBuilder out=new StringBuilder(64);
        for (byte b:md.digest()) out.append(String.format(Locale.ROOT,"%02x",b&255));
        return out.toString();
    }
    private static String safeError(Throwable ex) {
        if (ex instanceof InvocationTargetException) {
            Throwable cause=((InvocationTargetException) ex).getTargetException();
            if (cause!=null) ex=cause;
        }
        String name=ex.getClass().getSimpleName();
        return name.matches("[A-Za-z0-9_]{1,60}")?name:"UNKNOWN";
    }

    public static void main(String[] args) throws Exception {
        require(args.length==3,"R352_EXPECT_JAR_SCRATCH_WAIT");
        Path original=Paths.get(args[0]).toRealPath();
        Path scratch=Paths.get(args[1]).toRealPath();
        int ms=Integer.parseInt(args[2]);
        require(ms>=1000 && ms<=10000,"R352_INVALID_OBSERVATION_DURATION");
        require(Files.isRegularFile(original) && Files.size(original)==17532075L,
                "R352_ORIGINAL_JAR_LENGTH_MISMATCH");
        require(PIN.equals(sha(original)),"R352_ORIGINAL_JAR_HASH_MISMATCH");
        require(Files.isDirectory(scratch) && !scratch.startsWith(original.getParent()),
                "R352_INVALID_SCRATCH");
        try (ZipFile jar=new ZipFile(original.toFile())) {
            require(jar.size()>10000 && jar.getEntry("rs/gui/Launcher.class")!=null,
                    "R352_ORIGINAL_JAR_CLASS_MISSING");
        }
        // JVM must be a disposable child of a bounded supervising parent.
        System.setProperty("user.home",scratch.toString());
        System.setProperty("user.dir",scratch.toString());
        System.setProperty("java.io.tmpdir",scratch.toString());
        R351DeniedEndpointAudit guard=new R351DeniedEndpointAudit(scratch);
        System.setSecurityManager(guard);
        Thread launch=new Thread(()->{
            try {
                phase="CLASS_LOADING";
                Class<?> clazz=Class.forName("rs.gui.Launcher",false,
                        ClassLoader.getSystemClassLoader());
                Path source=Paths.get(clazz.getProtectionDomain().getCodeSource()
                        .getLocation().toURI()).toRealPath();
                require(source.equals(original),"R352_LAUNCHER_SOURCE_MISMATCH");
                verified=true;
                phase="CLASS_VERIFIED";
                Method main=clazz.getMethod("main",String[].class);
                invoked=true;
                phase="MAIN_INVOKED";
                main.invoke(null,(Object)new String[0]);
                phase="MAIN_RETURNED";
            } catch (Throwable ex) {
                failure=safeError(ex);
                phase="LAUNCH_EXCEPTION";
            }
        },"r352-original-v309-startup");
        launch.setDaemon(true);
        launch.start();
        Thread windows=new Thread(()->{
            long end=System.nanoTime()+ms*1000000L;
            try {
                while(System.nanoTime()<end) {
                    int count=0;
                    for (Window w:Window.getWindows()) if (w.isShowing()) count++;
                    windowsShowing=count;
                    windowQueries.incrementAndGet();
                    if (count>0) break;
                    Thread.sleep(150);
                }
            } catch (Throwable ex) {
                // Do not include message or potentially user-controlled text.
            } finally {windowQueryFinished=true;}
        },"r352-window-query");
        windows.setDaemon(true);
        windows.start();
        Thread.sleep(ms);
        StringBuilder json=new StringBuilder(1024);
        json.append("{\"status\":\"R352_ORIGINAL_STARTUP_DENY_TRACE_ONLY\"");
        json.append(",\"original_jar_sha256\":\"").append(PIN).append('"');
        json.append(",\"launcher_class_verified\":").append(verified);
        json.append(",\"original_main_invoked\":").append(invoked);
        json.append(",\"phase\":\"").append(phase).append('"');
        json.append(",\"failure_type\":\"").append(failure).append('"');
        json.append(",\"windows_showing\":").append(windowsShowing);
        json.append(",\"window_query_finished\":").append(windowQueryFinished);
        json.append(",\"window_queries\":").append(windowQueries.get());
        json.append(",\"stdout_redirected\":").append(System.out!=CONTROL_OUT);
        json.append(",\"endpoint_audit\":").append(guard.receiptJson());
        json.append(",\"login_verified\":false");
        json.append(",\"same_pid_reconnect\":\"NOT_TESTED\"}");
        // Channel is captured before original Launcher rebinds System.out/System.err.
        CONTROL_OUT.println("R352_RECEIPT:"+json);
        CONTROL_OUT.flush();
    }
}
