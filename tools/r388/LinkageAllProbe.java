import java.net.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;
/** Never initializes the client. Performs class loading and declared-member
 * inspection on an isolated provided candidate/dependency classpath. */
public final class LinkageAllProbe {
    public static void main(String[] args) throws Exception {
        if(args.length < 2) throw new IllegalArgumentException("needs candidate.jar and dependency.jar");
        URL[] cp = {Paths.get(args[0]).toUri().toURL(),Paths.get(args[1]).toUri().toURL()};
        try(URLClassLoader loader = new URLClassLoader(cp, ClassLoader.getPlatformClassLoader()); ZipFile zip = new ZipFile(args[0])) {
            List<String> classes = new ArrayList<>();
            Enumeration<? extends ZipEntry> items=zip.entries();
            while(items.hasMoreElements()) { ZipEntry e=items.nextElement(); if(e.getName().endsWith(".class")) classes.add(e.getName().substring(0,e.getName().length()-6).replace('/','.')); }
            Collections.sort(classes);
            TreeMap<String,Integer> failures=new TreeMap<>(); int linked=0;
            for(String name:classes) {
                try {
                    Class<?> c=Class.forName(name, false, loader);
                    c.getDeclaredFields(); c.getDeclaredMethods(); c.getDeclaredConstructors(); linked++;
                } catch (Throwable e) {
                    String key=e.getClass().getSimpleName()+": "+(e.getMessage()==null?"":e.getMessage());
                    failures.put(key, failures.getOrDefault(key,0)+1);
                    if(failures.size()<=20) System.out.println("FAIL "+name+" "+key);
                }
            }
            System.out.println("TOTAL="+classes.size()+" LINKED_WITH_REFLECTION="+linked+" FAILED="+(classes.size()-linked));
            System.out.println("FAILURE_KINDS="+failures);
            if(classes.size()!=linked) System.exit(1);
        }
    }
}
