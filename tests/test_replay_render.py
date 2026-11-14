"""Exercise the actual native observer sprite blitters at every screen edge."""
import sys,struct,pathlib
if len(sys.argv)>2:sys.path.insert(0,sys.argv[2])
import pefile
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn.x86_const import UC_X86_REG_ESP
pe=pefile.PE(sys.argv[1]);image=pe.get_memory_mapped_image()
W,H=1280,720
for flipped in (False,True):
 for x,y in [(-5,10),(1277,10),(20,-3),(20,718),(-100,-100),(5000,5000),(512,320)]:
  u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(0x400000,0xe00000);u.mem_write(0x400000,image)
  u.mem_map(0x2000000,0x10000);u.mem_map(0x2100000,0x200000);u.mem_map(0x2400000,0x10000)
  def word(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
  frame=0x2101000;word(0x115e308,W);word(0x115f80c,frame)
  for offset,value in [(0x4d0,0),(0x4d4,0),(0x4d8,W-1),(0x4dc,H-1)]:word(0x115e2f8+offset,value)
  word(0x6ca0ec+3064,0x2000000);word(0x6c99b8+3064,0)
  u.mem_write(0x2000000,bytes(range(1,49)));u.mem_write(0x2001000,bytes(range(256)))
  u.mem_write(frame-4096,b'\xa7'*(W*H+8192))
  sp=0x2408000;ret=0x2400100
  u.mem_write(sp,struct.pack('<8I',ret,x&0xffffffff,y&0xffffffff,8,6,1,0,0x2001000));u.reg_write(UC_X86_REG_ESP,sp)
  u.emu_start(0x46a3d0 if flipped else 0x46a330,ret,count=100000)
  assert u.reg_read(UC_X86_REG_ESP)==sp+4
  assert bytes(u.mem_read(frame-4096,4096))==b'\xa7'*4096 and bytes(u.mem_read(frame+W*H,4096))==b'\xa7'*4096,(flipped,x,y,'guard modified')
  actual=bytes(u.mem_read(frame,W*H));expected=bytearray(b'\xa7'*(W*H))
  for row in range(6):
   for col in range(8):
    xx,yy=x+col,y+row
    if 0<=xx<W and 0<=yy<H:expected[yy*W+xx]=row*8+(7-col if flipped else col)+1
  assert actual==expected,(flipped,x,y,'pixels differ')
print('PASS: native normal/mirrored sprite pixels and guards at all four edges, fully outside, and center')
