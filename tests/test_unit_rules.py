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
 return kind,flag,xy,param,struct.unpack('<H',u.mem_read(0xa6ef82,2))[0]
for m in ('portable','svga','hd','wide'):
 image=build(m)
 assert ground(image,0,0,180)==(180,1,30|40<<16,25,0)      # plain building click: immediate, leave placement
 assert ground(image,1,0,180)==(180,0,30|40<<16,25,0)      # Ctrl (native): queued, leave placement
 assert ground(image,0,1,180)==(180,0,30|40<<16,25,180)    # Shift building: queued, stay in placement
 assert ground(image,0,1,3)==(3,0,30|40<<16,25,0)          # Shift move: queued waypoint, mode ends
assert ground(source,0,1,180)==(180,1,30|40<<16,25,0) and ground(source,1,0,180)[1]==0
print('PASS Shift queues construction and keeps placement mode; plain/Ctrl clicks unchanged; original ignored Shift')
