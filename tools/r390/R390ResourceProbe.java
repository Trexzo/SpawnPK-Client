import java.io.*;
import java.net.*;
import java.nio.file.*;
import java.security.*;
import java.util.*;
import java.util.zip.*;

/** R390: isolated, no-initialization resource-visibility probe.
 * Takes pre-verified local JARs; no client entrypoint, native code or network.
 */
public final class R390ResourceProbe {
    static void require(boolean pass, String why) {
        if (!pass) throw new IllegalStateException(why);
    }
    static String digest(InputStream in) throws Exception {
        MessageDigest md = MessageDigest.getInstance("SHA-256");
        byte[] buf = new byte[65536];
        long n = 0;
        try (InputStream stream = in) {
            for (int read; (read = stream.read(buf)) != -1;) {
                n += read;
                require(n <= 128L * 1024 * 1024, "RESOURCE_OVERSIZE");
                md.update(buf, 0, read);
            }
        }
        return Base64.getEncoder().encodeToString(md.digest());
    }
    public static void main(String[] args) throws Exception {
        require(args.length == 4, "NEEDS_CANDIDATE_PRIMARY_COMPANION_EXPECTED_COUNT");
        Path candidate = Paths.get(args[0]).toRealPath();
        Path primary = Paths.get(args[1]).toRealPath();
        Path companion = Paths.get(args[2]).toRealPath();
        int expected = Integer.parseInt(args[3]);
        require(expected > 0 && expected < 10000, "INVALID_COUNT");
        URL[] urls = {candidate.toUri().toURL(),primary.toUri().toURL(),companion.toUri().toURL()};
        try (URLClassLoader loader = new URLClassLoader(urls, ClassLoader.getPlatformClassLoader());
             ZipFile original = new ZipFile(companion.toFile())) {
            Class<?> launcher = Class.forName("rs.gui.Launcher", false, loader);
            require(launcher.getClassLoader() == loader, "LAUNCHER_WRONG_LOADER");
            Set<String> names = new HashSet<>();
            int total = 0, classEntries = 0, missing = 0, changed = 0, shadowed = 0;
            Enumeration<? extends ZipEntry> items = original.entries();
            while(items.hasMoreElements()) {
                ZipEntry entry = items.nextElement();
                String name = entry.getName();
                require(names.add(name), "DUPLICATE_RESOURCE");
                require(!name.startsWith("/") && !name.contains("\\") && !name.contains(".."), "UNSAFE_RESOURCE_PATH");
                if (entry.isDirectory()) continue;
                if (name.endsWith(".class")) {classEntries++;continue;}
                total++;
                URL uri = loader.getResource(name);
                if (uri == null) {missing++;continue;}
                if (!"jar".equals(uri.getProtocol())) {shadowed++;continue;}
                URLConnection conn = uri.openConnection();
                if (!(conn instanceof JarURLConnection)) {shadowed++;continue;}
                URI found = ((JarURLConnection)conn).getJarFileURL().toURI();
                if (!companion.toUri().equals(found)) {shadowed++;continue;}
                String expectedDigest = digest(original.getInputStream(entry));
                String actualDigest = digest(uri.openStream());
                if (!expectedDigest.equals(actualDigest)) changed++;
            }
            System.out.println("R390_RESOURCE_VISIBILITY " +
                "RESOURCE_ENTRIES="+total+" VISIBLE_IDENTICAL="+(total-missing-changed-shadowed)+
                " MISSING="+missing+" CHANGED="+changed+" SHADOWED="+shadowed+
                " COMPANION_CLASSES="+classEntries+" LAUNCHER_NO_INIT=PASS");
            require(total == expected && classEntries == 0 && missing == 0 &&
                    changed == 0 && shadowed == 0, "RESOURCE_RESOLUTION_FAILED");
        }
    }
}
