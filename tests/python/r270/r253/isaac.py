"""Source-compatible unsigned-32 ISAAC stream for a localhost test server."""
MASK=0xffffffff

def mix(a):
    a=list(a)
    a[0]=(a[0]^(a[1]<<11))&MASK; a[3]=(a[3]+a[0])&MASK; a[1]=(a[1]+a[2])&MASK
    a[1]=(a[1]^(a[2]>>2))&MASK; a[4]=(a[4]+a[1])&MASK; a[2]=(a[2]+a[3])&MASK
    a[2]=(a[2]^(a[3]<<8))&MASK; a[5]=(a[5]+a[2])&MASK; a[3]=(a[3]+a[4])&MASK
    a[3]=(a[3]^(a[4]>>16))&MASK; a[6]=(a[6]+a[3])&MASK; a[4]=(a[4]+a[5])&MASK
    a[4]=(a[4]^(a[5]<<10))&MASK; a[7]=(a[7]+a[4])&MASK; a[5]=(a[5]+a[6])&MASK
    a[5]=(a[5]^(a[6]>>4))&MASK; a[0]=(a[0]+a[5])&MASK; a[6]=(a[6]+a[7])&MASK
    a[6]=(a[6]^(a[7]<<8))&MASK; a[1]=(a[1]+a[6])&MASK; a[7]=(a[7]+a[0])&MASK
    a[7]=(a[7]^(a[0]>>9))&MASK; a[2]=(a[2]+a[7])&MASK; a[0]=(a[0]+a[1])&MASK
    return a

class Isaac:
    def __init__(self,seed):
        self.r=[0]*256;self.m=[0]*256
        self.r[:len(seed)]=[x&MASK for x in seed]
        a=[0x9e3779b9]*8
        for _ in range(4): a=mix(a)
        for target in (self.r,self.m):
            for i in range(0,256,8):
                a=mix([(v+target[i+j])&MASK for j,v in enumerate(a)])
                self.m[i:i+8]=a
        self.acc=0;self.last=0;self.counter=0
        self.generate();self.remaining=256
    def generate(self):
        self.counter=(self.counter+1)&MASK
        self.last=(self.last+self.counter)&MASK
        for i in range(256):
            v=self.m[i]
            sh=i&3
            if sh==0:self.acc^=(self.acc<<13)&MASK
            elif sh==1:self.acc^=self.acc>>6
            elif sh==2:self.acc^=(self.acc<<2)&MASK
            else:self.acc^=self.acc>>16
            self.acc=(self.acc+self.m[(i+128)&255])&MASK
            x=self.m[(v&1020)>>2]
            w=(x+self.acc+self.last)&MASK
            self.m[i]=w
            self.last=(self.m[((w>>8)&1020)>>2]+v)&MASK
            self.r[i]=self.last
    def next(self):
        if self.remaining==0:self.generate();self.remaining=256
        self.remaining-=1
        return self.r[self.remaining]
    def encode_opcode(self,opcode):return (opcode+self.next())&255
