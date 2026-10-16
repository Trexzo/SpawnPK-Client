"""R203: exact, private, fail-closed single-source assertion owner candidate.

Input must be manually SHA-approved. Output is a new private ZIP, never
published to GitHub. This is NOT proof of original client bytecode parity.
"""
import argparse, hashlib, zipfile
from pathlib import Path

def patch(inp:Path,out:Path,member:str,approved_sha:str,old_owner:str,new_owner:str):
    with zipfile.ZipFile(inp) as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or member not in names or not member.startswith("src/") or not member.endswith(".java") or ".." in Path(member).parts:
            raise ValueError("Unsafe or missing source member")
        blob=z.read(member)
        if hashlib.sha256(blob).hexdigest().lower()!=approved_sha.lower():
            raise ValueError("SHA-256 preflight failure")
        old=(old_owner+".class.desiredAssertionStatus()").encode()
        new=(new_owner+".class.desiredAssertionStatus()").encode()
        if blob.count(old)!=1:raise ValueError("Assertion reference not unique")
        updated=blob.replace(old,new)
        with zipfile.ZipFile(out,"x",zipfile.ZIP_DEFLATED) as target:
            for name in names:
                target.writestr(name,updated if name==member else z.read(name))
    return hashlib.sha256(updated).hexdigest()

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-zip",type=Path,required=True)
    p.add_argument("--out-zip",type=Path,required=True)
    p.add_argument("--member",required=True)
    p.add_argument("--approved-sha256",required=True)
    p.add_argument("--old-owner",required=True)
    p.add_argument("--new-owner",required=True)
    a=p.parse_args()
    print(patch(a.source_zip,a.out_zip,a.member,a.approved_sha256,a.old_owner,a.new_owner))
