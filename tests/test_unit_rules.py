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
