"""Reuse only redundant terrain renders within one simulation tick.
Fog derivation, simulation, sprite/overlay rendering and clipping stay native.
"""
def install(g):
 va=g['va'];state=va+0xb000
 # The selection queue ends below B000; the terrain image begins at 10000.
 # Keys are local render inputs, never serialized gameplay state.
 keys=[('dword ptr [0xa6ea50]',4),('dword ptr [esi+0x4354]',8),
       ('dword ptr [esi+0x4358]',12)]
 keys += [('dword ptr ['+hex(0xca1060+i*4)+']',16+i*4) for i in range(4)]
 keys += [('dword ptr [esi+0x4ccc]',36),('dword ptr [esi+0x8c]',52),
          ('dword ptr [0x115e2f8]',56),('dword ptr [0xcbdc3c]',64),
          ('word ptr [0xb2d85e]',68),('dword ptr [0x4d8934]',72),
          ('dword ptr [0x4d8938]',76),('word ptr [0xced900]',80)]
 def load(source):return ('movzx eax,' if source.startswith('word') else 'mov eax,')+source
 compare=';'.join(load(source)+f';cmp eax,dword ptr [{state+offset}];jne redraw' for source,offset in keys)
 store=';'.join(load(source)+f';mov dword ptr [{state+offset}],eax' for source,offset in keys)
 target=va+g['cursor']
 code=f'''pushfd;pushad;inc dword ptr [{state+40}];
 cmp dword ptr [{state}],1;jne redraw;
 cmp word ptr [esi+0x4c5c],0;jne redraw;
 cmp dword ptr [esp+0x3c],0;jne redraw;
 {compare};
 mov ebx,dword ptr [esi+0x4354];sub ebx,24;jns x_start;xor ebx,ebx;x_start:
 movsx ebp,word ptr [esi+0x8c];mov edx,dword ptr [esi+0x4354];add edx,24;
 cmp ebp,edx;jle x_end;mov ebp,edx;x_end:
 mov eax,dword ptr [esi+0x4358];sub eax,24;jns y_start;xor eax,eax;y_start:
 movsx edi,word ptr [esi+0x8e];mov edx,dword ptr [esi+0x4358];add edx,24;
 cmp edi,edx;jle y_end;mov edi,edx;y_end:
 next_x:cmp ebx,ebp;jge reuse;mov ecx,eax;imul edx,ebx,160;add edx,0xabbca6;
 next_y:cmp ecx,edi;jge advance;cmp byte ptr [edx+ecx],0;jne redraw;inc ecx;jmp next_y;
 advance:inc ebx;jmp next_x;
 reuse:inc dword ptr [{state+48}];
 mov edx,dword ptr [0xb60cf8];sub edx,dword ptr [0x78c2a8];js ready;
 mov eax,dword ptr [0x78c2d4];sub eax,edx;cmp eax,4;jl ready;
 inc dword ptr [{state+84}];push 1;call dword ptr [0x4d0170];
 ready:popad;popfd;jmp 0x480809;
 redraw:inc dword ptr [{state+44}];{store};mov dword ptr [{state}],1;
 popad;popfd;jmp 0x480553'''
 g['hook'](0x47fe99,7,code)
 return dict(gate=target,state=state)
