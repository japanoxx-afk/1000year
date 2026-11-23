// Local-only battle UI: custom hotkeys and a hero portrait bar.
// Neither feature writes simulation state or creates command packets of its
// own. Hotkeys only translate the virtual key the native window procedure sees,
// so every client still receives the same native commands. The hero bar draws
// with the game's own portrait sheet and moves only the local camera through
// the native jump request used by the "last alert" key.

// ---- Custom hotkeys ------------------------------------------------------
// keyMap[physical] = logical virtual key. Identity by default; 0 disables a key.
uint8_t keyMap[256];
bool keyMapActive=false,heroBarEnabled=true,clipCursorEnabled=true,cursorClipped=false;
WNDPROC localPreviousProc=nullptr;HWND localWindow=nullptr;
bool swallowLeftUp=false;

// Keys that the native game polls with GetAsyncKeyState (camera arrows and
// modifiers) cannot be translated through window messages and are never mapped.
bool remappableKey(unsigned key){
 return key>=8&&key<256&&key!=VK_SHIFT&&key!=VK_CONTROL&&key!=VK_MENU&&key!=VK_RETURN&&
  key!=VK_LSHIFT&&key!=VK_RSHIFT&&key!=VK_LCONTROL&&key!=VK_RCONTROL&&key!=VK_LMENU&&key!=VK_RMENU&&
  !(key>=VK_LEFT&&key<=VK_DOWN)&&key!=VK_ESCAPE&&key!=VK_LWIN&&key!=VK_RWIN&&key!=VK_SNAPSHOT;
}
// MYTH_KEYMAP: comma separated "PHYSICAL:LOGICAL" hex virtual-key pairs.
void loadKeyMap(){
 for(unsigned i=0;i<256;++i)keyMap[i]=(uint8_t)i;
 wchar_t text[4096];DWORD n=GetEnvironmentVariableW(L"MYTH_KEYMAP",text,4096);
 if(n&&n<4096){
  const wchar_t* p=text;
  while(*p){
   wchar_t* end=nullptr;unsigned long from=wcstoul(p,&end,16);
   if(end==p||*end!=L':')break;p=end+1;
   unsigned long to=wcstoul(p,&end,16);if(end==p)break;p=end;
   if(from<256&&to<256&&remappableKey((unsigned)from)&&(to==0||remappableKey((unsigned)to))){keyMap[from]=(uint8_t)to;keyMapActive=true;}
   while(*p==L','||*p==L' ')++p;
  }
 }
 wchar_t hero[8];if(GetEnvironmentVariableW(L"MYTH_HERO_BAR",hero,8)&&hero[0]==L'0')heroBarEnabled=false;
 wchar_t clip[8];if(GetEnvironmentVariableW(L"MYTH_CLIP_CURSOR",clip,8)&&clip[0]==L'0')clipCursorEnabled=false;
}
bool inBattleInput(){return mem<uint16_t>(0x4dec90)==3&&!mem<uint32_t>(0xb9022c);}

// ---- Cursor confinement --------------------------------------------------
// During a battle, while the game window is the foreground window, keep the
// cursor inside its client area so edge scrolling works on every monitor
// layout. Losing focus (Alt+Tab), minimising or leaving the battle releases it.
void releaseCursor(){if(cursorClipped){ClipCursor(nullptr);cursorClipped=false;}}
void confineCursor(){
 if(playback||!clipCursorEnabled)return;
 HWND window=mem<HWND>(0x7a2ce0);
 if(!window||!IsWindow(window)||GetForegroundWindow()!=window||IsIconic(window)||mem<uint16_t>(0x4dec90)!=3){releaseCursor();return;}
 RECT client;if(!GetClientRect(window,&client))return;
 POINT a{client.left,client.top},b{client.right,client.bottom};ClientToScreen(window,&a);ClientToScreen(window,&b);
 RECT area{a.x,a.y,b.x,b.y};if(area.right<=area.left||area.bottom<=area.top)return;
 RECT current{};GetClipCursor(&current);
 if(!cursorClipped||!EqualRect(&current,&area)){if(ClipCursor(&area))cursorClipped=true;}
}

