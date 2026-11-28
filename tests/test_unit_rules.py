"""Execute the real unit-type initializer (00425530) in every resolution recipe.
Usage: python tests/test_unit_rules.py ORIGINAL_EXE
All modes must produce one identical table; watchtower supply (+0x10) is 15.
"""
import sys,json,hashlib,struct,pathlib,pefile
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn.x86_const import UC_X86_REG_ESP
source=pathlib.Path(sys.argv[1]).read_bytes()
assert hashlib.sha256(source).hexdigest()=='1b70b78e8ec040697fced744cbc5f0d2a7ff3477cce35fce3185200f031ceabf'
def build(name):
 r=json.loads(pathlib.Path('compat/'+name+'.json').read_text());b=bytearray(source)
 for e in r['Edits']:
  o=e['Offset'];before=bytes.fromhex(e['Before']);assert b[o:o+len(before)]==before;b[o:o+len(before)]=bytes.fromhex(e['After'])
 b+=bytes.fromhex(r.get('AppendHex',''));assert hashlib.sha256(b).hexdigest()==r['OutputSHA256'];return bytes(b)
def table(image):
 p=pefile.PE(data=image);u=Uc(UC_ARCH_X86,UC_MODE_32)
 u.mem_map(0x400000,(p.OPTIONAL_HEADER.SizeOfImage+0xfff)&~0xfff);u.mem_write(0x400000,p.get_memory_mapped_image())
 u.mem_map(0x200000,0x100000);u.mem_write(0x2f0000,b'\xc3');u.mem_write(0x4afd00,b'\xc3')  # sprite-name diagnostics only
 u.reg_write(UC_X86_REG_ESP,0x2e0000);u.mem_write(0x2e0000,struct.pack('<I',0x2f0000));u.emu_start(0x425530,0x2f0000,count=10000000)
 return bytes(u.mem_read(0xb60d10,200*896))
supply=lambda t,k:struct.unpack_from('<h',t,k*896+0x10)[0]
original=table(source);tables={m:table(build(m)) for m in ('portable','svga','hd','wide')}
assert len(set(tables.values()))==1,'unit rules differ between resolutions'
t=tables['portable']
assert supply(t,42)==15 and supply(t,63)==15 and supply(original,42)==supply(original,63)==5
changed=[k for k in range(200) if t[k*896:(k+1)*896]!=original[k*896:(k+1)*896]];assert changed==[42,63],changed
for m in ('portable','svga','hd','wide'):assert table(build('replay-'+m+'-0.7.1'))==original
print('PASS identical unit table in 640x480/800x600/1024x768/1280x720; only both watchtowers changed (supply 5->15); 0.7.1 replay recipes keep 5')
# Mireuk flame field target test (00458DCD..00458DDD) with real type flags:
# living units and mobile siege/ships call a strike; buildings and empty slots do not.
cases={'무사':0x2005,'궁예':0x22005,'마름쇠차':0x2404005,'포차':0x2044005,'전선':0x2004015,'성채':0x4842,'망루':0x4846,'회의소':0x1c8c2}
want={'무사':1,'궁예':1,'마름쇠차':1,'포차':1,'전선':1,'성채':0,'망루':0,'회의소':0}
def flame(image,flags):
 p=pefile.PE(data=image);u=Uc(UC_ARCH_X86,UC_MODE_32)
 u.mem_map(0x400000,(p.OPTIONAL_HEADER.SizeOfImage+0xfff)&~0xfff);u.mem_write(0x400000,p.get_memory_mapped_image())
 u.mem_map(0x200000,0x100000);from unicorn.x86_const import UC_X86_REG_EDI,UC_X86_REG_EAX
 u.mem_write(0x7ca6e8+77*2308+0x1d8,struct.pack('<I',flags));u.reg_write(UC_X86_REG_EDI,0xabcd0000|77);u.reg_write(UC_X86_REG_ESP,0x2e0000)
 u.emu_start(0x458dcd,0x458ddd,count=200);return u.reg_read(UC_X86_REG_EAX)
for m in ('portable','svga','hd','wide'):
 image=build(m)
 for name,flags in cases.items():assert flame(image,flags)==want[name],(m,name)
