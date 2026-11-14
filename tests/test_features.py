"""Execute actual injected x86 helpers against representative game-state fixtures."""
from pathlib import Path
# Share PE loading and stack helpers, without the unrelated renderer checks.
exec(Path('tests/test_hd.py').read_text().split('# Execute the real terrain blitter')[0])
from unicorn import UC_HOOK_CODE
f=r['Features']
def word(a,v):u.mem_write(a,struct.pack('<H',v))
def unit(i,flags=0x3001,owner=0,order=1,pending=1,hp=240,visible=1,queue=0,moving=0,typeid=7):
 a=0x7ca6e8+i*2308;u.mem_write(a,bytes(2308));word(0xa79620+i*2,typeid)
 u.mem_write(a+0x75,bytes([typeid]))
 u.mem_write(a+0x76,bytes([owner]));put(a+0x9c,hp);put(a+0x1d8,flags)
 u.mem_write(a+0x324,bytes([visible]));word(a+0x290,order);word(a+0x388,pending)
 # Freshly spawned idle workers have an unset destination, observed in the game.
 word(a+0x3a0,queue);u.mem_write(a+0x74,bytes([moving]));put(a+0x2a8,0x100010);put(a+0x2b4,0)
 put(a+0x29c,0x10000+i)
 return a
def classify(i):
 u.reg_write(UC_X86_REG_ESI,i);u.reg_write(UC_X86_REG_EDI,0x7ca6e8+i*2308)
 assert run(f['classify'])==4
 return u.reg_read(UC_X86_REG_EAX)
put(0xcbdc3c,0)
# Execute the native order receiver through the building rally hook.
u.mem_write(0x431250,b'\xc3')
a=unit(1,flags=0x10048c2,typeid=58)
assert run(0x464290,(3,30|(40<<16),0,100,0),ecx=a)==24
assert struct.unpack('<hh',u.mem_read(a+0x63c,4))==(30,40)
a=unit(1)
assert run(0x464290,(3,30|(40<<16),0,100,0),ecx=a)==24
assert struct.unpack('<H',u.mem_read(a+0x388,2))[0]==3
print('PASS native building ground orders set serialized rally coordinates; mobile orders preserved')
# Capture production rally commands with the real map-resource predicate.
saved=bytes(u.mem_read(0x4357b0,1));u.mem_write(0x4357b0,b'\xc3')
issued=[]
def rally_packet(uc,addr,size,data):
 if addr==0x4357b0:
  sp=uc.reg_read(UC_X86_REG_ESP)
  issued.append(struct.unpack('<6I',uc.mem_read(sp+4,24)))
h=u.hook_add(UC_HOOK_CODE,rally_packet)
word(0xca5598+0x8c,160);word(0xca5598+0x8e,160)
word(0xca5598+0x4ce0+(30*160+40)*2,1)
for typeid in [4,7,20,21,23,31]:
 unit(1,typeid=typeid)
 assert run(f['rally'],(0x10001,30,40,1))==4
 assert issued[-1][0:3]==(8,0x10001,30|(40<<16)),issued[-1]
unit(1,flags=0x2005,typeid=2)
assert run(f['rally'],(0x10001,30,40,1))==4
assert issued[-1][0]==3
unit(1)
assert run(f['rally'],(0x10001,31,40,1))==4
assert issued[-1][0]==3
u.hook_del(h);u.mem_write(0x4357b0,saved);u.ctl_remove_cache(0x4357b0,0x4357c0)
print('PASS all six worker types receive harvest on resource tiles; military/ground rallies retain movement')
# Execute the original exit search, including its candidate validation calls.
u.mem_write(0x47c3c0,bytes.fromhex('c22000'))
blocked=set()
def exit_collision(uc,addr,size,data):
 if addr==0x47c3c0:
  sp=uc.reg_read(UC_X86_REG_ESP);x,y=struct.unpack('<II',uc.mem_read(sp+4,8))
  x=x&65535;y=y&65535
  valid=0<=x<160 and 0<=y<160 and (abs(x-50)>=3 or abs(y-50)>=3) and (x,y) not in blocked
  uc.reg_write(UC_X86_REG_EAX,int(valid))
