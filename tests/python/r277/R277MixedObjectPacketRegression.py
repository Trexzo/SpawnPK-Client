#!/usr/bin/env python3
"""Actual v309 nested 60/151/101 layout for different cached IDs/rotations.
Stand-alone strict fixture; Java test independently verifies actual decoding and scene.
"""
from dataclasses import dataclass
@dataclass(frozen=True)
class Delta:
    action: str
    object_id: int | None
    x: int
    y: int
    shape: int
    rotation: int

def packed(x,y,bx=56,by=52):
    if not (1<=x<=102 and 1<=y<=102 and 0<=x-bx<=7 and 0<=y-by<=7):
        raise ValueError('object coordinate is outside current 8x8 update window')
    return ((x-bx)<<4)|(y-by)

def spawn(id,x,y,rot=0,bx=56,by=52):
    if not(0<=id<=65535 and 0<=rot<=3):raise ValueError('bad id/rot')
    return bytes((151,(packed(x,y,bx,by)+128)&255,id&255,id>>8,(128-(10*4+rot))&255))

def remove(x,y,rot=0,bx=56,by=52):
    if not (0<=rot<=3):raise ValueError('bad rot')
    return bytes((101,(-(10*4+rot))&255,packed(x,y,bx,by)))

def outer(actions,bx=56,by=52):
    if not (0<=bx<=103 and 0<=by<=103):raise ValueError('invalid base')
    payload=bytes((by,(-bx)&255))+b''.join(actions)
    if len(payload)>65535:raise ValueError('oversized object batch')
    return bytes((60,len(payload)>>8,len(payload)&255))+payload

def decode(message):
    if len(message)<5 or message[0]!=60:raise ValueError('missing 60 wrapper')
    size=int.from_bytes(message[1:3],'big')
    if size!=len(message)-3:raise ValueError('not exactly the declared packet60 length')
    by,bx=message[3],(-message[4])&255
    if bx>103 or by>103:raise ValueError('bad packet60 base')
    i=5;out=[]
    while i<len(message):
        opcode=message[i];i+=1
        if opcode==151:
            if i+4>len(message):raise ValueError('truncated151')
            p=(message[i]-128)&255;id=message[i+1]|message[i+2]<<8
            value=(128-message[i+3])&255
            i+=4;kind='spawn'
        elif opcode==101:
            if i+2>len(message):raise ValueError('truncated101')
            value=(-message[i])&255;p=message[i+1];id=None
            i+=2;kind='remove'
        else:raise ValueError('unknown nested opcode')
        # client masks the top bit of packed coordinate through &7, but for
        # this isolated test enforce exact 8x8-window canonical encoding.
        if p&0x88:raise ValueError('noncanonical packed tile')
        x=bx+(p>>4&7);y=by+(p&7)
        if x>102 or y>102:raise ValueError('tile out of playable scene')
        if value>>2!=10:raise ValueError('non-object shape in shape10 test')
        out.append(Delta(kind,id,x,y,value>>2,value&3))
    return out

def main():
    checks=0
    def ck(ok,msg):
        nonlocal checks
        if not ok:raise AssertionError(msg)
        checks+=1
    objects=[(2,56,52,0),(114,60,52,1),(152,59,56,0),(104,63,59,0)]
    encoded=outer([spawn(*o) for o in objects]);parsed=decode(encoded)
    ck(len(encoded)==25 and encoded[1:3]==b'\x00\x16','wrong mixed four-object packet length')
    ck(len(parsed)==4,'did not decode four independent objects')
    for d,o in zip(parsed,objects):
        ck(d.action=='spawn','not a spawn')
        ck((d.object_id,d.x,d.y,d.rotation)==o,'genuine object identity/coordinate/rotation drift')
        ck(d.shape==10,'wrong scene shape')
    rotate=outer([remove(60,52,1),spawn(114,60,52,0)])
    r=decode(rotate)
    ck(len(r)==2 and r[0].action=='remove' and r[1].action=='spawn','rotation replacement order lost')
    ck((r[0].rotation,r[1].rotation)==(1,0),'stale rotation survives remove/reinsert')
    clean=outer([remove(63,59),remove(59,56),remove(60,52),remove(56,52)])
    ck(len(decode(clean))==4,'reverse remove failed')
    ck(all(v.action=='remove' for v in decode(clean)),'unexpected removal mutation')
    ck([v.x for v in decode(clean)]==[63,59,60,56],'reverse removal order changed')
    for name,data in [
        ('short',encoded[:4]),('missing-last-byte',encoded[:-1]),('missing-two',encoded[:-2]),
        ('trailing',encoded+b'\x00'),('wrong-opcode',b'\x3d'+encoded[1:]),
        ('unknown-nested',encoded[:5]+b'\x55'+encoded[6:]),
        ('incorrect-length',encoded[:1]+b'\x00\x01'+encoded[3:]),
        ('high-bit-tile',encoded[:6]+b'\x08'+encoded[7:]),
        ('invalid-shape',encoded[:9]+b'\x00'+encoded[10:]),
        ('truncated-remove',outer([remove(60,52)])[:-1]),
    ]:
        try:decode(data)
        except ValueError:ck(True,'rejected '+name)
        else:raise AssertionError('did not reject invalid '+name)
    for bad in [(-1,56,52,0),(65536,56,52,0),(104,65,52,0),(104,56,60,0),(104,56,52,4),(104,55,52,0)]:
        try:spawn(*bad)
        except ValueError:ck(True,'spawn rejected')
        else:raise AssertionError('invalid spawn accepted '+str(bad))
    for bad in [(60,52,4),(64,52,0),(60,51,0)]:
        try:remove(*bad)
        except ValueError:ck(True,'remove rejected')
        else:raise AssertionError('invalid removal accepted '+str(bad))
    print(f'R277_MIXED_OBJECT_CODEC_PASS checks={checks} count=4 distinct_ids=4 rotated_range=true malformed_rejected=true')
if __name__=='__main__':main()
