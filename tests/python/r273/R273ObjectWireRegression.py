#!/usr/bin/env python3
"""R273: independently decode exact real Client.handleMenuAction output (R265 JAR)."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'r270'/'r253'))
from isaac import Isaac

CAPTURED={
  502:bytes.fromhex('2e07010c0101800c00b8020c00680c01'),
  900:bytes.fromhex('2e07010c0101800c0030e800810c0c02'),
}
checks=0
def ck(ok,why):
 global checks
 if not ok:raise AssertionError(why)
 checks+=1

def decode(wire, seed):
 cipher=Isaac(seed);offset=0;records=[]
 while offset<len(wire):
  start=offset;op=(wire[offset]-cipher.next())&255;offset+=1
  if op==98:
   if offset>=len(wire):offset=start;break
   size=wire[offset];offset+=1
   if size<5 or size>53 or size%2==0 or offset+size>len(wire):offset=start;break
   data=wire[offset:offset+size];offset+=size
   records.append({'opcode':op,'size':size,'offset':start,'payload':data})
  elif op in (132,252):
   if offset+6>len(wire):offset=start;break
   data=wire[offset:offset+6];offset+=6
   if op==132:
    x=((data[0]-128)&255)|(data[1]<<8)
    obj_id=(data[2]<<8)|data[3]
    y=(data[4]<<8)|((data[5]-128)&255)
   else:
    obj_id=((data[0]-128)&255)|(data[1]<<8)
    y=data[2]|(data[3]<<8)
    x=(data[4]<<8)|((data[5]-128)&255)
   records.append({'opcode':op,'size':6,'offset':start,'object_id':obj_id,'world_x':x,'world_y':y,'payload':data})
  else:offset=start;break
 return records,offset

for action,wire in CAPTURED.items():
 records,offset=decode(wire,[13,22,37,41]);ck(offset==len(wire),'full wire consumed')
 ck(len(records)==2,'route + object both decoded')
 ck(records[0]['opcode']==98,'actual approach opcode')
 ck(records[0]['size']==7,'actual path size')
 ck(records[1]['opcode']==(132 if action==502 else 252),'real action opcode mismatch')
 ck(records[1]['offset']==9,'real object frame offset mismatch')
 ck(records[1]['object_id']==104,'real chest id mismatch')
 ck(records[1]['world_x']==3202 and records[1]['world_y']==3201,'actual target mismatch')
 for n in range(9,16):
  _,at=decode(wire[:n],[13,22,37,41])
  ck(at<=n and at<16,'truncated object packet accepted')
 ck(decode(wire+b'\x7f',[13,22,37,41])[1]==len(wire),'trailing unknown opcode accepted')
ck(len(CAPTURED)==2,'source captures lost')
print('R273_INDEPENDENT_REAL_OBJECT_WIRE_PASS checks='+str(checks)+' actions=Search/Shut ids=104 coords=3202,3201')
