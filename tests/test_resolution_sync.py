"""Differential execution of actual native rally/production code across modes.
Usage: python tests/test_resolution_sync.py ORIGINAL_EXE [MODULE_DIR]
The legacy portable recipe is a negative control: it must differ.
"""
import sys,pathlib,json,struct,hashlib
if len(sys.argv)>2:sys.path.insert(0,sys.argv[2])
import pefile
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
source=pathlib.Path(sys.argv[1]).read_bytes()
assert hashlib.sha256(source).hexdigest()=='1b70b78e8ec040697fced744cbc5f0d2a7ff3477cce35fce3185200f031ceabf'
results={}
for mode in ('portable','svga','hd','wide','replay-portable-0.6.11'):
 recipe=json.loads(pathlib.Path('compat/'+mode+'.json').read_text());image=bytearray(source)
 for edit in recipe['Edits']:
  offset=edit['Offset'];before=bytes.fromhex(edit['Before']);after=bytes.fromhex(edit['After'])
  assert image[offset:offset+len(before)]==before;image[offset:offset+len(after)]=after
 image.extend(bytes.fromhex(recipe.get('AppendHex','')))
 assert hashlib.sha256(image).hexdigest()==recipe['OutputSHA256']
 pe=pefile.PE(data=bytes(image));u=Uc(UC_ARCH_X86,UC_MODE_32)
 # Keep the native network verifier and its visible error path intact.
 for start,end in ((0x4882b0,0x488317),(0x485e50,0x485f1d)):
  offset=pe.get_offset_from_rva(start-0x400000);assert bytes(image[offset:offset+end-start])==source[offset:offset+end-start]
 if mode=='portable':
  for start,end in ((0x46afd0,0x46b03d),(0x41c670,0x41c6a0)):
   offset=pe.get_offset_from_rva(start-0x400000);assert bytes(image[offset:offset+end-start])==source[offset:offset+end-start]
 u.mem_map(0x400000,pe.OPTIONAL_HEADER.SizeOfImage);u.mem_write(0x400000,pe.get_memory_mapped_image());u.mem_map(0x200000,0x10000)
 def put(address,*values):u.mem_write(address,struct.pack('<'+'I'*len(values),*values))
 def word(address,value):u.mem_write(address,struct.pack('<h',value))
 def run(address,args,ecx):
  put(0x208000,0x209ff0,*args);u.reg_write(UC_X86_REG_ESP,0x208000);u.reg_write(UC_X86_REG_ECX,ecx)
  u.emu_start(address,0x209ff0,count=4000000);assert u.reg_read(UC_X86_REG_EIP)==0x209ff0
  return u.reg_read(UC_X86_REG_EAX)
 # Collision answers are identical map data for all clients. Execute each
 # client's own candidate enumeration/scoring, including native control flow.
 for address,pop in ((0x47c3c0,32),(0x47c580,32),(0x483730,8),(0x4835b0,8)):
  u.mem_write(address,b'\xc2'+struct.pack('<H',pop))
 def collision(uc,address,size,data):
  if address not in (0x47c3c0,0x47c580,0x483730,0x4835b0):return
  x,y=struct.unpack('<II',uc.mem_read(uc.reg_read(UC_X86_REG_ESP)+4,8));x&=65535;y&=65535
  valid=0<=x<160 and 0<=y<160 and (abs(x-50)>=2 or abs(y-50)>=3)
  uc.reg_write(UC_X86_REG_EAX,1 if address==0x483730 else int(not valid) if address==0x4835b0 else int(valid))
 u.hook_add(UC_HOOK_CODE,collision);u.mem_write(0x431250,b'\xc3')
 building=0x7ca6e8+2308;u.mem_write(building,bytes(2308));word(0xa79622,58)
 u.mem_write(building+0x75,b'\x3a\x00');put(building+0x9c,100);put(building+0x1d8,0x10048c2,0x300)
 put(building+0x29c,0x10001);word(building+0x2a8,50);word(building+0x2aa,50)
 word(building+0x388,1);u.mem_write(building+0x324,b'\x01');word(building+0x63c,-1);word(building+0x63e,-1)
 put(0xcbdc3c,0)
 run(0x464290,(3,30|(40<<16),0,100,0),building)
 rally=struct.unpack('<hh',u.mem_read(building+0x63c,4));births=[]
 for entry,args in ((0x4652a0,(0x209000,0x209004,1,1,0)),(0x417880,(0x209000,0x209004,1,1)),(0x417780,(0x209000,0x209004,1,1))):
  for target in ((50,0),(50,159),(0,50),(159,50)):
   word(building+0x63c,target[0]);word(building+0x63e,target[1])
   assert run(entry,args,building)==1
   births.append((struct.unpack('<h',u.mem_read(0x209000,2))[0],struct.unpack('<h',u.mem_read(0x209004,2))[0]))
 results[mode]=(rally,births)
assert results['portable']==results['svga']==results['hd']==results['wide'],results
assert results['portable']!=results['replay-portable-0.6.11'],results
assert results['portable'][0]==(30,40)
print('PASS: native rally receiver and all three production paths agree across 640x480, 800x600, 1024x768 and 1280x720; legacy mismatch reproduced')
print('Legacy rally:',results['replay-portable-0.6.11'][0],'; fixed:',results['portable'][0])
print('Legacy births:',results['replay-portable-0.6.11'][1][:4],'; fixed:',results['portable'][1][:4])