h=u.hook_add(UC_HOOK_CODE,exit_collision)
a=unit(1,flags=0x10048c2,typeid=58);word(a+0x2a8,50);word(a+0x2aa,50)
for target in [(50,0),(50,159),(0,50),(159,50)]:
 word(a+0x63c,target[0]);word(a+0x63e,target[1])
 assert run(0x4652a0,(0x209000,0x209004,1,1,0),ecx=a)==24
 x=struct.unpack('<h',u.mem_read(0x209000,2))[0];y=struct.unpack('<h',u.mem_read(0x209004,2))[0]
 assert (target[1]!=0 or y<50) and (target[1]!=159 or y>50)
 assert (target[0]!=0 or x<50) and (target[0]!=159 or x>50),(target,x,y)
blocked.update((x,y) for x in range(46,55) for y in range(46,55))
assert run(0x4652a0,(0x209000,0x209004,1,1,0),ecx=a)==24
assert u.reg_read(UC_X86_REG_EAX)==0
u.hook_del(h)
print('PASS original spawn search prefers all four rally directions and refuses blocked exits')
for kwargs,want in [({},1),({'order':2},0),({'order':8},0),({'pending':2},0),({'queue':1},0),({'moving':1},0),({'owner':1},0),({'hp':0},0),({'visible':0},0),({'flags':0x1c8c2},0),({'flags':0x2005},2),({'flags':0x22005},6),({'flags':0x2001},1)]:
 unit(1,**kwargs);assert classify(1)==want,(kwargs,classify(1))
print('PASS idle/working/moving/queued/dead/enemy/hidden/building/military/hero classification')
for typeid in [4,7,20,21,23,31]:
 a=unit(1,typeid=typeid);assert classify(1)==1,typeid
 put(a+0x2b4,0x230048);assert classify(1)==1,typeid
 for order in [2,3,8]:
  unit(1,typeid=typeid,order=order);assert classify(1)==0,(typeid,order)
unit(1,typeid=5);assert classify(1)==0
print('PASS all six worker types with unset/stale destinations; active orders excluded')
# No game UI APIs are needed: these are original selection bookkeeping fixtures.
u.mem_write(0x425120,b'\xc3')
u.mem_write(0x467250,b'\xc3')
u.mem_write(0x4633f0,bytes.fromhex('c20c00'))
def native_select(uc,addr,size,data):
 if addr==0x467250:
  uc.mem_write(0xa79580,bytes(80));put(0xa7957c,0)
 elif addr==0x4633f0:
  sp=uc.reg_read(UC_X86_REG_ESP);i=struct.unpack('<I',uc.mem_read(sp+4,4))[0]
  n=struct.unpack('<I',uc.mem_read(0xa7957c,4))[0]
  assert n<20
  put(0xa79580+n*4,0x10000+i);put(0xa7957c,n+1);uc.mem_write(0x7ca6e8+i*2308,b'\x01')
h=u.hook_add(UC_HOOK_CODE,native_select)
for i,typeid in enumerate([4,7,20,21,23,31],1):unit(i,typeid=typeid)
unit(7,typeid=7,order=8);unit(8,typeid=31,owner=1)
u.reg_write(UC_X86_REG_EAX,1);assert run(f['select'])==4
assert struct.unpack('<I',u.mem_read(f['count'],4))[0]==6
assert struct.unpack('<6I',u.mem_read(0xa79580,24))==tuple(0x10000+i for i in range(1,7))
print('PASS idle selection includes all six worker types and excludes working/enemy workers')
for i in range(1,46):unit(i,flags=0x2005)
unit(46,flags=0x22005);unit(47);unit(48,order=8);unit(49,owner=1)
u.reg_write(UC_X86_REG_EAX,2);assert run(f['select'])==4
assert struct.unpack('<I',u.mem_read(f['count'],4))[0]==46
assert all(u.mem_read(0x7ca6e8+i*2308,1)==b'\x01' for i in range(1,47))
assert u.mem_read(0x7ca6e8+47*2308,1)==b'\0'
assert struct.unpack('<I',u.mem_read(0xa7957c,4))[0]==20
u.hook_del(h)
print('PASS all 46 military units highlighted; native 20-slot selection stays in bounds')
# Execute original command building; capture its original 104-byte packets.
u.mem_write(0x42c490,bytes.fromhex('c26800'))
packets=[]
def packet(uc,addr,size,data):
 if addr==0x42c490:
  sp=uc.reg_read(UC_X86_REG_ESP);v=bytes(uc.mem_read(sp+4,104))
  n=struct.unpack_from('<H',v,20)[0]
  packets.append((struct.unpack_from('<H',v,0)[0],n,struct.unpack_from('<'+'I'*n,v,22)))
