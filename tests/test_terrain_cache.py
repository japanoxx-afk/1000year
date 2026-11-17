"""Execute the terrain reuse gate, including invalidation and map-edge guards."""
from pathlib import Path
exec(Path('tests/test_hd.py').read_text().split('# Execute the real terrain blitter')[0])
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
cache=r['Features']['terrainCache']['state'];world=0xca5598
put(0x4d0170,0x209100);u.mem_write(0x209100,b'\xc2\x04\x00')
put(world+0x4354,50,50);put(world+0x8c,160|(160<<16));put(world+0x4ccc,0x600000)
put(0xa6ea50,100);put(0x115e2f8,4);put(0xcbdc3c,0);put(0xb2d85e,0)
put(0xca1060,0,0,W-1,H-1);put(0x4d8934,4,2);put(0xced900,0)
u.mem_write(0xabbca6,bytes(160*160));u.mem_write(world+0x4c5c,b'\0\0')
stop=[];bad_writes=[]
def boundary(uc,address,size,data):
 if address in (0x480553,0x480809):stop.append(address);uc.emu_stop()
def write_guard(uc,kind,address,size,value,data):
 if not (0x200000<=address<0x210000 or cache<=address<cache+128):bad_writes.append((address,size))
u.hook_add(UC_HOOK_CODE,boundary);guard=u.hook_add(UC_HOOK_MEM_WRITE,write_guard)
registers=(UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_EDI,UC_X86_REG_EBP,UC_X86_REG_ESI)
def gate(expected,fog=0):
 # Fixture writes are outside emulation and are not observed by write_guard.
 put(0x208018,fog);u.reg_write(UC_X86_REG_ESP,0x208000)
 for i,register in enumerate(registers):u.reg_write(register,world if register==UC_X86_REG_ESI else 0x12340000+i)
 before=[u.reg_read(register) for register in registers];u.reg_write(UC_X86_REG_EFLAGS,0x246);stop.clear()
 u.emu_start(0x47fe99,0x480850,count=100000)
 assert stop==[0x480553 if expected=='draw' else 0x480809],(name,expected,stop)
 assert before==[u.reg_read(register) for register in registers]
 assert u.reg_read(UC_X86_REG_ESP)==0x208000 and u.reg_read(UC_X86_REG_EFLAGS)==0x246
 assert not bad_writes,bad_writes
gate('draw');gate('reuse');gate('reuse')
put(0x78c2d4,50);put(0x78c2a8,1000);put(0xb60cf8,1010);gate('reuse')
assert struct.unpack('<I',u.mem_read(cache+84,4))[0]==1
# Never sleep close to a native tick deadline, or after it has passed.
for now in (1047,1050,1080,990):put(0xb60cf8,now);gate('reuse')
assert struct.unpack('<I',u.mem_read(cache+84,4))[0]==1
# Native tick, camera, surface/view, phase, player, shading and map replacement.
for address,value in ((0xa6ea50,101),(world+0x4354,51),(world+0x4358,52),(0xca1060,1),(0xca1068,W-2),(0x115e2f8,5),(0xb2d85e,1),(0xcbdc3c,1),(0x4d8934,3),(0x4d8938,1),(world+0x4ccc,0x610000)):
 put(address,value);gate('draw');gate('reuse')
gate('draw',fog=1);gate('reuse')
for offset in (0x4c5c,0x4c5d):
 u.mem_write(world+offset,b'\1');gate('draw');u.mem_write(world+offset,b'\0');gate('reuse')
dirty=0xabbca6+51*160+52;u.mem_write(dirty,b'\1');gate('draw');u.mem_write(dirty,b'\0');gate('reuse')
# Far-away dirty cells do not invalidate this view. Edges never scan outside map.
u.mem_write(0xabbca6+159*160+159,b'\1');gate('reuse')
for x,y in ((0,0),(159,159),(0,159),(159,0)):
 u.mem_write(0xabbca6,bytes(160*160));put(world+0x4354,x,y);gate('draw');gate('reuse')
attempts,draws,reuses=struct.unpack('<III',u.mem_read(cache+40,12));assert attempts==draws+reuses and reuses>0
print('PASS',name,': same-tick reuse, tick/camera/fog/terrain/lighting/view invalidation, map edges, registers/flags/stack and simulation-write guards')
