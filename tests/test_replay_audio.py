"""Validate each replay-only fog bypass leads solely to a sound queue call."""
import sys,re,struct,pathlib
if len(sys.argv)>2:sys.path.insert(0,sys.argv[2])
import pefile,capstone
pe=pefile.PE(sys.argv[1]);md=capstone.Cs(3,4)
source=pathlib.Path('native/replay.cpp').read_text(encoding='utf-8')
sites=[int(x,16) for x in re.search(r'soundVisibilitySites\[\]=\{(.*?)\}',source).group(1).split(',')]
for site in sites:
 initial=list(md.disasm(pe.get_data(site-0x400000,20),site))
 assert initial[0].mnemonic=='call' and initial[0].op_str=='0x42bc80'
 assert initial[1].mnemonic=='test' and initial[1].op_str=='eax, eax' and initial[2].mnemonic=='jne'
 end=int(initial[2].op_str,16);pending=[(initial[2].address+initial[2].size,0,0)];seen=set()
 while pending:
  pc,stack,sounds=pending.pop()
  if (pc,stack,sounds) in seen:continue
  seen.add((pc,stack,sounds));assert len(seen)<80
  if pc==end:assert stack==0 and sounds==1,(hex(site),'invalid audio path');continue
  ins=next(md.disasm(pe.get_data(pc-0x400000,15),pc));op=ins.mnemonic;nxt=pc+ins.size
  assert op in ('mov','movsx','movzx','lea','xor','push','add','cmp','jne','jmp','call'),(hex(site),str(ins))
  if op in ('mov','movsx','movzx','lea','xor'):assert '[' not in ins.op_str.split(',')[0],(hex(site),'memory write')
  if op=='push':stack+=4
  if op=='add':assert ins.op_str=='esp, 0xc';stack-=12
  if op=='call':assert ins.op_str=='0x433560';sounds+=1
  if op=='jmp':pending.append((int(ins.op_str,16),stack,sounds))
  elif op=='jne':pending.extend([(int(ins.op_str,16),stack,sounds),(nxt,stack,sounds)])
  else:pending.append((nxt,stack,sounds))
print('PASS:',len(sites),'audio-only fog branches; no gameplay writes, no other calls, balanced native sound arguments')
