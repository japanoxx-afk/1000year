"""Shared V1.070KR gameplay rules, local selection and HUD helpers.
Gameplay hooks must be installed in every resolution, including portable mode.
"""
def install(g):
 asm,b,raw,va,hook,W=(g[n] for n in ('asm','b','raw','va','hook','W'))
 def emit(code):
  at=va+g['cursor'];blob=asm(at,code);off=raw+g['cursor'];b[off:off+len(blob)]=blob;g['cursor']=(g['cursor']+len(blob)+15)&~15;return at
 # Fire arrow (attack 17): class 3 siege engines/ships share the native
 # double-attack branch already used for classes 5 and 6.
 g['patch'](0x401468,asm(0x401468,'je 0x4013cf'),'fire arrows double against siege engines and ships')
 # The input cursor must offer a rally command before the simulation receiver
 # can process it. Buildings previously offered no ground command at all.
 hook(0x46ccf0,8,'''push edx; push ecx;
 cmp dword ptr [0xa7957c],1; jne native;
 movzx edx,word ptr [0xa79580]; test edx,edx; jz native;
 imul edx,edx,2308; add edx,0x7ca6e8;
 test byte ptr [edx+0x1d8],2; jz native;
 movsx ecx,byte ptr [edx+0x76]; cmp ecx,dword ptr [0xcbdc3c]; jne native;
 mov byte ptr [0xa6ef80],1; mov dword ptr [0x78c2c0],1;
 mov word ptr [0xa6ef82],21; mov word ptr [0xa6ef84],8;
 mov word ptr [0xa6ef86],1; pop ecx; pop edx; mov eax,1; ret;
 native: pop ecx; pop edx; cmp word ptr [0xa6ef82],0; jmp 0x46ccf8''')
 # ESC button objects share their coordinates between drawing and hit testing.
 cx=(W-640)//2;cy=(g['H']-480)//2
 for x,y in [(0x41e497,0x41e492),(0x41e4c1,0x41e4bc),(0x41e4ec,0x41e4e7),(0x41e516,0x41e511),(0x41e540,0x41e53b),(0x41e56b,0x41e566),(0x41e595,0x41e590),(0x41e5bf,0x41e5ba)]:
  import struct
  for addr,delta in [(x,cx),(y,cy)]:
   old=struct.unpack('<I',g['p'].get_data(addr+1-0x400000,4))[0]
   g['d'](addr+1,old+delta,'center ESC button')
 g['d'](0x41e955,150+cx,'center ESC backdrop x')
 g['d'](0x41e950,138+cy,'center ESC backdrop y')
 # Feed ordinary ground orders for buildings through the game's native rally
 # command (21). Native +63C/+63E fields are serialized with the unit and read
 # by the production completion path at 0040E5F1.
 hook(0x464290,8,'''cmp word ptr [esp+4],3; je ground; cmp word ptr [esp+4],8; jne native; ground:
 test byte ptr [ecx+0x1d8],2; jz native;
 mov word ptr [esp+4],21;
 native: cmp word ptr [ecx+0x388],1; jmp 0x464298''')
 # Score valid exits on the rally-facing half-plane before considering the
 # nearest distance. Share this rule across all three native production paths.
 exit_score=emit('''push ebp;
 movsx ebp,di; movsx edx,word ptr [esi+0x2a8]; sub ebp,edx;
 movsx ecx,bx; movsx edx,word ptr [esi+0x2aa]; sub ecx,edx;
 mov eax,ebp; imul eax,eax; imul ecx,ecx; add eax,ecx; shl eax,16;
 cmp word ptr [esi+0x63c],0; jl done; cmp word ptr [esi+0x63e],0; jl done;
 push eax;
 movsx ecx,word ptr [esi+0x63c]; movsx edx,word ptr [esi+0x2a8]; sub ecx,edx;
 movsx eax,bx; movsx edx,word ptr [esi+0x2aa]; sub eax,edx;
 movsx edx,word ptr [esi+0x63e]; movsx edx,dx;
 push ecx; movsx ecx,word ptr [esi+0x2aa]; sub edx,ecx; pop ecx;
 push ecx; push edx; imul ecx,ebp; imul edx,eax; add ecx,edx;
 imul ebp,dword ptr [esp]; imul eax,dword ptr [esp+4]; sub eax,ebp; add esp,8;
 test eax,eax; jns positive; neg eax; positive: add eax,eax;
 mov edx,ecx; test edx,edx; jle outside; cmp eax,edx; jg outside;
 pop eax; jmp facing; outside: pop eax; add eax,0x1000000;
 facing: sub eax,edx;
 done: pop ebp; ret''')
 for start,length,end,initial,final in [(0x465341,38,0x465367,0x4652ad,0x4653a5),(0x4178e5,38,0x41790b,0x41788d,0x417941)]:
  g['d'](initial,0x7fffffff,'exit distance sentinel')
  g['d'](final,0x7fffffff,'exit failure sentinel')
  hook(start,length,f'call {exit_score}; mov ecx,dword ptr [esp+0x14]; jmp {end}')
 g['d'](0x41778d,0x7fffffff,'air exit distance sentinel')
 g['d'](0x417843,0x7fffffff,'air exit failure sentinel')
 hook(0x4177e0,37,f'''push esi; push edi; push ebx;
 mov esi,dword ptr [esp]; mov edi,dword ptr [esp+8]; mov ebx,dword ptr [esp+4];
 call {exit_score}; pop ebx; pop edi; pop esi;
 mov ecx,dword ptr [esp+0x14]; jmp 0x417805''')
 # Production's original rally dispatch: use the native harvest order on a
 # resource tile for workers, otherwise retain the native move order.
 rally=emit('''pushad;
 movzx eax,word ptr [esp+36]; imul eax,eax,2308;
 lea edi,[eax+0x7ca6e8]; movzx eax,byte ptr [edi+0x75];
 cmp eax,4; je worker; cmp eax,7; je worker;
 cmp eax,20; je worker; cmp eax,21; je worker;
 cmp eax,23; je worker; cmp eax,31; jne move;
 worker: movsx eax,word ptr [esp+40]; movsx edx,word ptr [esp+44];
 test eax,eax; js move; test edx,edx; js move;
 cmp ax,word ptr [0xca5624]; jge move;
 cmp dx,word ptr [0xca5626]; jge move;
 mov ecx,dword ptr [0xcaa268]; test ecx,ecx; jz move;
 mov edx,dword ptr [edx*4+0xca98f4]; add edx,eax;
 movzx eax,byte ptr [ecx+edx]; push eax;
 movzx eax,word ptr [edi+0x29c]; push eax;
 call 0x475230; add esp,8; cmp eax,1; jne move;
 popad;
 push 0; push dword ptr [esp+20]; push dword ptr [0xb90224];
 mov eax,dword ptr [esp+24]; shl eax,16;
 movzx edx,word ptr [esp+20]; or eax,edx; push eax;
 push dword ptr [esp+20]; push 8; call 0x4357b0;
 add esp,24; ret;
 move: popad; jmp 0x4358a0''')
 hook(0x40e627,5,f'call {rally}; jmp 0x40e62c')
 # Original-resolution clients need identical simulation/input rules, without
 # importing HD resource layout, selection widgets or a display-mode switch.
 if g.get('rules_only'):return dict(rally=rally,exit_score=exit_score)
 origin=va+0x2400;idle=origin+4;count=origin+8;busy=origin+12;keys=origin+16
 qcount=origin+20;qread=origin+24;qwrite=origin+28;queue=va+0x4000
 fmt=va+0x2500;txt=va+0x2540;group=va+0x2800
 label='쉬는 일꾼 : %d'.encode('cp949')+b'\0';b[raw+0x2500:raw+0x2500+len(label)]=label
 # ESI=index, EDI=unit pointer. Result bitmask: idle worker=1, military=2, hero=4.
 # Types 4/7/20/21/23/31 cover the three factions' workers and ox workers.
 # Destination +2B4 can be zero at spawn or stale after stopping. Current order,
 # pending orders and movement state determine idleness, not destination equality.
 classify=emit('''
 xor eax,eax
 cmp esi,1200
 jae no
 cmp word ptr [esi*2+0xa79620],0
 je no
 cmp dword ptr [edi+0x9c],0
 jle no
 cmp byte ptr [edi+0x324],1
 jne no
 movsx edx,byte ptr [edi+0x76]
 cmp edx,dword ptr [0xcbdc3c]
 jne no
 mov edx,dword ptr [edi+0x1d8]
 test edx,2
 jnz no
 test edx,1
 jz no
 test edx,4
 jnz military
 movzx edx,byte ptr [edi+0x75]
 cmp edx,4
 je worker
 cmp edx,7
 je worker
 cmp edx,20
 je worker
 cmp edx,21
 je worker
 cmp edx,23
 je worker
 cmp edx,31
 jne no
 worker:
 cmp word ptr [edi+0x290],1
 jne no
 cmp word ptr [edi+0x388],1
 jne no
 cmp word ptr [edi+0x3a0],0
 jne no
 cmp word ptr [edi+0x61c],0
 jne no
 cmp byte ptr [edi+0x74],0
 jne no
 mov eax,1
 ret
 military:
 mov eax,2
 test edx,0x20000
 jz no
 or eax,4
 no: ret
 ''')
 # Drop only overflow highlights; the native clear routine handles its 20 slots.
 drop=emit(f'''
 pushad
 cmp dword ptr [{busy}],0
 jne done
 mov ebp,dword ptr [{count}]
 mov dword ptr [{count}],0
 mov esi,20
 next:
 cmp esi,ebp
 jae done
 mov ebx,dword ptr [{group}+esi*4]
 test ebx,ebx
 jz advance
 push ebx
 call 0x467140
 add esp,4
 test eax,eax
 jz advance
 movzx eax,bx
 imul eax,eax,2308
 mov byte ptr [eax+0x7ca6e8],0
 advance: inc esi
 jmp next
 done: popad
 ret
 ''')
 # Preserve original selection API and clear behaviour for manual selection.
 hook(0x467250,10,f'call {drop}; push esi; mov word ptr [0xa6f070],0xffff; jmp 0x46725a')
 hook(0x417a80,7,f'pushfd; cmp dword ptr [ecx+0x9c],0; jle dead; call {drop}; dead: popfd; push ecx; push ebx; push ebp; push esi; or esi,-1; jmp 0x417a87')
 select=emit(f'''
 pushad
 mov ebp,eax
 call 0x467250
 call 0x425120
 mov dword ptr [{busy}],1
 xor ebx,ebx
 mov esi,1
 mov edi,0x7ca6e8+2308
 scan:
 call {classify}
 test eax,ebp
 jz advance
 mov eax,dword ptr [edi+0x29c]
 mov dword ptr [{group}+ebx*4],eax
 cmp ebx,20
 jae overflow
 push 0
 push 1
 push esi
 mov ecx,0x78d024
 call 0x4633f0
 jmp added
 overflow: mov byte ptr [edi],1
 added: inc ebx
 advance:
 inc esi
 add edi,2308
 cmp esi,1200
 jb scan
 mov dword ptr [{count}],ebx
 mov dword ptr [{busy}],0
 popad
 ret
 ''')
 original_enqueue=emit('mov eax,ecx; mov cx,word ptr [eax+0x8d4]; jmp 0x42c499')
 enqueue=emit(f'''
 cmp dword ptr [{qcount}],0
 jne buffer
 cmp word ptr [ecx+0x8d4],5
 jl native
 buffer:
 pushad
 cmp dword ptr [{qcount}],256
 jae done
 mov eax,dword ptr [{qwrite}]
 imul edi,eax,104
 add edi,{queue}
 lea esi,[esp+36]
 mov ecx,26
 cld
 rep movsd dword ptr es:[edi],dword ptr [esi]
 inc eax
 and eax,255
 mov dword ptr [{qwrite}],eax
 inc dword ptr [{qcount}]
 done: popad
 ret 104
 native: jmp {original_enqueue}
 ''')
 hook(0x42c490,9,f'jmp {enqueue}')
 flush=emit(f'''
 pushad
 next:
 cmp dword ptr [{qcount}],0
 je done
 cmp word ptr [0xa6e9a8+0x8d4],5
 jge done
 mov eax,dword ptr [{qread}]
 imul esi,eax,104
 add esi,{queue}
 sub esp,104
 mov edi,esp
 mov ecx,26
 cld
 rep movsd dword ptr es:[edi],dword ptr [esi]
 mov ecx,0xa6e9a8
 call {original_enqueue}
 inc dword ptr [{qread}]
 and dword ptr [{qread}],255
 dec dword ptr [{qcount}]
 jmp next
 done: popad
 ret
 ''')
 refresh=emit(f'''
 pushad
 cmp dword ptr [{count}],0
 je done
 mov edi,0xa79580
 xor eax,eax
 mov ecx,20
 cld
 rep stosd dword ptr es:[edi],eax
 xor esi,esi
 xor ebp,ebp
 scan:
 cmp esi,dword ptr [{count}]
 jae finish
 mov ebx,dword ptr [{group}+esi*4]
 test ebx,ebx
 jz advance
 push ebx
 call 0x467140
 add esp,4
 test eax,eax
 jz invalid
 movzx eax,bx
 imul edi,eax,2308
 add edi,0x7ca6e8
 movsx eax,byte ptr [edi+0x76]
 cmp eax,dword ptr [0xcbdc3c]
 jne unhighlight
 cmp byte ptr [edi+0x324],1
 jne unhighlight
 cmp ebp,20
 jae advance
 mov dword ptr [0xa79580+ebp*4],ebx
 inc ebp
 jmp advance
 unhighlight: mov byte ptr [edi],0
 invalid: mov dword ptr [{group}+esi*4],0
 advance: inc esi
 jmp scan
 finish:
 mov dword ptr [0xa7957c],ebp
 test ebp,ebp
 jnz done
 mov dword ptr [{count}],0
 done: popad
 ret
 ''')
 keyboard=emit(f'''
 pushad
 call {flush}
 call {refresh}
 xor ebx,ebx
 cmp word ptr [0x78c928+0xbe*2],0
 je key2
 or ebx,1
 key2: cmp word ptr [0x78c928+0xc0*2],0
 je key3
 or ebx,2
 key3: cmp word ptr [0x78c928+9*2],0
 je checked
 or ebx,4
 checked:
 mov eax,dword ptr [{keys}]
 mov dword ptr [{keys}],ebx
 not eax
 and eax,ebx
 cmp dword ptr [0xb9022c],0
 jne done
 cmp word ptr [0xced900],0
 jne done
 cmp word ptr [0xced8fc],0
 jne done
 cmp dword ptr [0xced908],0
 jne done
 cmp dword ptr [0xced910],0
 jne done
 cmp dword ptr [0xd375c8],0
 jne done
 test eax,1
 jz army
 mov eax,1
 call {select}
 jmp done
 army: test eax,2
 jz hero
 mov eax,2
 call {select}
 jmp done
 hero: test eax,4
 jz done
 mov eax,4
 call {select}
 done: popad
 ret
 ''')
 hook(0x46dff0,5,f'call {keyboard}; call 0x46d140; jmp 0x46dff5')
 original_command=emit('sub esp,0xb8; jmp 0x435046')
 # Keep the original 20-unit packet format and queue the same command for every batch.
 command=emit(f'''
 cmp dword ptr [esp],0x46ed15
 jne native
 cmp dword ptr [{count}],20
 jbe native
 cmp word ptr [0xa6f000],1
 je native
 pushad
 mov ebp,esp
 sub esp,80
 mov edi,esp
 mov esi,0xa79580
 mov ecx,20
 cld
 rep movsd dword ptr es:[edi],dword ptr [esi]
 xor ebx,ebx
 batch:
 mov edi,0xa79580
 xor eax,eax
 mov ecx,20
 rep stosd dword ptr es:[edi],eax
 mov edi,0xa79580
 xor edx,edx
 fill:
 cmp ebx,dword ptr [{count}]
 jae send
 mov eax,dword ptr [{group}+ebx*4]
 mov dword ptr [edi+edx*4],eax
 inc ebx
 inc edx
 cmp edx,20
 jb fill
 send:
 push dword ptr [ebp+52]
 push dword ptr [ebp+48]
 push dword ptr [ebp+44]
 push dword ptr [ebp+40]
 push dword ptr [ebp+36]
 call {original_command}
 add esp,20
 cmp ebx,dword ptr [{count}]
 jb batch
 mov esi,esp
 mov edi,0xa79580
 mov ecx,20
 rep movsd dword ptr es:[edi],dword ptr [esi]
 add esp,80
 popad
 mov eax,1
 ret
 native: jmp {original_command}
 ''')
 hook(0x435040,6,f'jmp {command}')
 # Right-align resources using exact icon/glyph widths and current digit counts.
 # The full-width background is repainted before units and the HUD on each
 # render cycle. It removes old digits without overwriting terrain or units
 # with the former 512x28 black color-fill rectangle.
 layout=emit(f'''
 pushad
 mov eax,dword ptr [ebp+0x14]
 call digits
 mov ebx,ecx
 mov eax,dword ptr [ebp+0x18]
 call digits
 add ebx,ecx
 movsx eax,word ptr [ebp+0x1b5c]
 add eax,dword ptr [ebp+0x1c]
 call digits
 add ebx,ecx
 movsx eax,word ptr [ebp+0x1b62]
 call digits
 add ebx,ecx
 inc ebx
 push 0x21
 call 0x469c10
 add esp,4
 imul ebx,eax
 push 0x23
 call 0x469c10
 add esp,4
 imul eax,eax,3
 add ebx,eax
 add ebx,20
 mov eax,{W-4}
 sub eax,ebx
 mov dword ptr [{origin}],eax
 popad
 ret
 digits: xor ecx,ecx
 mov esi,10
 test eax,eax
 jns digit
 neg eax
 inc ecx
 digit: inc ecx
 xor edx,edx
 div esi
 test eax,eax
 jne digit
 ret
 ''')
 hook(0x48b87c,6,f'call {layout}; push 0x21; mov dword ptr [esp+0x18],ebp; jmp 0x48b882')
 hook(0x48b896,5,f'push dword ptr [{origin}]; jmp 0x48b89b')
 hook(0x48b8b9,6,f'add esi,dword ptr [{origin}]; jmp 0x48b8bf')
 counter=emit(f'''
 pushad
 xor ebx,ebx
 mov esi,1
 mov edi,0x7ca6e8+2308
 scan: call {classify}
 and eax,1
 add ebx,eax
 inc esi
 add edi,2308
 cmp esi,1200
 jb scan
 mov dword ptr [{idle}],ebx
 push ebx
 push {fmt}
 push {txt}
 call dword ptr [0x4d021c]
 add esp,12
 popad
 ret
 ''')
 # Draw via the same game-selected Korean font, without modifying existing hint state.
 draw=emit(f'''
 pushad
 call {counter}
 sub esp,8
 mov edi,dword ptr [0x65181c]
 lea eax,[esp]
 push eax
 push edi
 mov edx,dword ptr [edi]
 call dword ptr [edx+0x44]
 test eax,eax
 jne finish
 mov ebx,dword ptr [esp]
 push dword ptr [0xcecc30]
 push ebx
 call dword ptr [0x4d0034]
 mov dword ptr [esp+4],eax
 push 0xffffff
 push ebx
 call dword ptr [0x4d0030]
 push 1
 push ebx
 call dword ptr [0x4d0044]
 push {txt}
 call dword ptr [0x4d00d4]
 push eax
 push {txt}
 push 7
 push 6
 push ebx
 call dword ptr [0x4d0028]
 push dword ptr [esp+4]
 push ebx
 call dword ptr [0x4d0034]
 push ebx
 push edi
 mov edx,dword ptr [edi]
 call dword ptr [edx+0x68]
 finish: add esp,8
 popad
 ret
 ''')
 hook(0x46c332,5,f'call 0x4315d0; call {draw}; jmp 0x46c337')
 # Battle initialization discards handles from a previous battle without dereferencing them.
 hook(0x46afd0,5,f'mov dword ptr [{qcount}],0; mov dword ptr [{qread}],0; mov dword ptr [{qwrite}],0; mov dword ptr [{count}],0; mov dword ptr [{busy}],0; mov dword ptr [{keys}],0; pushad; cmp dword ptr [0x115e2f8],4; je ready; call 0x41c9a0; push 4; mov ecx,0x115e2f8; call 0x4af6a0; mov ecx,0x115e2f8; call 0x4b0250; call 0x41c670; ready: popad; mov ecx,0xcbce78; jmp 0x46afd5')
 return dict(rally=rally,classify=classify,select=select,keyboard=keyboard,command=command,original_command=original_command,drop=drop,counter=counter,draw=draw,layout=layout,origin=origin,idle=idle,count=count,busy=busy,keys=keys,group=group,text=txt,enqueue=enqueue,original_enqueue=original_enqueue,flush=flush,qcount=qcount,qread=qread,qwrite=qwrite,queue=queue,refresh=refresh)
