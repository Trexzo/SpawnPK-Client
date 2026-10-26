#!/usr/bin/env python3
"""Strict packet60/nested object151+101 fixture. Independent test, no private game source."""
from dataclasses import dataclass
from typing import Sequence

@dataclass(frozen=True)
class Delta:
    action: str
    x: int
    y: int
    object_id: int | None
    shape: int
    rotation: int

def encode_spawn(x,y,object_id=104,shape=10,rotation=0,base_x=48,base_y=48):
    dx=x-base_x;dy=y-base_y
    if not (0<=dx<=7 and 0<=dy<=7 and 0<=object_id<=65535 and 0<=shape<=31 and 0<=rotation<=3):
        raise ValueError('out of local scene update window')
    return bytes((151,((dx<<4)|dy)+128 & 255,object_id&255,(object_id>>8)&255,(128-((shape<<2)|rotation))&255))

def encode_remove(x,y,shape=10,rotation=0,base_x=48,base_y=48):
    dx=x-base_x;dy=y-base_y
    if not (0<=dx<=7 and 0<=dy<=7 and 0<=shape<=31 and 0<=rotation<=3):
        raise ValueError('outside batch window')
    return bytes((101,(-((shape<<2)|rotation))&255,(dx<<4)|dy))

def encode_outer(parts:Sequence[bytes],base_x=48,base_y=48):
    body=bytes((base_y,(-base_x)&255))+b''.join(parts)
    return b'\x3c'+len(body).to_bytes(2,'big')+body

def decode(wire:bytes)->list[Delta]:
    if len(wire)<5 or wire[0]!=60:raise ValueError('invalid object-container packet')
    length=int.from_bytes(wire[1:3],'big')
    if len(wire)!=length+3:raise ValueError('outer packet length mismatch')
    base_y=wire[3];base_x=(-wire[4])&255
    if not 0<=base_x<=103 or not 0<=base_y<=103:raise ValueError('out of scene base')
    p=5;results=[]
    while p<len(wire):
        op=wire[p];p+=1
        if op==151:
            if len(wire)-p<4:raise ValueError('truncated spawn object')
            packed=(wire[p]-128)&255
            obj=wire[p+1]|wire[p+2]<<8
            shape_rotation=(128-wire[p+3])&255
            p+=4;action='spawn'
        elif op==101:
            if len(wire)-p<2:raise ValueError('truncated object remove')
            shape_rotation=(-wire[p])&255;packed=wire[p+1]
            p+=2;obj=None;action='remove'
        else:raise ValueError('unknown scene object delta opcode '+str(op))
        dx=packed>>4&7;dy=packed&7
        if packed>>7 or dx>7 or dy>7:raise ValueError('invalid delta nibble')
        x,y=base_x+dx,base_y+dy
        if not(1<=x<=102 and 1<=y<=102):raise ValueError('object delta beyond playable tile')
        if shape_rotation>>2!=10:raise ValueError('non-chest test shape')
        results.append(Delta(action,x,y,obj,shape_rotation>>2,shape_rotation&3))
    return results

def main():
    checks=0
    def ck(ok,why):
        nonlocal checks
        if not ok:raise AssertionError(why)
        checks+=1
    payload=encode_outer([encode_spawn(50,49),encode_spawn(51,49),encode_spawn(50,50)])
    ck(len(payload)==20,'three object-151 frames not 20 bytes')
    ck(payload[0]==60,'outer opcode')
    ck(int.from_bytes(payload[1:3],'big')==17,'outer declared short')
    result=decode(payload)
    ck(len(result)==3,'three real object spawns not decoded')
    for i,(x,y) in enumerate(((50,49),(51,49),(50,50))):
        obj=result[i];ck(obj.action=='spawn','not spawn')
        ck(obj.x==x and obj.y==y,'position drift')
        ck(obj.object_id==104,'object ID drift')
        ck(obj.shape==10 and obj.rotation==0,'shape drift')
    removal=encode_outer([encode_remove(51,49)])
    ck(len(removal)==8,'object removal size')
    old=decode(removal)
    ck(len(old)==1 and old[0].action=='remove','remove decoding')
    ck(old[0].x==51 and old[0].y==49,'removed adjacent tile mismatch')
    mixed=decode(encode_outer([encode_spawn(50,49),encode_remove(50,49),encode_spawn(50,49)]))
    ck([o.action for o in mixed]==['spawn','remove','spawn'],'order of updates was lost')
    invalid=[payload[:-1],payload[:-2],payload+b'\0',bytes((61,))+payload[1:],payload[:1]+b'\0\0'+payload[3:],
        payload[:5]+b'\xff'+payload[6:],payload[:5]+b'\x97'+payload[6:9],
        bytes((60,))+payload[1:4]+bytes((2,))+payload[5:]]
    for idx,bad in enumerate(invalid):
        try:decode(bad)
        except ValueError:ck(True,'rejected')
        else:raise AssertionError(f'malformed object frame unexpectedly accepted case={idx}')
    for x,y in ((47,49),(48,56),(56,48),(105,104)):
        try:encode_spawn(x,y)
        except ValueError:ck(True,'rejected illegal local')
        else:raise AssertionError('out-of-window update accepted')
    print('R276_OBJECT_BATCH_FRAMING_PASS checks='+str(checks)+' outer_len=17 three_spawns=true removal=true malformed_rejected=true')

if __name__=='__main__':main()