// ---- Hero portrait bar ---------------------------------------------------
struct HeroCard {RECT box;uint32_t handle;};
std::vector<HeroCard> heroCards;
std::vector<uint8_t> heroUnderlay;void* heroSurface=nullptr;RECT heroArea{};
constexpr int heroSheet=0xfb;
bool heroUnit(unsigned id){
 if(!mem<uint16_t>(0xa79620+id*2))return false;
 uintptr_t u=0x7ca6e8+id*2308;
 return mem<int32_t>(u+0x9c)>0&&mem<uint8_t>(u+0x324)==1&&(mem<uint32_t>(u+0x1d8)&0x20000)&&
  (int)mem<int8_t>(u+0x76)==mem<int32_t>(0xcbdc3c);
}
// Day/night changes the palette, so resolve the bar color for every frame.
uint8_t nearestColor(uint8_t r,uint8_t g,uint8_t b,uint8_t fallback){
 void* primary=mem<void*>(0x115f814);void* palette=nullptr;PALETTEENTRY entries[256]{};
 if(!primary||FAILED(((HRESULT(WINAPI*)(void*,void**))(*(void***)primary)[20])(primary,&palette))||!palette)return fallback;
 HRESULT got=((HRESULT(WINAPI*)(void*,DWORD,DWORD,DWORD,PALETTEENTRY*))(*(void***)palette)[4])(palette,0,0,256,entries);
 ((ULONG(WINAPI*)(void*))(*(void***)palette)[2])(palette);if(FAILED(got))return fallback;
 int best=fallback;long bestDistance=0x7fffffff;
 for(int i=1;i<255;++i){long dr=entries[i].peRed-r,dg=entries[i].peGreen-g,db=entries[i].peBlue-b;long d=dr*dr+dg*dg+db*db;if(d<bestDistance){bestDistance=d;best=i;}}
 return (uint8_t)best;
}
void restoreHeroes(){
 if(!heroSurface||heroUnderlay.empty())return;
 uint8_t desc[124];if(lockSurface(heroSurface,desc)){
  auto target=mem<uint8_t*>((uintptr_t)desc+36);int pitch=mem<int32_t>((uintptr_t)desc+16);int w=heroArea.right-heroArea.left;
  if(target&&pitch>=heroArea.right)for(int y=heroArea.top;y<heroArea.bottom;++y)memcpy(target+y*pitch+heroArea.left,heroUnderlay.data()+(y-heroArea.top)*w,w);
  unlockSurface(heroSurface);
 }heroSurface=nullptr;heroUnderlay.clear();
}
void fillRect(uint8_t* target,int pitch,int x0,int y0,int x1,int y1,uint8_t color){for(int y=y0;y<y1;++y)memset(target+y*pitch+x0,color,x1-x0);}
void bar(uint8_t* target,int pitch,int x,int y,int w,int value,int maximum,uint8_t color,uint8_t frame){
 fillRect(target,pitch,x,y,x+w,y+5,frame);fillRect(target,pitch,x+1,y+1,x+w-1,y+4,0);
 if(maximum<=0)return;int filled=(int)((int64_t)std::max(0,std::min(value,maximum))*(w-2)/maximum);
 if(filled>0)fillRect(target,pitch,x+1,y+1,x+1+filled,y+4,color);
}
void drawHeroes(){
 heroCards.clear();
 if(playback||!heroBarEnabled||failed||mem<uint16_t>(0x4dec90)!=3||mem<int32_t>(0x115e304)!=8)return;
 void* surface=mem<void*>(0x65181c);int width=mem<int32_t>(0x115e2fc),height=mem<int32_t>(0x115e300);
 if(!surface||width<640||width>8192||height<480||height>8192)return;
 int portraitW=((int(__cdecl*)(int))0x469c10)(heroSheet),portraitH=((int(__cdecl*)(int))0x469c30)(heroSheet);
 bool portraits=portraitW>0&&portraitH>0&&portraitW<=96&&portraitH<=96;
 int cardW=portraits?portraitW+4:44,imageH=portraits?portraitH:36,cardH=imageH+16;
 // Below the idle-worker label (HD) or the elapsed timer (native 640x480).
 int left=4,top=width>=1024?28:56,limit=height-60;
 std::vector<unsigned> heroes;
 for(unsigned id=1;id<1200;++id)if(heroUnit(id))heroes.push_back(id);
 while(!heroes.empty()&&top+(int)heroes.size()*(cardH+4)>limit)heroes.pop_back();
 if(heroes.empty())return;
 heroArea={left,top,left+cardW,top+(int)heroes.size()*(cardH+4)};
 uint8_t desc[124];
 if(!lockSurface(surface,desc))return;
 {auto target=mem<uint8_t*>((uintptr_t)desc+36);int pitch=mem<int32_t>((uintptr_t)desc+16);int w=heroArea.right-heroArea.left;
  if(!target||pitch<width){unlockSurface(surface);return;}
  heroUnderlay.resize((size_t)w*(heroArea.bottom-heroArea.top));
  for(int y=heroArea.top;y<heroArea.bottom;++y)memcpy(heroUnderlay.data()+(y-heroArea.top)*w,target+y*pitch+heroArea.left,w);
  heroSurface=surface;
  for(size_t i=0;i<heroes.size();++i){int y=top+(int)i*(cardH+4);fillRect(target,pitch,left,y,left+cardW,y+cardH,0xfd);fillRect(target,pitch,left+1,y+1,left+cardW-1,y+cardH-1,0);}
 }
 unlockSurface(surface);
 // Native portrait blit through the renderer's own surface lock and clipping.
 if(portraits&&((int(__thiscall*)(void*,void*))0x4af970)((void*)0x115e2f8,surface)==1){
  for(size_t i=0;i<heroes.size();++i){
   uintptr_t u=0x7ca6e8+heroes[i]*2308;unsigned type=mem<uint8_t>(u+0x75);
   int frame=mem<int16_t>(0xb60d10+type*896);
   if(frame>=0)((void(__cdecl*)(int,int,int,int))0x469c50)(left+2,top+(int)i*(cardH+4)+2,heroSheet,frame);
  }
  ((int(__thiscall*)(void*,void*))0x4afb30)((void*)0x115e2f8,surface);
 }
 // Palette reads go through the graphics wrapper's lock; refresh twice a second.
 static uint8_t mana=0xd6,high=0xd6,middle=0xd5,low=0xd7;static DWORD paletteChecked=0;
 if(!paletteChecked||GetTickCount()-paletteChecked>=500){paletteChecked=GetTickCount();mana=nearestColor(48,96,240,0xd6);high=nearestColor(32,200,48,0xd6);middle=nearestColor(232,208,32,0xd5);low=nearestColor(224,32,24,0xd7);}
 if(lockSurface(surface,desc)){
  auto target=mem<uint8_t*>((uintptr_t)desc+36);int pitch=mem<int32_t>((uintptr_t)desc+16);
  if(target&&pitch>=width)for(size_t i=0;i<heroes.size();++i){
   uintptr_t u=0x7ca6e8+heroes[i]*2308;int y=top+(int)i*(cardH+4);
   int hp=mem<int32_t>(u+0x9c),hpMax=mem<int32_t>(u+0x108),mp=mem<int32_t>(u+0xa0),mpMax=mem<int32_t>(u+0x10c);
   // Same thresholds as the native unit health bar: above 70%, above 30%, rest.
   uint8_t hpColor=hpMax>0&&hp*10>hpMax*7?high:hpMax>0&&hp*10>hpMax*3?middle:low;
   bar(target,pitch,left+2,y+imageH+3,cardW-4,hp,hpMax,hpColor,0xfd);
   if(mpMax>0)bar(target,pitch,left+2,y+imageH+9,cardW-4,mp,mpMax,mana,0xfd);
   heroCards.push_back({{left,y,left+cardW,y+cardH},mem<uint32_t>(u+0x29c)});
  }
  unlockSurface(surface);
 }
}
// Move only this client's camera, through the native jump request (the same
// request the game issues for the last-alert key).
bool clickHero(){
 int x=mem<int32_t>(0xd375b0),y=mem<int32_t>(0xd375b4);
 for(const auto& card:heroCards){
  if(x<card.box.left||x>=card.box.right||y<card.box.top||y>=card.box.bottom)continue;
  unsigned id=card.handle&0xffff;if(id<1||id>=1200||!heroUnit(id)||mem<uint32_t>(0x7ca6e8+id*2308+0x29c)!=card.handle)return true;
  uintptr_t u=0x7ca6e8+id*2308;
  ((void(__thiscall*)(void*,int,int))0x42c600)((void*)0xa6e9a8,mem<int16_t>(u+0x2a8),mem<int16_t>(u+0x2aa));
  return true;
 }
 return false;
}
LRESULT CALLBACK localWindowProc(HWND window,UINT message,WPARAM key,LPARAM data){
 if(cursorClipped&&((message==WM_ACTIVATEAPP&&!key)||message==WM_KILLFOCUS||(message==WM_SIZE&&key==SIZE_MINIMIZED)||(message==WM_MOUSEMOVE&&mem<uint16_t>(0x4dec90)!=3)))releaseCursor();
 if(message==WM_LBUTTONDOWN&&!heroCards.empty()&&inBattleInput()&&clickHero()){swallowLeftUp=true;return 0;}
 if(message==WM_LBUTTONUP&&swallowLeftUp){swallowLeftUp=false;return 0;}
 if(keyMapActive&&key<256&&(message==WM_KEYDOWN||message==WM_SYSKEYDOWN||message==WM_KEYUP||message==WM_SYSKEYUP)){
  uint8_t mapped=keyMap[key];
  if(mapped!=key){
   if(message==WM_KEYUP||message==WM_SYSKEYUP){
    // Release both the physical and the logical key so a key held across a
    // chat toggle can never remain pressed in the native key array.
    mem<uint16_t>(0x78c928+key*2)=0;
    if(!mapped)return CallWindowProcA(localPreviousProc,window,message,key,data);
    if(mem<uint16_t>(0x4dec90)==3)key=mapped;
   }else if(inBattleInput()){
    if(!mapped)return 0;
    key=mapped;data=(data&~0x01ff0000)|((LPARAM)MapVirtualKeyA(mapped,0)<<16);
   }
  }
 }
 return CallWindowProcA(localPreviousProc,window,message,key,data);
}
// Subclass once, on the native game thread, after the battle window exists.
void attachLocalInput(){
 if(playback||localPreviousProc||(!keyMapActive&&!heroBarEnabled&&!clipCursorEnabled))return;
 HWND window=mem<HWND>(0x7a2ce0);if(!window||!IsWindow(window))return;
 localPreviousProc=(WNDPROC)SetWindowLongPtrA(window,GWLP_WNDPROC,(LONG_PTR)localWindowProc);
 if(localPreviousProc)localWindow=window;
}
