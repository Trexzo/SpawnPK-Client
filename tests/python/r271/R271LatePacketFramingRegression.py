"""R271 standalone 11+ check synthetic framing fixture; NOT a socket receipt."""
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parent/'r270'/'r253'))
from isaac import Isaac
from decode_outbound_walk_r271 import decode

checks=0
def ck(value,why):
 global checks
 if not value:raise AssertionError(why)
 checks+=1
seed=[13,22,37,41];cipher=Isaac(seed)
walk=bytes([7,1,12,1,1,128,12,0])
parts=[(185,b'\x03\x90'),(103,b'\x02Hi'),(103,b'\x02Hi'),(0,b''),(121,b''),
       (164,walk),(0,b''),(164,walk),(77,b'\x05ABCDE'),(0,b''),(164,walk),(164,walk)]
wire=b''.join(bytes([cipher.encode_opcode(op)])+p for op,p in parts)
report=decode(wire,seed)
ck(report['error'] is None,'unknown source-backed opcode')
ck(report['map_ready'],'map-ready absent')
ck([p['opcode'] for p in report['packets']]==[op for op,_ in parts],'ISAAC opcode sequence drift')
ck(len(report['walk_packets'])==4,'not all 4 walks parsed')
ck(report['stop_offset']==len(wire),'unconsumed bytes')
ck(any(p['opcode']==77 and p['length']==6 for p in report['packets']),'77 variable-byte framing')
for i in range(13,len(wire),13):
 truncated=decode(wire[:i],seed)
 ck(truncated['stop_offset']<=i,'parser overread on truncation')
ck(decode(wire[:-1],seed)['stop_offset']<len(wire),'final truncated frame overread')
print('R271_LATE_PACKET77_ISAAC_WALK_PASS checks='+str(checks))
