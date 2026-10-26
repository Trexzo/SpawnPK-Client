"""Fail-closed decoder for *known* early client C>S packets (offline fixture)."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'r253'))
from isaac import Isaac

KNOWN_FIXED={0:0,121:0,36:4}
VARIABLE_BYTE={164,98,248}

def decode(wire,seed):
 c=Isaac(seed)
 packets=[];i=0;err=None
 while i<len(wire):
  start=i;opcode=(wire[i]-c.next())&255;i+=1
  if len(packets)==0 and opcode==185:length=2
  elif len(packets) in (1,2) and opcode==103:
   if i>=len(wire):break
   length=1+wire[i]
  elif opcode in VARIABLE_BYTE:
   if i>=len(wire):break
   length=1+wire[i]
  elif opcode in KNOWN_FIXED:length=KNOWN_FIXED[opcode]
  else:err=f'unknown opcode {opcode} at offset {start}';break
  if i+length>len(wire):break
  payload=bytes(wire[i:i+length]);i+=length
  pkt={'offset':start,'opcode':opcode,'length':length}
  if opcode in VARIABLE_BYTE:
   n=payload[0];p=payload[1:]
   pkt['declared_size']=n
   if opcode==164 and n>=5 and n%2==1 and len(p)==n:
    first_x=((p[0]-128)&255)|(p[1]<<8)
    waypoint_count=(n-3)//2
    dx=[];dy=[]
    for j in range(waypoint_count-1):
     dx.append((p[2+2*j]+128)%256-128)
     dy.append((p[3+2*j]+128)%256-128)
    yoff=2+2*(waypoint_count-1)
    first_y=p[yoff]|(p[yoff+1]<<8)
    target_x=first_x+sum(dx);target_y=first_y+sum(dy)
    pkt['route']={'base_x':first_x,'base_y':first_y,'target_x':target_x,'target_y':target_y,'waypoints':waypoint_count,'run':(-p[-1])&255}
  packets.append(pkt)
 return {'packets':packets,'stop_offset':i,'error':err,'map_ready':any(p['opcode']==121 for p in packets),
         'walk_packets':[p for p in packets if p['opcode']==164 and 'route' in p]}

if __name__=='__main__':
 def check(ok,why):
  global checks
  if not ok:raise AssertionError(why)
  checks+=1
 checks=0
 # These exact 9 bytes were independently produced by the real R265-built
 # Java Client.method3573(0) using seed [13,22,37,41], NOT a crafted packet.
 captured=bytes([112,7,1,12,1,1,128,12,0])
 proof=decode(captured,[13,22,37,41]);walks=proof['walk_packets']
 check(proof['error'] is None,'decode errored')
 check(len(walks)==1,'missing real movement')
 check(walks[0]['opcode']==164,'incorrect raw opcode')
 route=walks[0]['route']
 check(route['base_x']==3201 and route['base_y']==3200,'wrong first waypoint')
 check(route['target_x']==3202 and route['target_y']==3201,'wrong destination')
 check(route['waypoints']==2 and route['run']==0,'path/run drift')
 check(proof['stop_offset']==len(captured),'not all wire consumed')
 for n in range(len(captured)):
  check(len(decode(captured[:n],[13,22,37,41])['walk_packets'])==0,'truncation decoded complete movement at '+str(n))
 check(not decode(bytes([0]),[13,22,37,41])['walk_packets'],'random junk accepted')
 bad=bytearray(captured);bad[1]=4
 check(not decode(bad,[13,22,37,41])['walk_packets'],'bad length was accepted as route')
 # Extend an authentic early-packet framing example to contain a moving packet.
 seed=[13,22,37,41];c=Isaac(seed)
 segments=[(185,bytes(2)),(103,b'\x02XY'),(103,b'\x02ZZ'),(0,b''),(121,b''),
           (164,bytes([7,1,12,1,1,128,12,0]))]
 raw=b''.join(bytes([c.encode_opcode(op)])+body for op,body in segments)
 proof=decode(raw,seed)
 check(proof['map_ready'],'map ready lost in combined stream')
 check([p['opcode'] for p in proof['packets']]==[185,103,103,0,121,164],'packet boundaries changed')
 check(len(proof['walk_packets'])==1,'no walk after map ready')
 check(proof['walk_packets'][0]['route']['target_x']==3202,'combined waypoint corruption')
 check(proof['error'] is None,'unexpected combined parser error')
 print('R270_WALK_SERVER_DECODER_PASS checks='+str(checks))
