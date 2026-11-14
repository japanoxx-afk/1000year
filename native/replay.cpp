// Hash-locked Millennium Myth 1.070KR command replay adapter.
// Addresses were inspected in this executable; no addresses from reference games.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#define _CRT_SECURE_NO_WARNINGS
#include <windows.h>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
#include <string>

namespace {
template<class T> T& mem(uintptr_t p) {return *reinterpret_cast<T*>(p);}
struct State {uint32_t tick,seed,units,hash;};
struct Packet {uint8_t bytes[104];};
struct Command {uint32_t player; Packet packet;};
struct Frame {State before,after; uint32_t result,count;};
static_assert(sizeof(Frame)==40,"wire format");
std::wstring root;
bool playback=false,active=false,failed=false,privateSave=false,inside=false;
bool completed=false;
bool dispatchEntered=false;
FILE* output=nullptr;
std::vector<Command> commands;
std::vector<uint8_t> input;
struct CodeEdit {uintptr_t where;std::vector<uint8_t> before;};
std::vector<CodeEdit> edits;
size_t cursor=8;
Frame frame{};
void* advance=nullptr;
uint32_t dispatchResult=1;
uint32_t frames=0;
DWORD lastControl=0;
bool paused=false,stepping=false;
uint32_t speedKeys=0;
uint32_t tickMilliseconds=60,speed=150; // percent: 150 means 1.5x
void setSpeedKeys(uint32_t down){uint32_t pressed=down&~speedKeys;speedKeys=down;if(pressed&1)speed=150;if(pressed&2)speed=200;if(pressed&4)speed=400;}
int64_t playbackClock=0,clockFrequency=0;
int64_t counterNow(){LARGE_INTEGER value;QueryPerformanceCounter(&value);return value.QuadPart;}
int64_t framePeriod(){return clockFrequency*tickMilliseconds*100/(1000*speed);}
char checkpoint[MAX_PATH]{};
WNDPROC previousWindowProc=nullptr;
void writeSpeed(){FILE* f=_wfopen((root+L"\\control.txt").c_str(),L"wb");if(f){if(speed==150)fputs("speed1.5",f);else fprintf(f,"speed%u",speed/100);fclose(f);}}
LRESULT CALLBACK replayWindowProc(HWND window,UINT message,WPARAM key,LPARAM data){
 if(playback&&!mem<uint32_t>(0xb9022c)&&(message==WM_KEYDOWN||message==WM_KEYUP)){
  unsigned value=key=='1'||key==VK_NUMPAD1?1:key=='2'||key==VK_NUMPAD2?2:key=='4'||key==VK_NUMPAD4?4:0;
  if(value){if(message==WM_KEYDOWN){speed=value==1?150:value*100;writeSpeed();}return 0;}
 }
 return CallWindowProcA(previousWindowProc,window,message,key,data);
}
void status(const char* message) {
 std::wstring path=root+L"\\status.txt";
 HANDLE f=CreateFileW(path.c_str(),GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE,nullptr,CREATE_ALWAYS,0,nullptr);
 if(f!=INVALID_HANDLE_VALUE){DWORD n;WriteFile(f,message,(DWORD)strlen(message),&n,nullptr);CloseHandle(f);}
}
void fail(const char* message){failed=true;status(message);}
uint32_t hashBytes(uint32_t h,const void* data,size_t size){auto p=(const uint8_t*)data;while(size--){h^=*p++;h*=16777619;}return h;}
State snapshot(){
 State s{mem<uint32_t>(0xa6ea50),mem<uint32_t>(0xa6ea5c),0,2166136261u};
 for(uint32_t id=1;id<1200;++id){
  auto type=mem<uint16_t>(0xa79620+id*2);if(!type)continue;
  uintptr_t u=0x7ca6e8+id*2308;
  s.units++;s.hash=hashBytes(s.hash,&id,4);s.hash=hashBytes(s.hash,&type,2);
  for(auto span: {std::pair<uint32_t,uint32_t>{0x75,2},{0x9c,4},{0x290,4},{0x29c,4},{0x2a8,4},{0x388,12},{0x63c,4}})
   s.hash=hashBytes(s.hash,(void*)(u+span.first),span.second);
 }
 for(unsigned player=0;player<8;++player){
  uintptr_t p=0xb137bc+player*0x33d4;
  s.hash=hashBytes(s.hash,(void*)(p+0x14),12);
  s.hash=hashBytes(s.hash,(void*)(p+0x1b5c),8);
 }
 return s;
}
bool equal(const State&a,const State&b){return !memcmp(&a,&b,sizeof(a));}
// Reveal only while deriving or drawing observer visuals. Restore the original
// simulation visibility planes before any command/AI update or state check.
uint8_t savedVisibility[8*0x6400];unsigned revealDepth=0;
int16_t savedDayPhase=0;
struct ObserverView {
 bool enabled;
 ObserverView():enabled(playback&&(active||completed)&&!failed){if(enabled&&revealDepth++==0){
  memcpy(savedVisibility,(void*)0xa7d4a6,sizeof(savedVisibility));memset((void*)0xa7d4a6,0,sizeof(savedVisibility));
  // Phase zero is the daylight render variant. Tile buffers CAA234/CAA238
  // contain terrain data, not observer visibility, and must remain untouched.
  savedDayPhase=mem<int16_t>(0xb2d85e);mem<int16_t>(0xb2d85e)=0;
 }}
 ~ObserverView(){if(enabled&&--revealDepth==0){memcpy((void*)0xa7d4a6,savedVisibility,sizeof(savedVisibility));mem<int16_t>(0xb2d85e)=savedDayPhase;}}
};
struct PlayerResources {unsigned slot;int rice,wood,population,limit;wchar_t name[32];};
std::vector<PlayerResources> playerResources(){
 std::vector<PlayerResources> rows;
 for(unsigned i=0;i<8;++i){uintptr_t p=0xb137bc+i*0x33d4;unsigned nation=mem<uint8_t>(p);if(!nation||nation==6)continue;
  PlayerResources r{i,mem<int32_t>(p+0x14),mem<int32_t>(p+0x18),mem<int16_t>(p+0x1b5c)+mem<int32_t>(p+0x1c),mem<int16_t>(p+0x1b62),{}};
  char name[16]{};memcpy(name,(void*)(0x7a0d38+i*15),15);
  MultiByteToWideChar(949,0,name,-1,r.name,32);rows.push_back(r);
 }return rows;
}
void drawResources(){
 if(!playback||(!active&&!completed)||failed)return;
 void* surface=mem<void*>(0x65181c);if(!surface)return;
 auto table=*(void***)surface;HDC dc=nullptr;
 auto getDC=(HRESULT(WINAPI*)(void*,HDC*))table[17];auto releaseDC=(HRESULT(WINAPI*)(void*,HDC))table[26];
 if(FAILED(getDC(surface,&dc))||!dc)return;
 int saved=SaveDC(dc);SelectClipRgn(dc,nullptr);SetMapMode(dc,MM_TEXT);SetViewportOrgEx(dc,0,0,nullptr);SetWindowOrgEx(dc,0,0,nullptr);SetBkMode(dc,TRANSPARENT);
 HFONT font=mem<HFONT>(0xcecc30);if(font)SelectObject(dc,font);
 int width=mem<int32_t>(0x115e308),left=width-430;if(left<4)left=4;
 // Legacy replays reserve 128 columns which the background never repaints.
 // Clear only that non-terrain strip before drawing changing-width numbers.
 int terrainWidth=mem<int32_t>(0x46bdca);if(terrainWidth>0&&terrainWidth<width){RECT unused{terrainWidth,32,width,180};FillRect(dc,&unused,(HBRUSH)GetStockObject(BLACK_BRUSH));}
 auto text=[&](int x,int y,const wchar_t* value){int n=(int)wcslen(value);SetTextColor(dc,RGB(0,0,0));TextOutW(dc,x+1,y+1,value,n);SetTextColor(dc,RGB(255,255,255));TextOutW(dc,x,y,value,n);};
 text(left,34,L"플레이어");text(left+150,34,L"쌀");text(left+235,34,L"나무");text(left+320,34,L"전비");
 int y=50;for(const auto& r:playerResources()){
  wchar_t label[64],value[64];swprintf_s(label,L"P%u %s",r.slot+1,r.name);text(left,y,label);
  swprintf_s(value,L"%d",r.rice);text(left+150,y,value);swprintf_s(value,L"%d",r.wood);text(left+235,y,value);
  swprintf_s(value,L"%d/%d",r.population,r.limit);text(left+320,y,value);y+=16;
 }
 if(saved)RestoreDC(dc,saved);releaseDC(surface,dc);
}
uint32_t __fastcall observerFog(void* self,void*){ObserverView view;return ((uint32_t(__thiscall*)(void*))0x47fa10)(self);}
uint32_t __cdecl observerBackground(){ObserverView view;return ((uint32_t(__cdecl*)())0x46bda0)();}
uint32_t __cdecl observerUnits(){ObserverView view;return ((uint32_t(__cdecl*)())0x46be00)();}
uint32_t __cdecl observerSelection(){ObserverView view;return ((uint32_t(__cdecl*)())0x46bea0)();}
uint32_t __cdecl observerHud(){ObserverView view;drawResources();return ((uint32_t(__cdecl*)())0x46c380)();}
bool write(const void* p,size_t n){if(failed)return false;if(!output||ftell(output)<0||ftell(output)+n>128u*1024*1024||fwrite(p,1,n,output)!=n){fail("ERROR: replay write failed or size limit reached");return false;}return true;}
bool read(void* p,size_t n){if(cursor>input.size()||n>input.size()-cursor){fail("ERROR: truncated replay");return false;}memcpy(p,input.data()+cursor,n);cursor+=n;return true;}
void finish(){
 if(output){uint32_t end=0xffffffff;write(&end,4);fflush(output);fclose(output);output=nullptr;}
 active=false;
 completed=true;
 if(!failed)status("COMPLETE");
}
int __cdecl savePath(int /*slot*/,char* path){
 if(privateSave){strcpy_s(path,MAX_PATH,checkpoint);return 1;}
 // The original routine is only bypassed during our own save/load operation.
 return 0;
}
uintptr_t pathContinue=0x48d175;
__declspec(naked) void pathHook(){__asm {
 cmp byte ptr [privateSave],0
 je original
 mov eax,[esp+8]
 push eax
 mov eax,[esp+8]
 push eax
 call savePath
 add esp,8
 ret
 original:
 movsx eax,word ptr [esp+4]
 jmp [pathContinue]
}}
bool checkpointOperation(bool load){
 privateSave=true;
 int result=((int(__cdecl*)(int))(load?0x48d6f0:0x48d330))(0);
 privateSave=false;
 return result==1;
}
void begin(){
 if(active||failed)return;
 if(playback){
  // Start a local battle first so native resources and DirectDraw surfaces exist.
  // The native full loader restores the recorded map, player slots and objects.
  if(!checkpointOperation(true)){fail("ERROR: initial save restore failed");return;}
 }else{
  // Saving emits a UI notification packet. Preserve the queue around that call.
  uint8_t queue[0x34c];memcpy(queue,(void*)(0xa6e9a8+0x6cc),sizeof(queue));
  State before=snapshot();
  bool ok=checkpointOperation(false);
  memcpy((void*)(0xa6e9a8+0x6cc),queue,sizeof(queue));
  if(!ok||!equal(before,snapshot())){fail("ERROR: initial save changed simulation state");return;}
  std::wstring path=root+L"\\commands.partial";
  output=_wfopen(path.c_str(),L"wb");if(!output){fail("ERROR: cannot create recording");return;}
  setvbuf(output,nullptr,_IOFBF,1024*1024);
  write("MYTHRP01",8);
 }
 active=true;status(playback?"PLAYING":"RECORDING");
 if(playback){FILE* f=_wfopen((root+L"\\timing.txt").c_str(),L"rb");if(f){unsigned n=0;if(fscanf(f,"%u",&n)==1&&n>=10&&n<=1000)tickMilliseconds=n;fclose(f);}}
 else {
  tickMilliseconds=((uint32_t(__cdecl*)())0x466960)();
  FILE* f=_wfopen((root+L"\\timing.txt").c_str(),L"wb");if(f){fprintf(f,"%u",tickMilliseconds);fclose(f);}
 }
 LARGE_INTEGER frequency;QueryPerformanceFrequency(&frequency);clockFrequency=frequency.QuadPart;playbackClock=counterNow();
}
void __cdecl capture(const Packet* packet,uint32_t player){
 if(!inside||failed||playback)return;
 if(player>=8||commands.size()>=400){fail("ERROR: invalid command batch");return;}
 Command c{player,*packet};commands.push_back(c);
}
uintptr_t packetContinue=0x4353a7;
__declspec(naked) void packetHook(){__asm {
 pushfd
 pushad
 mov eax,[esp+36+0x18]
 push eax
 push ebp
 call capture
 add esp,8
 popad
 popfd
 movsx ecx,ax
 lea ecx,[ecx+ecx*2]
 jmp [packetContinue]
}}
void __cdecl prepareCommands(){
 dispatchEntered=true;
#ifdef MYTH_REPLAY_TEST
 // Test build only: exercise the real consumed-command path for every slot.
 static bool fixtureSent=false;
 if(!playback&&inside&&!fixtureSent&&mem<uint32_t>(0xa6ea50)>=10){
  fixtureSent=true;
  for(unsigned player=0;player<8;++player){
   auto p=(Packet*)(0xa6f280+player*50*104);memset(p,0,sizeof(*p));
   mem<uint16_t>((uintptr_t)p)=65;mem<uint16_t>((uintptr_t)p+12)=(uint16_t)player;
   mem<uint32_t>((uintptr_t)p+16)=mem<uint32_t>(0xa6ea50)-1;
  }
 }
#endif
 if(!playback||!inside||failed)return;
 // Playback is offline: replace all eight player queues, including remote slots.
 memset((void*)0xa6f280,0,8*50*104);
 unsigned used[8]{};
 for(auto& c:commands){
  uint16_t kind=mem<uint16_t>((uintptr_t)c.packet.bytes),count=mem<uint16_t>((uintptr_t)c.packet.bytes+20);
  if(c.player>=8||used[c.player]>=50||kind<1||kind>363||count>20){fail("ERROR: invalid player queue");return;}
  for(unsigned i=0;i<count;++i){auto id=mem<uint16_t>((uintptr_t)c.packet.bytes+22+4*i);if(id<1||id>1199){fail("ERROR: invalid unit handle");return;}}
  auto target=(Packet*)(0xa6f280+(c.player*50+used[c.player]++)*104);
  *target=c.packet;
  // Offline native dispatch uses a one-tick latency instead of network latency.
  memcpy(target->bytes+16,&frame.before.tick,4);
  mem<uint32_t>((uintptr_t)target+16)--;
 }
}
uintptr_t queueContinue=0x43535d;
__declspec(naked) void queueHook(){__asm {
 pushfd
 pushad
 call prepareCommands
 popad
 popfd
 xor edi,edi
 mov esi,0xb1656e
 jmp [queueContinue]
}}
uint32_t __cdecl dispatch(){
 uint32_t result=((uint32_t(__cdecl*)())0x4352d0)();
 if(playback&&inside)return dispatchResult;
 dispatchResult=result;return result;
}
uint32_t __cdecl timerGate(){
 uint32_t result=((uint32_t(__cdecl*)())0x46c7a0)();
 // Wall-clock latency is not part of deterministic simulation. Reproduce the
 // recorded gate outcome, including command-only attempts without a tick.
 return playback&&inside?(frame.after.tick>frame.before.tick?1:0):result;
}
void __cdecl disableLiveCommands(){ }
bool pauseRequested(){
 DWORD foregroundPid=0;GetWindowThreadProcessId(GetForegroundWindow(),&foregroundPid);
 uint32_t down=0;
 if(foregroundPid==GetCurrentProcessId()&&!mem<uint32_t>(0xb9022c)){
  if((GetAsyncKeyState('1')|GetAsyncKeyState(VK_NUMPAD1))&0x8000)down|=1;
  if((GetAsyncKeyState('2')|GetAsyncKeyState(VK_NUMPAD2))&0x8000)down|=2;
  if((GetAsyncKeyState('4')|GetAsyncKeyState(VK_NUMPAD4))&0x8000)down|=4;
 }
 uint32_t previous=speed;setSpeedKeys(down);
 if(speed!=previous)writeSpeed();
 if(GetTickCount()-lastControl>=100){
  lastControl=GetTickCount();
  FILE* f=_wfopen((root+L"\\control.txt").c_str(),L"rb");
  if(f){char text[16]{};fread(text,1,15,f);fclose(f);
   if(!strcmp(text,"pause"))paused=true;
   if(!strcmp(text,"play"))paused=false;
   if(!strcmp(text,"speed1")||!strcmp(text,"speed1.5"))speed=150;
   if(!strcmp(text,"speed2"))speed=200;
   if(!strcmp(text,"speed4"))speed=400;
   if(!strcmp(text,"step")){paused=false;stepping=true;FILE* w=_wfopen((root+L"\\control.txt").c_str(),L"wb");if(w){fwrite("pause",1,5,w);fclose(w);}}
  }
 }
 return paused;
}
uint32_t __cdecl advanceHook(){
 if(completed)return playback?0:((uint32_t(__cdecl*)())advance)();
 if(failed)return playback?0:((uint32_t(__cdecl*)())advance)();
 if(playback&&pauseRequested()){playbackClock=counterNow();return 0;}
 if(!active)begin();
 if(failed)return playback?0:((uint32_t(__cdecl*)())advance)();
 if(!playback&&frames&&mem<uint32_t>(0xa6ea50)<frame.after.tick){finish();return ((uint32_t(__cdecl*)())advance)();}
 commands.clear();size_t frameStart=cursor;
 if(playback){
  uint32_t tag=0;if(!read(&tag,4))return 0;
  if(tag==0xffffffff){finish();completed=true;return 0;}
  if(tag!=1||!read(&frame,sizeof(frame))||frame.count>400){fail("ERROR: invalid replay frame");return 0;}
  commands.resize(frame.count);
  if(!read(commands.data(),commands.size()*sizeof(Command)))return 0;
  if(!equal(snapshot(),frame.before)){fail("ERROR: replay state mismatch before frame");return 0;}
  dispatchResult=frame.result;
  if(frame.after.tick>frame.before.tick&&!stepping&&counterNow()-playbackClock<framePeriod()){cursor=frameStart;return 0;}
 }else {frame={};frame.before=snapshot();dispatchResult=1;}
 inside=true;dispatchEntered=false;
 uint32_t result=((uint32_t(__cdecl*)())advance)();
 inside=false;
 State after=snapshot();
 if(playback){
  // The native input/timer gate can return before simulation starts. Such calls
  // are not frames and must not consume the next recorded simulation frame.
  if(!dispatchEntered&&equal(after,frame.before)&&!equal(frame.before,frame.after)){cursor=frameStart;return result;}
  if(!equal(after,frame.after)){
   char detail[256];sprintf_s(detail,"ERROR: frame %u expected %u/%u/%u/%08x actual %u/%u/%u/%08x",frames,frame.after.tick,frame.after.seed,frame.after.units,frame.after.hash,after.tick,after.seed,after.units,after.hash);fail(detail);
  }
 }
 else if(!equal(frame.before,after)||!commands.empty()) {
  frame.after=after;frame.result=dispatchResult;frame.count=(uint32_t)commands.size();
  uint32_t tag=1;write(&tag,4);write(&frame,sizeof(frame));write(commands.data(),commands.size()*sizeof(Command));
 }else return result;
 ++frames;if(playback&&stepping){paused=true;stepping=false;}
 if(playback&&after.tick>frame.before.tick){playbackClock+=framePeriod();int64_t now=counterNow();if(now-playbackClock>framePeriod()*2)playbackClock=now;}
 if(output&&frames%300==0)fflush(output);
 if(frames%100==0){char text[80];sprintf_s(text,"%s %u %u",playback?"PLAYING":"RECORDING",frames,after.tick);status(text);}
 return result;
}
void __cdecl bootstrap(){
 uint16_t state=mem<uint16_t>(0x4dec90);
 if(!playback&&active&&state!=3&&state!=22&&state!=23){finish();return;}
 if(playback&&active&&state!=3&&state!=22&&state!=23){
  if(cursor+4==input.size()&&mem<uint32_t>((uintptr_t)input.data()+cursor)==0xffffffff){cursor+=4;finish();}
  else fail("ERROR: replay left battle before its final record");
  return;
 }
 if(active||failed||completed)return;
#ifdef MYTH_REPLAY_TEST
 bool fromSave=!playback&&GetFileAttributesW((root+L"\\initial.dat").c_str())!=INVALID_FILE_ATTRIBUTES;
 if(!playback&&!fromSave)return;
#else
 if(!playback)return;
#endif
 // Run on the native game thread once the initial menus have been initialized.
 // Follow the native LOAD return path: full loader, battle graphics, state 3.
 if(state!=9&&state!=220)return;
#ifdef MYTH_REPLAY_TEST
 if(fromSave){if(!checkpointOperation(true)){fail("ERROR: fixture restore failed");return;}}
#endif
 // The renderer must be in battle mode BEFORE loading the checkpoint palette.
 // Recreating DirectDraw surfaces afterwards discarded that palette (black
 // screen), and bypassing the menu exit left menumusic.YAV playing.
 if(playback)((void(__cdecl*)())0x41f980)();
 ((void(__cdecl*)())0x46afd0)();
 if(playback){
  begin();if(failed)return;
  HWND window=mem<HWND>(0x7a2ce0);
  previousWindowProc=(WNDPROC)SetWindowLongPtrA(window,GWLP_WNDPROC,(LONG_PTR)replayWindowProc);
  if(!previousWindowProc){fail("ERROR: replay keyboard hookup failed");return;}
  ((void(__cdecl*)(int))0x468b20)(mem<int16_t>(0xca5628));
  int player=mem<int32_t>(0xcbdc3c);
  if(player<0||player>=8){fail("ERROR: invalid viewpoint player");return;}
  ((int(__cdecl*)(int))0x469a40)(mem<uint8_t>(0xb137bc+player*0x33d4));
 }
 mem<uint16_t>(0x4dec90)=3;
 mem<uint32_t>(0xcedd74)=0;mem<uint32_t>(0xcedd78)=0;
 mem<uint32_t>(0xcedd7c)=0;mem<uint32_t>(0xcedd80)=0;
#ifdef MYTH_REPLAY_TEST
 if(fromSave)begin();
#endif
}
uintptr_t loopContinue=0x470cd8;
__declspec(naked) void loopHook(){__asm {
 pushfd
 pushad
 call bootstrap
 popad
 popfd
 movsx eax,word ptr ds:[0x4dec90]
 jmp [loopContinue]
}}
bool patch(uintptr_t where,const void* bytes,size_t n){
 DWORD old;if(!VirtualProtect((void*)where,n,PAGE_EXECUTE_READWRITE,&old))return false;
 edits.push_back({where,std::vector<uint8_t>((uint8_t*)where,(uint8_t*)where+n)});
 memcpy((void*)where,bytes,n);FlushInstructionCache(GetCurrentProcess(),(void*)where,n);
 DWORD ignored;VirtualProtect((void*)where,n,old,&ignored);return true;
}
void rollback(){
 for(auto e=edits.rbegin();e!=edits.rend();++e){DWORD old;if(VirtualProtect((void*)e->where,e->before.size(),PAGE_EXECUTE_READWRITE,&old)){memcpy((void*)e->where,e->before.data(),e->before.size());FlushInstructionCache(GetCurrentProcess(),(void*)e->where,e->before.size());DWORD ignored;VirtualProtect((void*)e->where,e->before.size(),old,&ignored);}}
 edits.clear();
}
bool jump(uintptr_t where,void* target,size_t length){
 uint8_t b[16];if(length<5||length>sizeof(b))return false;
 memset(b,0x90,length);b[0]=0xe9;mem<int32_t>((uintptr_t)b+1)=(int32_t)((uintptr_t)target-where-5);
 return patch(where,b,length);
}
bool install(){
 wchar_t dir[32768],mode[16];
 if(!GetEnvironmentVariableW(L"MYTH_REPLAY_DIR",dir,32768))return true;
 root=dir;GetEnvironmentVariableW(L"MYTH_REPLAY_MODE",mode,16);playback=!wcscmp(mode,L"play");
 // The native CRT uses ANSI file names. A launcher-created short ASCII staging
 // directory is required; never silently replace an unrepresentable path.
 BOOL replaced=FALSE;
 if(!WideCharToMultiByte(CP_ACP,WC_NO_BEST_FIT_CHARS,(root+L"\\initial.dat").c_str(),-1,checkpoint,MAX_PATH,nullptr,&replaced)||replaced||strlen(checkpoint)>=120)return false;
 if(playback){
  FILE* f=_wfopen((root+L"\\commands.bin").c_str(),L"rb");if(!f)return false;
  fseek(f,0,SEEK_END);long n=ftell(f);rewind(f);
  if(n<12||n>128*1024*1024){fclose(f);return false;}
  input.resize(n);bool ok=fread(input.data(),1,n,f)==(size_t)n;fclose(f);
  if(!ok||memcmp(input.data(),"MYTHRP01",8))return false;
 }
 // Reject any unexpected baseline, before changing a single byte.
 if(memcmp((void*)0x46c5a0,"\x83\xec\x08\xe8\x98\xa1\xff\xff",8)||
    memcmp((void*)0x4353a1,"\x0f\xbf\xc8\x8d\x0c\x49",6)||
    memcmp((void*)0x435356,"\x33\xff\xbe\x6e\x65\xb1\x00",7)||
    memcmp((void*)0x48d170,"\x0f\xbf\x44\x24\x04",5)||
    memcmp((void*)0x470cd1,"\x0f\xbf\x05\x90\xec\x4d\x00",7)||
    memcmp((void*)0x46c69c,"\xe8\x2f\x8c\xfc\xff",5)||
    memcmp((void*)0x46c6a9,"\xe8\xf2\x00\x00\x00",5))return false;
 uintptr_t commandTarget=0x435045+mem<int32_t>(0x435041);
 if(playback)for(auto call: {std::pair<uintptr_t,uintptr_t>{0x46c68d,0x47fa10},{0x471f02,0x46bda0},{0x471f62,0x46be00},{0x471f85,0x46bea0},{0x471fa8,0x46c380}})
  if(mem<uint8_t>(call.first)!=0xe8||call.first+5+mem<int32_t>(call.first+1)!=call.second)return false;
 bool hdCommand=mem<uint8_t>(0x435040)==0xe9&&mem<uint8_t>(0x435045)==0x90&&commandTarget>=0x11d0000&&commandTarget<0x11d2000;
 if(memcmp((void*)0x435040,"\x81\xec\xb8\x00\x00\x00",6)&&!hdCommand)return false;
 advance=VirtualAlloc(nullptr,32,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);
 if(!advance)return false;
 auto t=(uint8_t*)advance;memcpy(t,(void*)0x46c5a0,8);
 mem<int32_t>((uintptr_t)t+4)=(int32_t)(0x466740-(uintptr_t)t-8);
 jump((uintptr_t)t+8,(void*)0x46c5a8,5);
 uint8_t call[5]={0xe8};mem<int32_t>((uintptr_t)call+1)=(int32_t)((uintptr_t)dispatch-0x46c6a1);
 uint8_t timer[5]={0xe8};mem<int32_t>((uintptr_t)timer+1)=(int32_t)((uintptr_t)timerGate-0x46c6ae);
 if(playback&&!patch(0x435040,"\xb8\x01\x00\x00\x00\xc3",6))return false;
 if(playback){
  if(memcmp((void*)0x433560,"\x66\x8b\x15\xa6\x72\x66\x00",7)||memcmp((void*)0x41fb50,"\x81\xec\xb0\x00\x00\x00",6)||memcmp((void*)0x431330,"\x81\xec\x88\x00\x00\x00",6))return false;
  // UI notification enqueue and portrait renderer; combat audio is retained.
  if(!patch(0x433560,"\xb8\x01\x00\x00\x00\xc3\x90",7)||!patch(0x41fb50,"\xb8\x01\x00\x00\x00\xc3",6)||!patch(0x431330,"\xb8\x01\x00\x00\x00\xc3",6))return false;
 }
 if(playback){
  for(auto site: {std::pair<uintptr_t,uintptr_t>{0x46c68d,(uintptr_t)observerFog},{0x471f02,(uintptr_t)observerBackground},{0x471f62,(uintptr_t)observerUnits},{0x471f85,(uintptr_t)observerSelection},{0x471fa8,(uintptr_t)observerHud}}){
   uint8_t code[5]={0xe8};mem<int32_t>((uintptr_t)code+1)=(int32_t)(site.second-site.first-5);if(!patch(site.first,code,5))return false;
  }
 }
 if(!jump(0x470cd1,(void*)loopHook,7)||!patch(0x46c6a9,timer,5)||!patch(0x46c69c,call,5)||!jump(0x48d170,(void*)pathHook,5)||
    !jump(0x4353a1,(void*)packetHook,6)||!jump(0x435356,(void*)queueHook,7)||!jump(0x46c5a0,(void*)advanceHook,8))return false;
 status("READY");return true;
}
}
BOOL WINAPI DllMain(HINSTANCE module,DWORD reason,LPVOID){
 if(reason==DLL_PROCESS_ATTACH){DisableThreadLibraryCalls(module);if(!install()){rollback();return FALSE;}}
 if(reason==DLL_PROCESS_DETACH&&output)finish();
 return TRUE;
}