h=u.hook_add(UC_HOOK_CODE,packet)
backup=bytes(u.mem_read(0xa79580,80))
assert run(0x435040,(2,3,100,200,0),stop=0x46ed15)==4
assert [n for _,n,_ in packets]==[20,20,6],packets
assert [v for _,_,ids in packets for v in ids]==[0x10000+i for i in range(1,47)]
assert bytes(u.mem_read(0xa79580,80))==backup
assert all(cmd==3 for cmd,_,_ in packets)
u.hook_del(h)
print('PASS actual 46-unit command emits 20/20/6 packets and restores native selection')
# A freed/reused handle cannot receive a stale group command.
put(0x7ca6e8+25*2308+0x29c,0x20000+25)
packets=[];h=u.hook_add(UC_HOOK_CODE,packet)
assert run(0x435040,(2,3,100,200,0),stop=0x46ed15)==4
assert sum(n for _,n,_ in packets)==45
u.hook_del(h)
print('PASS stale unit generations excluded from commands')
# Clear overflow highlights without touching the native slots.
assert run(f['drop'])==4
assert struct.unpack('<I',u.mem_read(f['count'],4))[0]==0
assert u.mem_read(0x7ca6e8+21*2308,1)==b'\0'
assert u.mem_read(0x7ca6e8+1*2308,1)==b'\x01'
print('PASS overflow selection cleanup')
# Key edges dispatch exact categories once, including input guards.
u.mem_write(f['select'],b'\xc3');u.ctl_remove_cache(f['select'],f['select']+16)
calls=[]
def keyselect(uc,addr,size,data):
 if addr==f['select']:calls.append(uc.reg_read(UC_X86_REG_EAX))
h=u.hook_add(UC_HOOK_CODE,keyselect)
for vk,mask in [(0xbe,1),(0xc0,2),(9,4)]:
 put(f['keys'],0);word(0x78c928+vk*2,1)
 assert run(f['keyboard'])==4
 assert run(f['keyboard'])==4
 word(0x78c928+vk*2,0);run(f['keyboard'])
assert calls==[1,2,4],calls
for addr in [0xb9022c,0xced900,0xced8fc,0xced908,0xced910,0xd375c8]:
 put(f['keys'],0);put(addr,1);word(0x78c928+9*2,1);run(f['keyboard']);put(addr,0);word(0x78c928+9*2,0)
assert calls==[1,2,4],calls
u.hook_del(h)
print('PASS period/backtick/Tab edges, held-key suppression, chat/pause/modifier guards')
# GDI output uses the exact Korean label and recomputes the idle count each frame.
format_api=0x209400;getdc=0x209500;release=0x209600;gdi_api=0x209700;strlen=0x209800;textout=0x209900
put(0x4d021c,format_api);put(0x4d00d4,strlen);put(0x4d0028,textout)
put(0x4d0034,gdi_api);put(0x4d0030,gdi_api);put(0x4d0044,gdi_api)
surface=0x604000;vtable=0x604100
put(0x65181c,surface);put(surface,vtable);put(vtable+0x44,getdc);put(vtable+0x68,release)
u.mem_write(format_api,b'\xc3');u.mem_write(getdc,bytes.fromhex('31c0c20800'));u.mem_write(release,bytes.fromhex('31c0c20800'))
u.mem_write(gdi_api,bytes.fromhex('b801000000c20800'));u.mem_write(strlen,bytes.fromhex('c20400'));u.mem_write(textout,bytes.fromhex('b801000000c21400'))
drawn=[]
def text_api(uc,addr,size,data):
 sp=uc.reg_read(UC_X86_REG_ESP)
 if addr==format_api:
  dest,fmt,n=struct.unpack('<III',uc.mem_read(sp+4,12))
  label=bytes(uc.mem_read(fmt,40)).split(b'\0')[0].decode('cp949')
  assert label=='쉬는 일꾼 : %d'
  uc.mem_write(dest,(label % n).encode('cp949')+b'\0')
 elif addr==getdc:
  dest=struct.unpack('<I',uc.mem_read(sp+8,4))[0];put(dest,123)
 elif addr==strlen:
  ptr=struct.unpack('<I',uc.mem_read(sp+4,4))[0];uc.reg_write(UC_X86_REG_EAX,len(bytes(uc.mem_read(ptr,40)).split(b'\0')[0]))
 elif addr==textout:
  dc,x,y,ptr,n=struct.unpack('<IIIII',uc.mem_read(sp+4,20))
  drawn.append((dc,x,y,bytes(uc.mem_read(ptr,n)).decode('cp949')))
