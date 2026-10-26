"""v309 R271: fail-closed early client stream decoder incl. source-derived opcode77.
This is a test helper only. Inputs are mock-login per-session ISAAC keys.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'r270'/'r253'))
from isaac import Isaac

KNOWN_FIXED={0:0,121:0,36:4}
VARIABLE_BYTE={164,98,248,77}
def decode(wire,seed):
 c=Isaac(seed);packets=[];i=0;error=None
 while i<len(wire):
  start=i;op=(wire[i]-c.next())&255;i+=1
  if len(packets)==0 and op==185:
   length=2
  elif len(packets) in (1,2) and op==103:
   if i>=len(wire):break
   length=1+wire[i]
  elif op in VARIABLE_BYTE:
   if i>=len(wire):break
   length=1+wire[i]
  elif op in KNOWN_FIXED:length=KNOWN_FIXED[op]
  else:error='unknown opcode '+str(op)+' at offset '+str(start);break
  if i+length>len(wire):break
  payload=bytes(wire[i:i+length]);i+=length
  item={'offset':start,'opcode':op,'length':length}
  if op in VARIABLE_BYTE:
   n=payload[0];p=payload[1:]
   item['declared_size']=n
   if op==164 and n>=5 and n%2==1 and len(p)==n:
    x=((p[0]-128)&255)|(p[1]<<8)
    count=(n-3)//2
    dx=[];dy=[]
    for j in range(count-1):
     dx.append((p[2+2*j]+128)%256-128)
     dy.append((p[3+2*j]+128)%256-128)
    k=2+2*(count-1);y=p[k]|(p[k+1]<<8)
    item['route']={'base_x':x,'base_y':y,'target_x':x+sum(dx),'target_y':y+sum(dy),'waypoints':count,'run':(-p[-1])&255}
  packets.append(item)
 return {'packets':packets,'stop_offset':i,'error':error,'map_ready':any(x['opcode']==121 for x in packets),
         'walk_packets':[x for x in packets if x['opcode']==164 and 'route' in x]}
