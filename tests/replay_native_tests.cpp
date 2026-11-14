// Execute the adapter's real x86 hook and queue code in an isolated process.
#include "../native/replay.cpp"
#include <cassert>
#include <iostream>
// Reserve the game's low address range in this fixed-base test image, before
// Windows chooses heap/stack addresses. The production adapter uses game data.
volatile unsigned char fixtureAddressSpace[12*1024*1024];
int main(){
 speed=150;speedKeys=0;setSpeedKeys(2);assert(speed==200);speed=150;setSpeedKeys(2);assert(speed==150);setSpeedKeys(0);setSpeedKeys(4);assert(speed==400);setSpeedKeys(1);assert(speed==150);
 clockFrequency=1000000;tickMilliseconds=50;assert(framePeriod()==33333);
 fixtureAddressSpace[0]=0;
 memset((void*)0xa7d4a6,1,8*0x6400);playback=true;active=true;failed=false;
 uint8_t nightLight[4]{0,0,0,0},nightShade[4]{3,3,3,3};mem<uint8_t*>(0xcaa234)=nightLight;mem<uint8_t*>(0xcaa238)=nightShade;mem<int16_t>(0xca5624)=2;mem<int16_t>(0xca5626)=2;mem<uint32_t>(0xca98f4+4)=2;mem<int16_t>(0xb2d85e)=5;
 {ObserverView view;assert(mem<uint8_t>(0xa7d4a6)==0);{ObserverView nested;assert(revealDepth==2);}assert(mem<uint8_t>(0xa7d4a6+8*0x6400-1)==0);assert(nightLight[3]==0&&nightShade[3]==3&&mem<int16_t>(0xb2d85e)==0);}
 assert(nightLight[3]==0&&nightShade[3]==3&&mem<int16_t>(0xb2d85e)==5);
 assert(revealDepth==0&&mem<uint8_t>(0xa7d4a6)==1&&mem<uint8_t>(0xa7d4a6+8*0x6400-1)==1);
 playback=false;{ObserverView view;assert(mem<uint8_t>(0xa7d4a6)==1);}
 memset((void*)0x7a0000,0,0x20000);mem<uint8_t>(0xb137bc)=1;mem<int32_t>(0xb137bc+0x14)=12345;mem<int32_t>(0xb137bc+0x18)=67890;mem<int32_t>(0xb137bc+0x1c)=4;mem<int16_t>(0xb137bc+0x1b5c)=20;mem<int16_t>(0xb137bc+0x1b62)=1600;
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
 std::cout<<"PASS: observer visibility restoration, resource rows, x86 eight-player capture/injection, handle preservation, queue limits, state checksums, bounded parser\n";
}
