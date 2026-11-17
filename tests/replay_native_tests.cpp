// Execute the adapter's real x86 hook and queue code in an isolated process.
#include "../native/replay.cpp"
#include <cassert>
#include <iostream>
// Reserve the game's low address range in this fixed-base test image, before
// Windows chooses heap/stack addresses. The production adapter uses game data.
volatile unsigned char fixtureAddressSpace[14*1024*1024];
__declspec(naked) void soundFixture(){__asm {
 mov eax,42
 ret
 }}
std::vector<uint8_t> fixturePixels(1344*720);unsigned fixtureLocks=0,fixtureUnlocks=0;
HRESULT WINAPI fixtureLock(void*,RECT*,void* result,DWORD,HANDLE){++fixtureLocks;mem<int32_t>((uintptr_t)result+16)=1344;mem<uint8_t*>((uintptr_t)result+36)=fixturePixels.data();return S_OK;}
HRESULT WINAPI fixtureUnlock(void*,RECT*){++fixtureUnlocks;return S_OK;}
int main(){
 // Music OFF and replay completion must never start a decoder thread.
 musicAvailable=true;mem<uint16_t>(0x4dec90)=3;mem<int32_t>(0x7c9cd0)=0;
 serviceBattleMusic();assert(musicThreadStarted==0&&musicRequest==0);
 playback=true;completed=true;mem<int32_t>(0x7c9cd0)=1;
 serviceBattleMusic();assert(musicThreadStarted==0&&musicRequest==0);
 completed=false;musicAvailable=false;playback=false;
 speed=150;speedKeys=0;setSpeedKeys(2);assert(speed==200);speed=150;setSpeedKeys(2);assert(speed==150);setSpeedKeys(0);setSpeedKeys(4);assert(speed==400);setSpeedKeys(1);assert(speed==150);
 clockFrequency=1000000;tickMilliseconds=50;assert(framePeriod()==33333);
 fixtureAddressSpace[0]=0;
 memset((void*)0xaaf4a6,0x22,0xc800);
 memset((void*)0xa7d4a6,1,8*0x6400);playback=true;active=true;failed=false;
 uint8_t nightLight[4]{0,0,0,0},nightShade[4]{3,3,3,3};mem<uint8_t*>(0xcaa234)=nightLight;mem<uint8_t*>(0xcaa238)=nightShade;mem<int16_t>(0xca5624)=2;mem<int16_t>(0xca5626)=2;mem<uint32_t>(0xca98f4+4)=2;mem<int16_t>(0xb2d85e)=5;
 {ObserverView view;assert(mem<uint8_t>(0xa7d4a6)==0&&mem<uint16_t>(0xaaf4a6)==0&&mem<uint16_t>(0xaaf4a6+0xc800-2)==0);{ObserverView nested;assert(revealDepth==2);}assert(mem<uint8_t>(0xa7d4a6+8*0x6400-1)==0);assert(nightLight[3]==0&&nightShade[3]==3&&mem<int16_t>(0xb2d85e)==0);}
 assert(nightLight[3]==0&&nightShade[3]==3&&mem<int16_t>(0xb2d85e)==5);
 assert(mem<uint16_t>(0xaaf4a6)==0x2222&&mem<uint16_t>(0xaaf4a6+0xc800-2)==0x2222);
 assert(revealDepth==0&&mem<uint8_t>(0xa7d4a6)==1&&mem<uint8_t>(0xa7d4a6+8*0x6400-1)==1);

 // Enemy units need the cached unit visibility flag as well as terrain fog.
 uintptr_t enemy=0x7ca6e8+30*2308,embarked=enemy+2308,dead=embarked+2308;
 for(unsigned id=30;id<=32;++id)mem<uint16_t>(0xa79620+id*2)=4;
 mem<uint8_t>(enemy+0x76)=1;mem<int32_t>(enemy+0x9c)=100;mem<uint8_t>(enemy+0x324)=1;mem<uint8_t>(enemy+0x1c)=0;mem<uint32_t>(enemy+0x60)=240;mem<uint32_t>(0xa6ea50)=240;
 mem<int32_t>(embarked+0x9c)=100;mem<uint8_t>(embarked+0x324)=0;mem<uint8_t>(embarked+0x1c)=0;
 mem<int32_t>(dead+0x9c)=0;mem<uint8_t>(dead+0x324)=1;mem<uint8_t>(dead+0x1c)=0;
 {ObserverUnits view;assert(mem<uint8_t>(enemy+0x1c)==1&&mem<uint32_t>(enemy+0x60)==239);assert(!mem<uint8_t>(embarked+0x1c)&&!mem<uint8_t>(dead+0x1c));mem<uint32_t>(enemy+0x60)=240;}
 assert(!mem<uint8_t>(enemy+0x1c)&&mem<uint32_t>(enemy+0x60)==240&&observerDrawn[1]==1);
 // Exercise the real x86 sound filter: positional combat reaches native queue.
 soundQueueContinue=(uintptr_t)soundFixture;auto sound=(int(__cdecl*)(int,int,int))observerSoundQueue;
 assert(sound(20,0,0)==1&&positionalSounds==0);assert(sound(20,12,17)==42&&positionalSounds==1);assert(sound(20,0,17)==42&&positionalSounds==2);
 assert(sound(21,12,17)==1&&positionalSounds==2); // no hero arrival chime
 heroEffectContinue=(uintptr_t)soundFixture;auto effect=(int(__cdecl*)(int))observerEffectDraw;
 mem<uint16_t>(0xd41272+3*68)=29;assert(effect(3)==1&&heroEffectsSkipped==1);mem<uint16_t>(0xd41272+3*68)=4;assert(effect(3)==42&&heroEffectsSkipped==1);
 assert(elapsedLabel(0,50)==L"경과 00:00"&&elapsedLabel(1200,50)==L"경과 01:00"&&elapsedLabel(72000,50)==L"경과 1:00:00");
 for(unsigned id=30;id<=32;++id)mem<uint16_t>(0xa79620+id*2)=0;
 playback=false;{ObserverView view;assert(mem<uint8_t>(0xa7d4a6)==1);}
 memset((void*)0x7a0000,0,0x20000);mem<uint8_t>(0xb137bc)=1;mem<int32_t>(0xb137bc+0x14)=12345;mem<int32_t>(0xb137bc+0x18)=67890;mem<int32_t>(0xb137bc+0x1c)=4;mem<int16_t>(0xb137bc+0x1b5c)=20;mem<int16_t>(0xb137bc+0x1b62)=1600;
 // Native indexed frame: changing temporary pitch must not move the panel.
 mem<int32_t>(0x115e2fc)=1280;mem<int32_t>(0x115e300)=720;mem<int32_t>(0x115e304)=8;mem<int32_t>(0x115e308)=512;
 void* vtable[33]{};vtable[25]=(void*)fixtureLock;vtable[32]=(void*)fixtureUnlock;void** object=vtable;mem<void*>(0x65181c)=&object;
 std::fill(fixturePixels.begin(),fixturePixels.end(),uint8_t(67));auto terrain=fixturePixels;
 playback=true;active=true;failed=false;auto resourceBuilds=resourceMask.builds;drawResources();assert(resourceMask.builds==resourceBuilds+1);assert(resourceCommits==1&&resourceLeft==850&&fixtureLocks==fixtureUnlocks);
 auto firstImage=fixturePixels;bool hasText=false;for(int y=34;y<66;++y)for(int x=850;x<1280;++x)if(fixturePixels[y*1344+x]!=67)hasText=true;assert(hasText);
 assert(fixturePixels[0]==67);restoreResources();assert(fixturePixels==terrain&&fixtureLocks==fixtureUnlocks);
 mem<int32_t>(0x115e308)=640;drawResources();assert(resourceMask.builds==resourceBuilds+1);assert(resourceLeft==850&&fixturePixels==firstImage);restoreResources();assert(fixturePixels==terrain);
 // Updated numbers start with the clean terrain, leaving no previous glyphs.
 mem<int32_t>(0xb137bc+0x14)=1;drawResources();assert(resourceMask.builds==resourceBuilds+2);assert(fixturePixels!=firstImage);restoreResources();assert(fixturePixels==terrain);mem<int32_t>(0xb137bc+0x14)=12345;
 // Timer works with recording disabled, without enabling observer vision.
 playback=false;hudOnly=true;active=false;mem<uint16_t>(0x4dec90)=3;mem<uint32_t>(0xa6ea50)=1200;timerTickStep=50;timerLastTick=1200;
 auto timerBuilds=timerMask.builds;drawTimer();assert(timerMask.builds==timerBuilds+1);assert(timerLeft==586&&timerTop==8&&fixturePixels!=terrain);auto timerFrame=fixturePixels;restoreTimer();assert(fixturePixels==terrain);drawTimer();assert(timerMask.builds==timerBuilds+1&&fixturePixels==timerFrame);restoreTimer();assert(fixturePixels==terrain);
 mem<uint32_t>(0xa6ea50)=1220;drawTimer();assert(timerMask.builds==timerBuilds+2&&fixturePixels!=timerFrame);restoreTimer();assert(fixturePixels==terrain);hudOnly=false;
 mem<void*>(0x65181c)=nullptr;
 auto rows=playerResources();assert(rows.size()==1&&rows[0].rice==12345&&rows[0].wood==67890&&rows[0].population==24&&rows[0].limit==1600);
 memset((void*)0xb10000,0,0x30000);active=false;
 memset((void*)0xb10000,0,0x20000);
 memset((void*)0xa60000,0,0x20000);
 unsigned fixtureId=120;uintptr_t unit=0x7ca6e8+fixtureId*2308;
 mem<uint32_t>(0xa6ea50)=240;mem<uint32_t>(0xa6ea5c)=123;
 auto original=snapshot();
 mem<uint16_t>(0xa79620+fixtureId*2)=4;
 mem<uint32_t>(unit+0x9c)=100;
 auto a=snapshot();assert(a.units==1&&a.hash!=original.hash);
 mem<uint32_t>(unit+0x9c)=99;assert(snapshot().hash!=a.hash);
 mem<uint32_t>(unit+0x9c)=100;assert(equal(a,snapshot()));
 playback=false;inside=true;
 Packet p{};mem<uint16_t>((uintptr_t)p.bytes)=3;
 mem<uint16_t>((uintptr_t)p.bytes+20)=1;
 mem<uint32_t>((uintptr_t)p.bytes+22)=0x12340078;
 for(unsigned player=0;player<8;++player){
  mem<uint32_t>((uintptr_t)p.bytes+4)=player+50;
  capture(&p,player);
 }
 assert(commands.size()==8);
 for(auto& c:commands)mem<uint16_t>((uintptr_t)c.packet.bytes)=352;
 playback=true;frame.before.tick=240;
 prepareCommands();assert(!failed);
 for(unsigned player=0;player<8;++player){
  uintptr_t q=0xa6f280+player*50*104;
  assert(mem<uint16_t>(q)==352&&mem<uint32_t>(q+4)==player+50);
  assert(mem<uint32_t>(q+16)==239&&mem<uint32_t>(q+22)==0x12340078);
  assert(mem<uint16_t>(q+104)==0);
 }
 commands.clear();for(unsigned i=0;i<50;++i)commands.push_back({7,p});
 prepareCommands();assert(!failed&&mem<uint16_t>(0xa6f280+399*104)==3);
 // Invalid batches are rejected before writing beyond the fixed queue.
 commands.push_back({7,p});prepareCommands();assert(failed);
 failed=false;commands.clear();commands.push_back({8,p});prepareCommands();assert(failed);
 // Strict bounded parsing accepts no truncated record, even with an oversized request.
 failed=false;input={1,2,3,4};cursor=0;uint32_t n=0;assert(read(&n,4));assert(n==0x04030201);
 assert(!read(&n,4)&&failed);
 std::cout<<"PASS: hero arrival visuals/chime suppression, replay/live HUD timer, raw/derived fog restoration, enemy/dead/embarked visibility, indexed panel stability/clean restoration across pitch changes, positional combat audio, resource rows, x86 eight-player capture/injection, handle preservation, queue limits, state checksums, bounded parser\n";
}
