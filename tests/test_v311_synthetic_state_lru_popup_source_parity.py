"""Independent Java9/JDK-only source parity for small state and UI helpers.

All classes here are synthetic; no private original v311 Java or game binary.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.standalone_source_parity import (
    StandaloneSourceParityError, verify_standalone_sources,
)

SOURCES = {
 "rs/synthetic87/Gauge.java": """
package rs.synthetic87;
public class Gauge {
 private int count;
 private float ratio=1.0f;
 public Gauge(int n){count=n;}
 public int count(){return count;}
 public float ratio(){return ratio;}
 public void update(int n,float f){count=n;ratio=f;}
}
""",
 "rs/synthetic87/RecentItems.java": """
package rs.synthetic87;
import java.util.LinkedHashMap;
import java.util.Map;
public final class RecentItems extends LinkedHashMap<Long,Long> {
 public RecentItems(boolean access){super(8,.75f,access);}
 @Override protected boolean removeEldestEntry(Map.Entry<Long,Long> entry){
  return size()>5;
 }
}
""",
 "rs/synthetic87/TicketBox.java": """
package rs.synthetic87;
import java.util.ArrayList;
import java.util.List;
public final class TicketBox {
 public List<Integer> events;
 public Gauge gauge;
 public TicketBox(int first){
  gauge=new Gauge(first);
  events=new ArrayList<Integer>();
  events.add(first);
 }
 public void append(int v){events.add(v);}
}
""",
 "rs/synthetic87/PopupWrapper.java": """
package rs.synthetic87;
import java.awt.Component;
import javax.swing.Popup;
import javax.swing.PopupFactory;
public final class PopupWrapper extends PopupFactory {
 @Override protected Popup getPopup(Component owner,Component contents,
 int x,int y,boolean lightweight){
  return super.getPopup(owner,contents,x,y,true);
 }
}
""",
}

PROBE = """
import rs.synthetic87.*;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.awt.Component;
import javax.swing.Popup;
public class Synthetic87Probe {
 public static void main(String[] unused)throws Exception{
  int cases=0;
  for(int n:new int[]{Integer.MIN_VALUE,-7,0,7,Integer.MAX_VALUE}){
   Gauge g=new Gauge(n);g.update(n+1,Float.intBitsToFloat(n));
   System.out.println("G:"+g.count()+":"+Float.floatToRawIntBits(g.ratio()));
   cases++;
  }
  for(int n:new int[]{-1,0,7}){
   TicketBox b=new TicketBox(n);b.append(n+4);
   System.out.println("B:"+b.events+":"+b.gauge.count());cases++;
  }
  for(boolean order:new boolean[]{false,true}){
   RecentItems map=new RecentItems(order);
   for(long i=0;i<8;i++)map.put(i,i*11);
   System.out.println("M:"+order+":"+map.size()+":"+map.keySet().iterator().next());cases++;
  }
  PopupWrapper popup=new PopupWrapper();
  Method method=PopupWrapper.class.getDeclaredMethod("getPopup",
   Component.class,Component.class,int.class,int.class,boolean.class);
  System.out.println("P:"+(popup instanceof javax.swing.PopupFactory)+":"+
   Modifier.isProtected(method.getModifiers())+":"+
   method.getReturnType().equals(Popup.class));cases++;
  if(cases!=11)throw new AssertionError("wrong toy count");
 }
}
"""

def sha(blob:bytes)->str:
 return hashlib.sha256(blob).hexdigest()

def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=50)
 if p.returncode:raise AssertionError(p.stderr[-1800:])
 return p.stdout

@unittest.skipUnless(
 all(shutil.which(x) for x in ('javac','javap','java')),'JDK9+ required')
class Synthetic87SourceParity(unittest.TestCase):
 def fixture(self,root:Path):
  source=root/'source'
  for name,body in SOURCES.items():
   dest=source/name;dest.parent.mkdir(parents=True,exist_ok=True)
   dest.write_text(body,encoding='utf-8')
  built=root/'original-classes';built.mkdir()
  run(['javac','--release','9','-proc:none','-g:none',
       '-classpath',str(root/'empty-cp'),
       '-sourcepath',str(root/'empty-sp'),'-d',str(built),
       *[str(source/name) for name in sorted(SOURCES)]])
  archive=root/'synthetic-original.jar'
  with zipfile.ZipFile(archive,'w') as z:
   for path in sorted(built.rglob('*.class')):
    z.writestr(path.relative_to(built).as_posix(),path.read_bytes())
  with zipfile.ZipFile(archive) as z:
   pins={name:sha(z.read(name)) for name in z.namelist()}
  self.assertEqual(len(pins),4)
  return source,archive,pins

 def test_four_class_closure_and_eleven_headless_behaviors(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source,archive,pins=self.fixture(root)
   result=verify_standalone_sources(archive,source,root/'rebuilt',
     original_sha256=sha(archive.read_bytes()),class_sha256=pins)
   self.assertTrue(result['all_passed'])
   self.assertEqual(result['total_classes'],4)
   self.assertFalse(result['original_game_binary_on_compile_classpath'])
   self.assertGreaterEqual(result[
    'explicit_original_project_dependency_closure']['source_project_dependency_edges'],1)
   probe=root/'Synthetic87Probe.java'
   probe.write_text(PROBE,encoding='utf-8')
   run(['javac','--release','9','-cp',str(archive),'-d',str(root),str(probe)])
   outputs=[]
   for cp in (archive,root/'rebuilt'/'classes'):
    outputs.append(run(['java','-Djava.awt.headless=true',
      '-cp',str(root)+os.pathsep+str(cp),'Synthetic87Probe']))
   self.assertEqual(outputs[0],outputs[1])
   self.assertEqual(len(outputs[0].splitlines()),11)

 def test_changed_gauge_getter_refused(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source,archive,pins=self.fixture(root)
   target=source/'rs/synthetic87/Gauge.java'
   original=target.read_text()
   altered=original.replace('return count;', 'return count+1;')
   self.assertNotEqual(original,altered)
   target.write_text(altered,encoding='utf-8')
   with self.assertRaisesRegex(StandaloneSourceParityError,
       'ORDERED_JVM_INSTRUCTIONS_OR_DECLARATIONS_MISMATCH'):
    verify_standalone_sources(archive,source,root/'rejected',
      original_sha256=sha(archive.read_bytes()),class_sha256=pins)

 def test_missing_dependency_source_refused(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source,archive,pins=self.fixture(root)
   (source/'rs/synthetic87/Gauge.java').unlink()
   with self.assertRaises(StandaloneSourceParityError):
    verify_standalone_sources(archive,source,root/'rejected',
      original_sha256=sha(archive.read_bytes()),class_sha256=pins)

 def test_wrong_authority_hash_refused(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source,archive,pins=self.fixture(root)
   with self.assertRaisesRegex(StandaloneSourceParityError,'WRONG_ORIGINAL_JAR'):
    verify_standalone_sources(archive,source,root/'rejected',
      original_sha256='0'*64,class_sha256=pins)

if __name__=='__main__':
 unittest.main(verbosity=2)
