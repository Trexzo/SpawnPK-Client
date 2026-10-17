"""Classify full-source javac diagnostics; do not mistake missing-library cascades for source defects."""
from __future__ import annotations
from collections import Counter
import argparse,hashlib,json,re
from pathlib import Path
ERROR = re.compile(r'^(.+?\.java):(\d+): error: (.+)$',re.M)
def classify(log: str, source_root: str = '') -> dict:
    categories, packages, owners = Counter(), Counter(), Counter()
    for path, line, message in ERROR.findall(log):
        path = path.replace('\\','/')
        root=source_root.replace('\\','/').rstrip('/')+'/' if source_root else '/src/'
        if root in path: path=path.split(root,1)[1]
        owners[path]+=1
        if message.startswith('package ') and message.endswith(' does not exist'):
            categories['missing_package']+=1
            packages[message[8:-15]]+=1
        else: categories[message]+=1
    return {'schema':'spk.r199.java11-diagnostic-frontier.v1',
        'error_count':sum(categories.values()),
        'diagnostic_categories':dict(sorted(categories.items())),
        'missing_package_occurrences':dict(sorted(packages.items())),
        'source_error_counts':dict(sorted(owners.items())),
        'limitations':['Requires Java 11 compiler profile for comparability',
            'No dependency resolution or original bytecode proof',
            'Compiler diagnostics may include cascades']}
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--javac-stderr',required=True,type=Path)
    p.add_argument('--source-root',default='')
    p.add_argument('--report',required=True,type=Path)
    a=p.parse_args()
    data=a.javac_stderr.read_bytes()
    report=classify(data.decode('utf-8',errors='replace'),a.source_root)
    report['stderr_sha256']=hashlib.sha256(data).hexdigest()
    with a.report.open('x',encoding='utf-8') as file:
        json.dump(report,file,indent=2,sort_keys=True);file.write('\n')
if __name__=='__main__':main()
