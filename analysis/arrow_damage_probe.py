"""Execute V1.070KR's original damage calculation, without changing game files."""
import sys, struct, json
from pathlib import Path
sys.path.insert(0,sys.argv[2])
import pefile
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn.x86_const import *
source=Path(sys.argv[1]).read_bytes()
patched=len(sys.argv)>3
if patched:
 import hashlib
 r=json.loads(Path(sys.argv[3]).read_text(encoding='utf-8-sig'))
 assert hashlib.sha256(source).hexdigest()==r['SourceSHA256']
 data=bytearray(source)
 for e in r['Edits']:
  o=e['Offset'];old=bytes.fromhex(e['Before']);new=bytes.fromhex(e['After'])
  assert data[o:o+len(old)]==old;data[o:o+len(old)]=new
 data.extend(bytes.fromhex(r.get('AppendHex','')))
 assert hashlib.sha256(data).hexdigest()==r['OutputSHA256']
 source=bytes(data)
p=pefile.PE(data=source);u=Uc(UC_ARCH_X86,UC_MODE_32)
u.mem_map(0x400000,p.OPTIONAL_HEADER.SizeOfImage)
u.mem_write(0x400000,p.get_memory_mapped_image())
u.mem_map(0x200000,0x10000)
def put(a,v):u.mem_write(a,struct.pack('<I',v))
def word(a,v):u.mem_write(a,struct.pack('<H',v))
def run(addr,args=(),ecx=0):
 sp=0x208000;u.mem_write(sp,struct.pack('<'+'I'*(len(args)+1),0x209ff0,*args))
 u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,ecx)
 u.emu_start(addr,0x209ff0,count=100000)
 assert u.reg_read(UC_X86_REG_EIP)==0x209ff0
 return u.reg_read(UC_X86_REG_EAX)
a=0x7ca6e8+2308
word(0xa79620+2,1);put(a+0x9c,10000);put(a+0x108,10000)
u.mem_write(a+0x324,b'\x01');put(a+0x29c,0x10001)
rows=[]
for defence in [0,30,70,90,100]:
 for cls in range(1,7):
  put(a+0x17c,defence);put(a+0x1e8,cls)
  row={'defence':defence,'class':cls}
  for name,kind in [('normal',18),('fire',17),('poison',38)]:
   row[name]=run(0x4010e0,(kind,100,0x10001))&65535
  rows.append(row)
print(json.dumps(rows,indent=2))
for kind in [17,38]:
 put(a+0x9c,10000);put(a+0x17c,30);put(a+0x1e8,1)
 before=bytes(u.mem_read(a,2308))
 result=run(0x401de0,(0,0x10001,0,kind,100))
 after=bytes(u.mem_read(a,2308))
 print('HIT',kind,'HP',struct.unpack_from('<I',after,0x9c)[0],
       'changed offsets',[hex(i) for i in range(2308) if before[i]!=after[i]])
missile=0x620000
for projectile,kind,mult in [(4,17,1),(5,38,2)]:
 u.mem_write(missile,bytes(1072));word(missile+0x26,projectile)
 word(missile+0x8a,100);put(missile+0x86,0x10001)
 put(missile+0x42c,100);put(a+0x9c,10000)
 before=bytes(u.mem_read(a,2308))
 run(0x456b70,ecx=missile)
 after=bytes(u.mem_read(a,2308))
 print('PROJECTILE',projectile,'HP',struct.unpack_from('<I',after,0x9c)[0],
       'changed offsets',[hex(i) for i in range(2308) if before[i]!=after[i]])
 assert struct.unpack_from('<I',after,0x9c)[0]==10000-70*mult
 assert all(before[i]==after[i] for i in range(2308) if not 0x9c<=i<0xa0)
checks=0
for attack in [1,2,3,7,15,20,25,30,33,50,75,100,127,255]:
 for defence in range(101):
  for cls in range(1,7):
   put(a+0x17c,defence);put(a+0x1e8,cls);put(a+0x9c,10000)
   for kind,bonus in [(17,cls in ([3,5,6] if patched else [5,6])),(38,cls in [1,2,4])]:
    scaled=attack*(2 if bonus else 1)
    expected=max(1,scaled-scaled*min(defence,90)//100)
    actual=run(0x4010e0,(kind,attack,0x10001))&65535
    assert actual==expected,(kind,attack,defence,cls,actual,expected)
    checks+=1
print('PASS',checks,'original x86 damage cases; integer rounding, minimum damage and defence cap')