for name,flags in cases.items():assert flame(source,flags)==(1 if flags&0x2000 else 0),name
print('PASS Mireuk flame field: living + mobile siege/ships strike in every resolution; buildings unchanged; original accepted living only')
# Shift-queued construction: execute the real ground-command tail (0046EC3A ->
# 0046ED42) with the packet builder stubbed, for each modifier and command.
def ground(image,ctrl,shift,command):
 p=pefile.PE(data=image);u=Uc(UC_ARCH_X86,UC_MODE_32)
 from unicorn import UC_HOOK_CODE
 from unicorn.x86_const import UC_X86_REG_EBX,UC_X86_REG_EDI
 u.mem_map(0x400000,(p.OPTIONAL_HEADER.SizeOfImage+0xfff)&~0xfff);u.mem_write(0x400000,p.get_memory_mapped_image())
 u.mem_map(0x200000,0x100000);u.mem_write(0x435040,b'\xc3')
 put=lambda a,v:u.mem_write(a,struct.pack('<I',v))
 put(0xced908,ctrl);put(0xced910,shift);u.mem_write(0xa6ef82,struct.pack('<H',command))
 # Command 180 builds type 5 (a building, flags bit 2); command 3 moves (type 0).
 u.mem_write(0xb8dd80+180*24+4,struct.pack('<H',5));put(0xb60d5c+5*896,0x4842);put(0xa79504,30);put(0xa79508,40);put(0xa7950c,25)
 u.reg_write(UC_X86_REG_EBX,0);u.reg_write(UC_X86_REG_EDI,1);u.reg_write(UC_X86_REG_ESP,0x2e0000)
 sent=[]
 def h(uc,a,s,d):
  if a==0x435040:
   sp=uc.reg_read(UC_X86_REG_ESP);sent.append(struct.unpack('<6I',uc.mem_read(sp,24)))
 u.hook_add(UC_HOOK_CODE,h,begin=0x435040,end=0x435040)
 u.emu_start(0x46ec3a,0x46ed42,count=500)
 kind,flag,xy,param=sent[0][2]&0xffff,sent[0][5]&0xff,sent[0][3],sent[0][4]
 return kind,flag,xy,param,struct.unpack('<H',u.mem_read(0xa6ef82,2))[0],u.mem_read(0xa6ef80,1)[0]
for m in ('portable','svga','hd','wide'):
 image=build(m)
 assert ground(image,0,0,180)==(180,1,30|40<<16,25,0,0)    # plain building click: immediate, leave placement
 assert ground(image,1,0,180)==(180,0,30|40<<16,25,0,0)    # Ctrl (native): queued, leave placement
 assert ground(image,0,1,180)==(180,0,30|40<<16,25,180,1)  # Shift building: queued, command kept AND waiting for the next click
 assert ground(image,0,1,3)==(3,0,30|40<<16,25,0,0)        # Shift move: queued waypoint, mode ends
