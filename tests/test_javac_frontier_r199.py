import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from javac_frontier_r199 import classify

class ClassifyTest(unittest.TestCase):
    def test_paths_and_categories(self):
        log=('/tmp/src/example/A.java:2: error: package org.demo does not exist\n'
             'import org.demo.A;\n'
             '/tmp/src/example/A.java:3: error: cannot find symbol\n'
             '/tmp/src/example/B.java:6: error: incompatible types: bad conversion\n'
             '3 errors\n')
        result=classify(log,'/tmp/src')
        self.assertEqual(3,result['error_count'])
        self.assertEqual(1,result['missing_package_occurrences']['org.demo'])
        self.assertEqual(2,result['source_error_counts']['example/A.java'])
        self.assertEqual(1,result['diagnostic_categories']['cannot find symbol'])
    def test_empty(self):
        self.assertEqual(0,classify('no errors')['error_count'])
if __name__=='__main__':unittest.main()
