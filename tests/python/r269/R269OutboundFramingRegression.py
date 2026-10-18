"""Pure framing regression. Real session ISAAC integration is evidenced separately.

A caller supplies the matching session cipher's successive 8-bit outputs. This
module only decodes packet boundaries supported by the initial v309 client
protocol; it refuses unknown frames instead of searching ciphertext for bytes.
"""

def decode_early_stream(wire: bytes, next_cipher_byte):
    offset=0;opcodes=[];offsets=[];error=None
    while offset < len(wire) and len(opcodes)<128:
        start=offset
        try:
            opcode=(wire[offset]-next_cipher_byte())&255
        except StopIteration:
            error='ISAAC stream exhausted';break
        offset+=1
        position=len(opcodes)
        if position==0 and opcode==185:
            payload_length=2
        elif position in (1,2) and opcode==103:
            if offset>=len(wire):error='missing chat length';break
            payload_length=1+wire[offset]
        elif position>=3 and opcode in (0,121):
            payload_length=0
        else:
            error=f'unexpected opcode {opcode} at {start}';break
        if offset+payload_length>len(wire):
            error=f'truncated opcode {opcode} at {start}';break
        offsets.append(start);opcodes.append(opcode);offset+=payload_length
        if opcode==121:break
    return {'opcodes':opcodes,'offsets':offsets,'map_ready_121_received':
            len(opcodes)>=4 and opcodes[:3]==[185,103,103] and opcodes[-1]==121 and not error,
            'error':error}

def selftest():
    checks=0
    packets=[(185,b'\x03\x90'),(103,b'\x10'+b'a'*16),(103,b'\x08'+b'b'*8)]
    packets += [(0,b'')]*5+[(121,b'')]
    masking=list(range(5,5+3*len(packets),3))
    raw=b''.join(bytes([(opcode+masking[i])&255])+payload for i,(opcode,payload) in enumerate(packets))
    def test(wire):
        it=iter(masking)
        return decode_early_stream(wire,lambda:next(it))
    proof=test(raw)
    assert proof['map_ready_121_received'];checks+=1
    assert proof['opcodes']==[185,103,103,0,0,0,0,0,121];checks+=1
    assert proof['offsets']==[0,3,21,31,32,33,34,35,36];checks+=1
    assert not test(raw[:-1])['map_ready_121_received'];checks+=1
    assert not test(raw[:2])['map_ready_121_received'];checks+=1
    assert not test(raw[:4])['map_ready_121_received'];checks+=1
    invalid=bytes([99+masking[0]])+raw[1:]
    assert not test(invalid)['map_ready_121_received'];checks+=1
    print(f'R269_OUTBOUND_FRAME_BOUNDARY_PASS checks={checks}')

if __name__=='__main__':selftest()