assert ground(source,0,1,180)==(180,1,30|40<<16,25,0,0) and ground(source,1,0,180)[1]==0
print('PASS Shift queues construction and keeps placement mode; plain/Ctrl clicks unchanged; original ignored Shift')
# "magic": chat word -> marked native cheat command -> toggle -> mana setter and per-tick refill.
def magic_checks(image,patched):
 from unicorn import UC_HOOK_CODE
 from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_EAX,UC_X86_REG_EIP,UC_X86_REG_ESI,UC_X86_REG_EDI
 p=pefile.PE(data=image);MARK=0x4947414d
 def machine(stub):
  u=Uc(UC_ARCH_X86,UC_MODE_32)
  u.mem_map(0x400000,(p.OPTIONAL_HEADER.SizeOfImage+0xfff)&~0xfff);u.mem_write(0x400000,p.get_memory_mapped_image())
  u.mem_map(0x200000,0x100000);u.mem_write(0x2f0000,b'\xc3')
  if stub:u.mem_write(0x435040,b'\xc3')
  return u
 u=machine(True);sec=p.sections[-1];flag=0x400000+sec.VirtualAddress+0x2620
 sent=[]
 def h(uc,a,s,d):sent.append(struct.unpack('<5I',uc.mem_read(uc.reg_read(UC_X86_REG_ESP)+4,20)))
 u.hook_add(UC_HOOK_CODE,h,begin=0x435040,end=0x435040)
 def call(addr,args=b'',ecx=0,count=20000,u=u):
  u.reg_write(UC_X86_REG_ESP,0x2e0000);u.mem_write(0x2e0000,struct.pack('<I',0x2f0000)+args);u.reg_write(UC_X86_REG_ECX,ecx)
  u.emu_start(addr,0x2f0000,count=count);assert u.reg_read(UC_X86_REG_EIP)==0x2f0000;return u.reg_read(UC_X86_REG_EAX)
 words=((b'magic',1),(b'1_magic',1),(b'MAGIC',1),(b'Magic ',1),(b'  1_Magic  ',1),(b'magi',0),(b'magics',0),(b'1_magi',0),
        (b'magic x',0),(b'amagic',0),(b'1_',0),(b'',0),(b'hello',0),(b'1_goods',0))
 for text,expect in words:
  sent.clear();u.mem_write(0x250000,text+b'\0'+bytes(16));u.mem_write(0xcbdc3c,struct.pack('<I',2));u.mem_write(0x260000,bytes(0x100))
  call(0x41a6a0,struct.pack('<II',0x250000,0),ecx=0x260000)
  assert (sent==[(2,0x15e,MARK,0,1)])==bool(expect and patched),(text,sent)
 # Native words still reach the native parser (1_goods sets its request flag).
 flags=[]
 for text in (b'1_goods',b'1_map',b'1_level'):
  u.mem_write(0x250000,text+b'\0');u.mem_write(0x260000,bytes(0x100));call(0x41a6a0,struct.pack('<II',0x250000,0),ecx=0x260000);flags.append(bytes(u.mem_read(0x260000,0x80)))
 if not patched:return flags
 packet=lambda kind,xy:struct.pack('<HBBII',kind,0,1,xy,0)+bytes(92)
 u.mem_write(0x260000,bytes(0x100))
 hero=0x7ca6e8+33*2308;u.mem_write(hero+0x10c,struct.pack('<i',150));u.mem_write(hero+0xa0,struct.pack('<i',3))
 call(0x41aa00,packet(0x15e,MARK),ecx=0x260000,count=200000);assert u.mem_read(flag,1)[0]==1
 assert struct.unpack('<i',u.mem_read(hero+0xa0,4))[0]==150      # switched on: mana refilled
 assert bytes(u.mem_read(0x260000,0x80))==bytes(0x80)          # native map cheat state untouched
 unit=0x270000;setm=lambda v:u.mem_write(unit+0xa0,struct.pack('<i',v));getm=lambda:struct.unpack('<i',u.mem_read(unit+0xa0,4))[0]
 u.mem_write(unit+0x10c,struct.pack('<i',100));setm(100);call(0x416e10,struct.pack('<i',0),ecx=unit);assert getm()==100
 # Regeneration step (00419632..0041963C): refills while on, leaves mana alone while off; registers as native.
 def regen(v):
  setm(v);u.reg_write(UC_X86_REG_ESI,unit);u.reg_write(UC_X86_REG_ESP,0x2e0000);u.mem_write(0x2e0024,struct.pack('<i',77))
  u.emu_start(0x419632,0x41963c,count=100);assert u.reg_read(UC_X86_REG_ESP)==0x2e0000 and u.reg_read(UC_X86_REG_EAX)==77
  assert u.reg_read(UC_X86_REG_EDI)==getm();return getm()
 assert regen(0)==100 and regen(40)==100 and regen(100)==100
 call(0x41aa00,packet(0x15e,MARK),ecx=0x260000);assert u.mem_read(flag,1)[0]==0      # toggles off
 assert regen(0)==0 and regen(40)==40
 call(0x416e10,struct.pack('<i',0),ecx=unit);assert getm()==0
 call(0x416e10,struct.pack('<i',250),ecx=unit);assert getm()==100;call(0x416e10,struct.pack('<i',-5),ecx=unit);assert getm()==0
 call(0x41aa00,packet(0x15e,MARK),ecx=0x260000);call(0x41a3e0,ecx=0x260000);assert u.mem_read(flag,1)[0]==0  # battle init resets
 # A plain native 0x15E (no marker) is not ours.
 call(0x41aa00,packet(0x15e,0),ecx=0x260000,count=2000000);assert u.mem_read(flag,1)[0]==0
 # End to end with the real command builder, pending queue and dispatcher:
 # chat at tick 100 -> executed by the dispatcher at tick 101 -> Mireuk's 100 mana is not consumed.
 e=machine(False);ecall=lambda *a,**k:call(*a,u=e,**k)
 e.mem_write(0xb8dd80+0x15e*24,struct.pack('<H',2))             # command table: native cheat type (set by game init)
 e.mem_write(0xcbdc3c,struct.pack('<I',2));e.mem_write(0xa6ea50,struct.pack('<I',100));e.mem_write(0x250000,b'magic\0'+bytes(16))
 g=0x7ca6e8+33*2308;e.mem_write(g+0x10c,struct.pack('<i',100));e.mem_write(g+0xa0,struct.pack('<i',0))
 ecall(0x41a6a0,struct.pack('<II',0x250000,0),ecx=0xcbce78,count=200000)
 assert struct.unpack('<H',e.mem_read(0xa6f27c,2))[0]==1 and e.mem_read(flag,1)[0]==0
 ecall(0x4352d0,count=2000000);assert e.mem_read(flag,1)[0]==0   # same tick: queued for the next one
 e.mem_write(0xa6ea50,struct.pack('<I',101));ecall(0x4352d0,count=2000000)
 assert e.mem_read(flag,1)[0]==1 and struct.unpack('<i',e.mem_read(g+0xa0,4))[0]==100
 ecall(0x416e10,struct.pack('<i',0),ecx=g);assert struct.unpack('<i',e.mem_read(g+0xa0,4))[0]==100   # cast: 100-100 stays 100
 e.mem_write(0xa6ea50,struct.pack('<I',102));ecall(0x4352d0,count=2000000);assert e.mem_read(flag,1)[0]==1  # executed once
 return flags
