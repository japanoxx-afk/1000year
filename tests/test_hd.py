"""Optional original-game x86 tests. python test_hd.py GAME_EXE [MODULE_DIR]."""
import sys,json,pathlib,struct,hashlib
if len(sys.argv)>2:sys.path.insert(0,sys.argv[2])
import pefile
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn.x86_const import *
name=sys.argv[3] if len(sys.argv)>3 else 'hd'
W,H=(1280,720) if name=='wide' else (1024,768)
VW=W-128;DX=W-640;DY=H-480
r=json.loads(pathlib.Path('compat/'+name+'.json').read_text())
s=pathlib.Path(sys.argv[1]).read_bytes();assert hashlib.sha256(s).hexdigest()==r['SourceSHA256']
b=bytearray(s)
for e in r['Edits']:
 o=e['Offset'];old=bytes.fromhex(e['Before']);new=bytes.fromhex(e['After']);assert b[o:o+len(old)]==old;b[o:o+len(old)]=new
b.extend(bytes.fromhex(r['AppendHex']));assert hashlib.sha256(b).hexdigest()==r['OutputSHA256']
p=pefile.PE(data=bytes(b));sec=p.sections[-1];base=p.OPTIONAL_HEADER.ImageBase
assert sec.Name.rstrip(b'\0')==b'.hd'
assert sec.VirtualAddress+sec.Misc_VirtualSize<=p.OPTIONAL_HEADER.SizeOfImage
assert 0x10000+VW*H<sec.Misc_VirtualSize
u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(base,p.OPTIONAL_HEADER.SizeOfImage);u.mem_write(base,p.get_memory_mapped_image())
u.mem_map(0x200000,0x10000);u.mem_map(0x2000000,0x100000)
def put(a,*v):u.mem_write(a,struct.pack('<'+'I'*len(v),*v))
def run(a,args=(),ecx=0,stop=0x209ff0):
 sp=0x208000;put(sp,stop,*args);u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,ecx);u.emu_start(a,stop,count=4000000)
 assert u.reg_read(UC_X86_REG_EIP)==stop
 return u.reg_read(UC_X86_REG_ESP)-sp
# Execute the real terrain blitter with a expanded source stride and full-screen destination pitch.
buf=base+sec.VirtualAddress+0x10000;dest=0x2001000
u.mem_write(buf,b'\x35'*(VW*H));u.mem_write(dest-16,b'\xa7'*(W*H+32))
put(0x115e2f8+12,8,W,H);put(0x115e2f8+0x1514,dest)
assert run(0x4b0d30,(0,0,VW,H,buf),0x115e2f8)==24
out=bytes(u.mem_read(dest,W*H))
assert all(out[y*W:y*W+VW]==b'\x35'*VW and out[y*W+VW:(y+1)*W]==b'\xa7'*128 for y in range(H))
assert bytes(u.mem_read(dest-16,16))==bytes(u.mem_read(dest+W*H,16))==b'\xa7'*16
print('PASS expanded terrain stride, reserved HUD columns and memory sentinels')
# Real HUD layout with deterministic sprite dimensions, then real button hit test.
for address in [0x469c10,0x469c30]:u.mem_write(address,bytes.fromhex('b820000000c3'))
assert run(0x43ab60,ecx=0xb8d6b0)==4
x,y=struct.unpack('<hh',u.mem_read(0xb8d6b4,4));assert (x,y)==(543+DX,278+DY)
assert struct.unpack('<hh',u.mem_read(0xb8d6e4,4))==(507+DX,3+DY)
print('PASS HUD layout anchors share the translated command/list positions')
assert run(0x49de70,ecx=0x7a2ce8)==4
assert run(0x49de70,ecx=0x7a2ce8)==4
assert struct.unpack('<II',u.mem_read(0x7a2ce8,8))==(467+DX,385+DY)
print('PASS mini-map shared position reset is idempotent')
# Test the background translation trampoline restores the original return path.
put(0xcecc60,480);assert run(0x468140,(900,700),stop=0x468146)==0
assert struct.unpack('<I',u.mem_read(0x208004,4))[0]==900-DX
assert struct.unpack('<I',u.mem_read(0x208008,4))[0]==700
print('PASS HUD transparency hit test maps display coordinates to source coordinates')

# The complete resource renderer is byte-for-byte identical to the original.
assert p.get_data(0x48b870-base,0x269)==pefile.PE(data=s).get_data(0x48b870-base,0x269)
print('PASS original resource icon and numeric layout restored')

# Exercise the real minimap projection using its new shared screen origin.
mx,my=467+DX,385+DY
u.mem_write(0x7a2ce8+0xfc3c+2*(40*160+80),bytes([37,61]))
assert run(0x49d900,(mx+80,my+40,0x601000,0x601004),0x7a2ce8)==20
assert u.reg_read(UC_X86_REG_EAX)==1
assert struct.unpack('<H',u.mem_read(0x601000,2))[0]==37
assert struct.unpack('<H',u.mem_read(0x601004,2))[0]==61
assert run(0x49d900,(mx+80,my+40-(H-480)//2,0x601000,0x601004),0x7a2ce8)==20
assert u.reg_read(UC_X86_REG_EAX)==0
print('PASS relocated minimap click projects correctly; previous centered location is rejected')

# Stub GDI measurement and capture TextOut arguments while executing the hint hook.
from unicorn import UC_HOOK_CODE
measure=0x209000;textout=0x209100
put(0x4d0040,measure);put(0x4d0028,textout)
u.mem_write(measure,bytes.fromhex('b801000000c21000'))
u.mem_write(textout,bytes.fromhex('b801000000c21400'))
seen=[]
def gdi(uc,address,size,data):
 sp=uc.reg_read(UC_X86_REG_ESP)
 if address==measure:
  hdc,text,length,extent=struct.unpack('<IIII',uc.mem_read(sp+4,16))
  assert (hdc,text,length)==(123,0x601000,4)
  put(extent,42,16)
 elif address==textout:
  seen.append(struct.unpack('<IIIII',uc.mem_read(sp+4,20)))
hook=u.hook_add(UC_HOOK_CODE,gdi)
u.reg_write(UC_X86_REG_ESI,0x601000);u.reg_write(UC_X86_REG_EAX,4)
assert run(0x431687,(0,0,123),stop=0x43169b)==0
assert seen==[(123,50,H-35,0x601000,4)],seen
u.hook_del(hook)
print('PASS original left-aligned hint and GDI call stack:',name)
