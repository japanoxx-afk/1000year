"""Native 640x480 geometry with the same gameplay rules as HD/wide."""
import argparse, pathlib, hashlib, json, struct
import pefile, keystone
parser=argparse.ArgumentParser()
parser.add_argument('--source',required=True)
parser.add_argument('--output',default='compat/portable.json')
args=parser.parse_args()
source=pathlib.Path(args.source).read_bytes()
assert hashlib.sha256(source).hexdigest()=='1b70b78e8ec040697fced744cbc5f0d2a7ff3477cce35fce3185200f031ceabf'
p=pefile.PE(data=source);b=bytearray(source);edits=[]
def patch(va,after,note):
 off=p.get_offset_from_rva(va-0x400000);before=bytes(b[off:off+len(after)])
 b[off:off+len(after)]=after
 edits.append(dict(Offset=off,Before=before.hex(),After=after.hex(),Note=note))
patch(0x48c580,bytes.fromhex('8b442404c7002e5c00008b442408c7002e5c0000b801000000c3'),'Portable paths')
patch(0x44fea0,bytes.fromhex('31c0c3'),'Skip legacy movies')
ks=keystone.Ks(keystone.KS_ARCH_X86,keystone.KS_MODE_32)
def asm(address,code):return bytes(ks.asm(code,address)[0])
def d(address,value,note):patch(address,struct.pack('<I',value),note)
# Allocate the same independent helper/command storage as internal resolutions.
# Geometry, surface sizes and native 512x480 world viewport stay unchanged.
raw=len(b);rva=(p.OPTIONAL_HEADER.SizeOfImage+4095)&~4095;va=0x400000+rva
hdr=p.sections[-1].get_file_offset()+40
assert hdr+40<=p.OPTIONAL_HEADER.SizeOfHeaders and not any(b[hdr:hdr+40])
b[hdr:hdr+40]=struct.pack('<8sIIIIIIHHI',b'.rules\0\0',0x100000,rva,0x4000,raw,0,0,0,0,0xe0000060)
struct.pack_into('<H',b,p.FILE_HEADER.get_field_absolute_offset('NumberOfSections'),len(p.sections)+1)
struct.pack_into('<I',b,p.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfImage'),rva+0x100000)
b.extend(bytes(0x4000));cursor=0;W,H=640,480;rules_only=True
def hook(address,length,code):
 global cursor
 target=va+cursor;blob=asm(target,code);b[raw+cursor:raw+cursor+len(blob)]=blob;cursor=(cursor+len(blob)+15)&~15
 patch(address,asm(address,'jmp '+hex(target))+b'\x90'*(length-5),'Shared rule/helper trampoline')
from game_features import install
features=install(globals());assert cursor<0x2000
# Preserve named compatibility edits first, then add the changed PE header.
covered=set()
for e in edits:covered.update(range(e['Offset'],e['Offset']+len(bytes.fromhex(e['After']))))
j=0
while j<len(source):
 if j in covered or source[j]==b[j]:j+=1;continue
 start=j
 while j<len(source) and j not in covered and source[j]!=b[j]:j+=1
 edits.append(dict(Offset=start,Before=source[start:j].hex(),After=b[start:j].hex(),Note='Shared rules section header'))
pathlib.Path(args.output).write_text(json.dumps(dict(Features=features,SourceSHA256=hashlib.sha256(source).hexdigest(),OutputSHA256=hashlib.sha256(b).hexdigest(),Edits=edits,AppendHex=b[len(source):].hex()),indent=2))
print('Portable shared rules:',len(edits),'edits; SHA256',hashlib.sha256(b).hexdigest())