native=magic_checks(source,False)
for m in ('portable','svga','hd','wide'):assert magic_checks(build(m),True)==native and any(any(f) for f in native)
print('PASS magic: magic/1_magic in any case send one marked cheat command; real builder+queue+dispatcher toggle it one tick later in every resolution; setter and regeneration keep mana full; off/reset restore native behaviour; native cheat words unchanged')
# Ground-unit draw pass (00480C93..0048107A): HD modes must traverse the same +/-24 tiles as the terrain,
# otherwise units vanish towards the screen corners. Original resolution keeps the native +/-13.
def unit_pass(image):
 from unicorn import UC_HOOK_CODE
 from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EIP,UC_X86_REG_ESI
 p=pefile.PE(data=image);u=Uc(UC_ARCH_X86,UC_MODE_32)
 u.mem_map(0x400000,(p.OPTIONAL_HEADER.SizeOfImage+0xfff)&~0xfff);u.mem_write(0x400000,p.get_memory_mapped_image())
 u.mem_map(0x200000,0x100000);obj=0x210000;u.mem_write(obj+0x4354,struct.pack('<ii',80,90));u.mem_write(obj+0x8c,struct.pack('<hh',160,160))
 seen=set()
 def h(uc,a,s,d):   # fog query: record the tile and report "hidden" so nothing else runs
  esp=uc.reg_read(UC_X86_REG_ESP);seen.add(struct.unpack('<ii',uc.mem_read(esp+4,8)));uc.reg_write(UC_X86_REG_EAX,1)
  uc.reg_write(UC_X86_REG_ESP,esp+12);uc.reg_write(UC_X86_REG_EIP,struct.unpack('<I',uc.mem_read(esp,4))[0])
 u.hook_add(UC_HOOK_CODE,h,begin=0x42bee0,end=0x42bee0);u.reg_write(UC_X86_REG_ESI,obj);u.reg_write(UC_X86_REG_ESP,0x2e0000)
 u.emu_start(0x480c93,0x48107a,count=5000000);return seen
square=lambda n:{(x,y) for x in range(80-n,80+n) for y in range(90-n,90+n)}
assert unit_pass(source)==square(13) and unit_pass(build('portable'))==square(13)
for m in ('svga','hd','wide'):assert unit_pass(build(m))==square(24),m
print('PASS ground-unit pass covers +/-24 tiles in 800x600/1024x768/1280x720 (was +/-13); 640x480 unchanged')
