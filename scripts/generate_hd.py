"""Generate the hash-locked V1.070KR HD recipe. Requires pefile, capstone, keystone-engine.
No original game files are distributed. See analysis/RESOLUTION.md for invariants.
"""
import argparse,struct,pathlib,json,hashlib
import pefile,capstone,keystone
parser=argparse.ArgumentParser()
parser.add_argument('--source',required=True)
parser.add_argument('--output',default='compat/hd.json')
parser.add_argument('--exe')
parser.add_argument('--wide',action='store_true',help='1280x720 internal 16:9 mode')
args=parser.parse_args()
W,H=(1280,720) if args.wide else (1024,768)
VW=W-128
DX,DY=W-640,H-480
source=pathlib.Path(args.source).read_bytes()
assert hashlib.sha256(source).hexdigest()=='1b70b78e8ec040697fced744cbc5f0d2a7ff3477cce35fce3185200f031ceabf', 'Unsupported executable'
p=pefile.PE(data=source);b=bytearray(source);edits=[]
def patch(va,after,note):
 off=p.get_offset_from_rva(va-0x400000)
 assert 0<=off<=len(source)-len(after)
 b[off:off+len(after)]=after
 edits.append(dict(VA=hex(va),Note=note,After=after.hex()))
patch(0x48c580,bytes.fromhex('8b442404c7002e5c00008b442408c7002e5c0000b801000000c3'),'Portable relative paths')
patch(0x44fea0,bytes.fromhex('31c0c3'),'Skip legacy movies through existing fallback')
ks=keystone.Ks(keystone.KS_ARCH_X86,keystone.KS_MODE_32)
def asm(va,s):return bytes(ks.asm(s,va)[0])
def d(va,x,n):patch(va,struct.pack('<I',x),n)
# Append an independent virtual allocation, never enlarge the original static buffer.
raw=len(b);rva=(p.OPTIONAL_HEADER.SizeOfImage+4095)&~4095;va=0x400000+rva
hdr=p.sections[-1].get_file_offset()+40
assert hdr+40<=p.OPTIONAL_HEADER.SizeOfHeaders and not any(b[hdr:hdr+40])
b[hdr:hdr+40]=struct.pack('<8sIIIIIIHHI',b'.hd\0\0\0\0\0',0x100000,rva,0x4000,raw,0,0,0,0,0xe0000060)
struct.pack_into('<H',b,p.FILE_HEADER.get_field_absolute_offset('NumberOfSections'),len(p.sections)+1)
struct.pack_into('<I',b,p.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfImage'),rva+0x100000)
b.extend(bytes(0x4000));b[raw+0x2000:raw+0x2400]=bytes([1])*1024
buf=va+0x10000
# Engine and offscreen geometry; the later battle-entry hook preserves menu mode.
d(0x4dec88,4,'custom internal engine mode')
d(0x4aefdc,W,'mode 4 internal width')
d(0x4aefe3,H,'mode 4 internal height')
for a,x in [(0x41c685,H),(0x4aedd3,W),(0x4aedd8,H),(0x47158c,H),(0x471591,W)]:d(a,x,'surface/window dimensions')
for a in [0x46aff7,0x46b02d,0x47f9b7,0x47f9d7]:d(a,H-1,'viewport bottom')
for a in [0x46affc,0x46b019,0x47f9bc,0x47f9c8]:d(a,VW-1,'viewport right')
for a,x in [(0x47f9e9,W),(0x47f9f3,H),(0x47fe3f,H),(0x47fe44,VW),(0x47fe49,buf),(0x47fe82,H-1),(0x47fe87,VW-1),(0x480556,H-1),(0x48055b,VW-1),(0x46bdc0,buf),(0x46bdc5,H),(0x46bdca,VW)]:d(a,x,'expanded terrain cache')
patch(0x47fe99,asm(0x47fe99,'jmp 0x480553'),'full redraw bypasses fixed-size incremental copy')
md=capstone.Cs(3,4);md.detail=True
for a,z in [(0x480588,0x480809),(0x480850,0x480c30)]:
 for i in md.disasm(p.get_data(a-0x400000,z-a),a):
  if i.mnemonic in ['add','sub'] and i.operands[-1].type==2 and i.operands[-1].imm==13:
   off=i.imm_offset;sz=i.imm_size;patch(i.address+off,(24).to_bytes(sz,'little'),'expanded visible tile traversal')
  if i.mnemonic=='lea' and i.operands[-1].type==3 and abs(i.operands[-1].mem.disp)==13:
   val=24 if i.operands[-1].mem.disp>0 else -24
   patch(i.address+i.disp_offset,val.to_bytes(i.disp_size,'little',signed=True),'expanded visible tile traversal')
for a in [0x48204c,0x4824d5,0x482a94,0x482d44,0x482fec]:
 i=next(md.disasm(p.get_data(a-0x400000,15),a));assert i.operands[-1].mem.disp==0x664704
 d(a+i.disp_offset,va+0x2000,'always-dirty read-only tile flags for full redraw')
# HUD shared layout seeds: draw and hit-test share these coordinates.
for a,z in [(0x43ab60,0x43ad38)]:
 for i in md.disasm(p.get_data(a-0x400000,z-a),a):
  if i.mnemonic=='mov' and len(i.operands)==2 and i.operands[0].type==3 and i.operands[1].type==2:
   off=i.operands[0].mem.disp;val=i.operands[1].imm
   if off in [4,0x34,0x46,0x4a,0x50,0x58,0x60]:delta=DX
   elif off in [6,0x36,0x3a,0x44,0x48,0x4c,0x52,0x5a,0x62]:delta=DY
   else:continue
   patch(i.address+i.imm_offset,(val+delta).to_bytes(i.imm_size,'little'),'HUD shared position')
d(0x43ac86,548+DX,'HUD shared x seed')
# Extend HD prototype with correctly anchored background/minimap.
def hook(addr,length,code):
 global cursor
 target=va+cursor;blob=asm(target,code);b[raw+cursor:raw+cursor+len(blob)]=blob;cursor=(cursor+len(blob)+15)&~15
 patch(addr,asm(addr,'jmp '+hex(target))+b'\x90'*(length-5),'HD trampoline')
cursor=0
# Background remains a 640x480 resource. Blit into the lower-right corner, preserving source pitch.
hook(0x46c503,5,'mov eax,640; jmp 0x46c508')
hook(0x46c546,6,f'push {DX}; push edx; call dword ptr [edi+0x1c]; jmp 0x46c54c')
d(0x49de72,467+DX,'minimap shared x')
d(0x49de79,385+DY,'minimap shared y')
# Mini-map is drawn into the original-coordinate background surface before that surface is translated.
hook(0x46c247,5,f'sub dword ptr [0x7a2ce8],{DX}; call 0x46c460; add dword ptr [0x7a2ce8],{DX}; jmp 0x46c24c')
# Transparent HUD-background pixel hit testing maps both display axes back to the original surface.
hook(0x468140,6,f'sub dword ptr [esp+4],{DX}; mov edx,dword ptr [0xcecc60]; jmp 0x468146')
# Retain original menu resolution. Battle initialization switches the renderer and surfaces.
d(0x4dec88,2,'native menu mode')
for a,x in [(0x4aedd3,640),(0x4aedd8,480),(0x47158c,480),(0x471591,640)]:d(a,x,'native menu dimensions')
hook(0x46afd0,5,'pushad; cmp dword ptr [0x115e2f8],4; je ready; call 0x41c9a0; push 4; mov ecx,0x115e2f8; call 0x4af6a0; mov ecx,0x115e2f8; call 0x4b0250; call 0x41c670; ready: popad; mov ecx,0xcbce78; jmp 0x46afd5')
d(0x447a4f,373+DY,'day-night dial y')
d(0x447a54,593+DX,'day-night dial x')
d(0x48b862,H-12,'bottom resource bar y')
hook(0x48b866,6,f'push {DX+6}; push eax; call dword ptr [ecx+0x1c]; jmp 0x48b86c')
d(0x43168e,H-35,'bottom tooltip text y')
# Mini-map camera footprint scales with the world viewport, keeping map projection unchanged.
hook(0x49d702,7,f'imul eax,eax,{VW}; xor edx,edx; mov ecx,512; div ecx; mov word ptr [esi+0x2284c],ax; jmp 0x49d709')
hook(0x49d72c,7,f'imul eax,eax,{H}; xor edx,edx; mov ecx,480; div ecx; mov word ptr [esi+0x2284e],ax; jmp 0x49d733')
# Extend the display-only fog shading caches. These derive visibility from the
# existing simulation map; neither exploration nor unit sight range is changed.
for i in md.disasm(p.get_data(0x47fa10-0x400000,0x47fe3e-0x47fa10),0x47fa10):
 if i.mnemonic in ['add','sub'] and i.operands[-1].type==2 and i.operands[-1].imm==13:
  patch(i.address+i.imm_offset,(24).to_bytes(i.imm_size,'little'),'expanded fog display cache')
 if i.mnemonic=='lea' and i.operands[-1].type==3 and abs(i.operands[-1].mem.disp)==13:
  val=24 if i.operands[-1].mem.disp>0 else -24
  patch(i.address+i.disp_offset,val.to_bytes(i.disp_size,'little',signed=True),'expanded fog display cache')
# The original cleanup intentionally retains the resource-bar surface. Reuse it
# on a mode change rather than overwriting its pointer with an empty surface.
hook(0x41c88d,6,'cmp dword ptr [0x651510],0; jne 0x41c8c2; push 0; push 1; push 12; jmp 0x41c893')
# Resource strip starts at the left edge with a 4px inset; subsequent items stay relative.
d(0x48b897,4,"resource first icon x")
d(0x48b8bb,4,"resource numeric layout origin")
# Bottom hint retains its original left x=50; only screen-bottom anchoring remains.
assert cursor<0x2000
assert 0x10000+VW*H<=0x100000
# Refresh canonical recipe after the final hook.
hunks=[];j=0
while j<len(source):
 if source[j]==b[j]:j+=1;continue
 start=j
 while j<len(source) and source[j]!=b[j]:j+=1
 hunks.append(dict(Offset=start,Before=source[start:j].hex(),After=b[start:j].hex(),Note='Verified HD patch offset '+hex(start)))
recipe=dict(SourceSHA256=hashlib.sha256(source).hexdigest(),OutputSHA256=hashlib.sha256(b).hexdigest(),Edits=hunks,AppendHex=b[len(source):].hex())
pathlib.Path(args.output).write_text(json.dumps(recipe,indent=2))
if args.exe: pathlib.Path(args.exe).write_bytes(b)
print('HD recipe:',len(hunks),'hunks; SHA256',recipe['OutputSHA256'])