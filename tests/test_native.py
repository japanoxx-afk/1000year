# Run with Python and an installed unicorn module (optional module directory as argv[1]).
import json,sys,struct,pathlib
if len(sys.argv)>1: sys.path.insert(0,sys.argv[1])
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn.x86_const import *
r=json.loads(pathlib.Path('compat/portable.json').read_text(encoding='utf-8-sig'))
for index,va in [(0,0x48c580),(1,0x44fea0)]:
 u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(0x400000,0x100000);u.mem_map(0x200000,0x10000)
 u.mem_write(va,bytes.fromhex(r['Edits'][index]['After']))
 sp=0x208000;ret=0x4ffff0
 u.mem_write(sp,struct.pack('<III',ret,0x201000,0x202000))
 u.reg_write(UC_X86_REG_ESP,sp)
 regs=[UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP]
 for reg in regs:u.reg_write(reg,0x12345678)
 u.emu_start(va,ret,count=100)
 assert u.reg_read(UC_X86_REG_ESP)==sp+4
 assert all(u.reg_read(reg)==0x12345678 for reg in regs)
 if index==0:
  assert u.reg_read(UC_X86_REG_EAX)==1
  assert bytes(u.mem_read(0x201000,4))==b'.\\\0\0'
  assert bytes(u.mem_read(0x202000,4))==b'.\\\0\0'
 else: assert u.reg_read(UC_X86_REG_EAX)==0
 print('PASS x86 patch',hex(va),'outputs, cdecl stack and callee-saved registers')
