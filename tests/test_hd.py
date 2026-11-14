"""Optional original-game x86 tests. python test_hd.py GAME_EXE [MODULE_DIR]."""
import sys,json,pathlib,struct,hashlib
if len(sys.argv)>2:sys.path.insert(0,sys.argv[2])
import pefile
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn.x86_const import *
r=json.loads(pathlib.Path('compat/hd.json').read_text())
s=pathlib.Path(sys.argv[1]).read_bytes();assert hashlib.sha256(s).hexdigest()==r['SourceSHA256']
b=bytearray(s)
for e in r['Edits']:
 o=e['Offset'];old=bytes.fromhex(e['Before']);new=bytes.fromhex(e['After']);assert b[o:o+len(old)]==old;b[o:o+len(old)]=new
b.extend(bytes.fromhex(r['AppendHex']));assert hashlib.sha256(b).hexdigest()==r['OutputSHA256']
p=pefile.PE(data=bytes(b));sec=p.sections[-1];base=p.OPTIONAL_HEADER.ImageBase
assert sec.Name.rstrip(b'\0')==b'.hd'
assert sec.VirtualAddress+sec.Misc_VirtualSize<=p.OPTIONAL_HEADER.SizeOfImage
assert 0x10000+896*768<sec.Misc_VirtualSize
u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(base,p.OPTIONAL_HEADER.SizeOfImage);u.mem_write(base,p.get_memory_mapped_image())
u.mem_map(0x200000,0x10000);u.mem_map(0x2000000,0x100000)
def put(a,*v):u.mem_write(a,struct.pack('<'+'I'*len(v),*v))
def run(a,args=(),ecx=0,stop=0x209ff0):
 sp=0x208000;put(sp,stop,*args);u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,ecx);u.emu_start(a,stop,count=4000000)
 assert u.reg_read(UC_X86_REG_EIP)==stop
 return u.reg_read(UC_X86_REG_ESP)-sp
# Execute the real terrain blitter with a 896-byte source stride and 1024-byte destination pitch.
buf=base+sec.VirtualAddress+0x10000;dest=0x2001000
u.mem_write(buf,b'\x35'*(896*768));u.mem_write(dest-16,b'\xa7'*(1024*768+32))
put(0x115e2f8+12,8,1024,768);put(0x115e2f8+0x1514,dest)
assert run(0x4b0d30,(0,0,896,768,buf),0x115e2f8)==24
out=bytes(u.mem_read(dest,1024*768))
assert all(out[y*1024:y*1024+896]==b'\x35'*896 and out[y*1024+896:(y+1)*1024]==b'\xa7'*128 for y in range(768))
assert bytes(u.mem_read(dest-16,16))==bytes(u.mem_read(dest+1024*768,16))==b'\xa7'*16
print('PASS expanded terrain stride, reserved HUD columns and memory sentinels')
# Real HUD layout with deterministic sprite dimensions, then real button hit test.
for address in [0x469c10,0x469c30]:u.mem_write(address,bytes.fromhex('b820000000c3'))
assert run(0x43ab60,ecx=0xb8d6b0)==4
x,y=struct.unpack('<hh',u.mem_read(0xb8d6b4,4));assert (x,y)==(927,566)
assert struct.unpack('<hh',u.mem_read(0xb8d6e4,4))==(891,291)
print('PASS HUD layout anchors share the translated command/list positions')
assert run(0x49de70,ecx=0x7a2ce8)==4
assert run(0x49de70,ecx=0x7a2ce8)==4
assert struct.unpack('<II',u.mem_read(0x7a2ce8,8))==(851,673)
print('PASS mini-map shared position reset is idempotent')
# Test the background translation trampoline restores the original return path.
put(0xcecc60,480);assert run(0x468140,(900,700),stop=0x468146)==0
assert struct.unpack('<I',u.mem_read(0x208004,4))[0]==516
print('PASS HUD transparency hit test maps display coordinates to source coordinates')