h=u.hook_add(UC_HOOK_CODE,text_api)
assert run(f['draw'])==4
assert drawn==[(123,6,7,'쉬는 일꾼 : 1')],drawn
unit(48)
assert run(f['draw'])==4
assert drawn[-1][-1]=='쉬는 일꾼 : 2',drawn
u.hook_del(h)
print('PASS Korean idle label, count refresh, GDI position and stack')
# Original queue accepts just five packets. Larger commands must drain over frames.
u.mem_write(0x42c490,p.get_data(0x42c490-base,16));u.ctl_remove_cache(0x42c490,0x42c4d0)
u.mem_write(f['select'],p.get_data(f['select']-base,1));u.ctl_remove_cache(f['select'],f['select']+16)
h=u.hook_add(UC_HOOK_CODE,native_select)
for i in range(1,1200):unit(i,flags=0x2005)
u.reg_write(UC_X86_REG_EAX,2);assert run(f['select'])==4
u.hook_del(h)
assert struct.unpack('<I',u.mem_read(f['count'],4))[0]==1199
word(0xa6e9a8+0x8d4,0)
assert run(0x435040,(0,3,100,200,0),stop=0x46ed15)==4
assert struct.unpack('<H',u.mem_read(0xa6e9a8+0x8d4,2))[0]==5
assert struct.unpack('<I',u.mem_read(f['qcount'],4))[0]==55
all_handles=[]
while True:
 n=struct.unpack('<H',u.mem_read(0xa6e9a8+0x8d4,2))[0]
 for j in range(n):
  pkt=bytes(u.mem_read(0xa6e9a8+0x6cc+j*104,104));k=struct.unpack_from('<H',pkt,20)[0]
  all_handles.extend(struct.unpack_from('<'+'I'*k,pkt,22))
 word(0xa6e9a8+0x8d4,0)
 if struct.unpack('<I',u.mem_read(f['qcount'],4))[0]==0:break
 assert run(f['flush'])==4
assert all_handles==[0x10000+i for i in range(1,1200)]
# Global/system command callers are never duplicated across the mass selection.
assert run(0x435040,(0,0x55,0,0,1))==4
assert struct.unpack('<H',u.mem_read(0xa6e9a8+0x8d4,2))[0]==1
assert struct.unpack('<I',u.mem_read(f['qcount'],4))[0]==0
print('PASS all 1199 units receive ordered packets despite the native five-packet queue; global commands stay single')
# Selection front slots refill after death; converted/hidden units leave the group.
for i in range(1,21):put(0x7ca6e8+i*2308+0x9c,0)
u.mem_write(0x7ca6e8+21*2308+0x76,b'\x01')
u.mem_write(0x7ca6e8+22*2308+0x324,b'\x00')
assert run(f['refresh'])==4
assert struct.unpack('<I',u.mem_read(0xa79580,4))[0]==0x10000+23
assert struct.unpack('<I',u.mem_read(0xa7957c,4))[0]==20
assert u.mem_read(0x7ca6e8+21*2308,1)==b'\0'
assert u.mem_read(0x7ca6e8+22*2308,1)==b'\0'
print('PASS dead/converted/hidden members removed and native selection slots refilled')
