#include "../native/replay.cpp"
#include <cassert>
#include <iostream>
volatile unsigned char musicFixtureAddressSpace[14*1024*1024];
bool waitMusic(bool playing){for(unsigned n=0;n<50;++n){if((musicPlaying!=0)==playing)return true;Sleep(100);}return false;}
int wmain(int argc,wchar_t** argv){
 assert(argc==2||argc==3);musicFixtureAddressSpace[0]=0;
 wchar_t temporary[MAX_PATH];GetTempPathW(MAX_PATH,temporary);root=temporary;
 battleMusicPath=argv[1];musicAvailable=true;playback=false;
 mem<uint16_t>(0x4dec90)=3;mem<int32_t>(0x7c9cd0)=0;
 serviceBattleMusic();assert(musicThreadStarted==0); // Never override music OFF.
 mem<int32_t>(0x7c9cd0)=1;serviceBattleMusic();assert(waitMusic(true));
 if(argc==3){for(unsigned n=0;n<50&&musicLoops==0;++n)Sleep(100);assert(musicLoops>0);fileMusicStop();assert(waitMusic(false));std::cout<<"PASS: end-of-stream loops local audio and stops cleanly\n";return 0;}
 Sleep(500);LONGLONG first=musicPosition;Sleep(500);assert(musicPosition>first);
 fileMusicPause();assert(waitMusic(false));LONGLONG frozen=musicPosition;Sleep(400);assert(musicPosition==frozen);
 serviceBattleMusic();assert(waitMusic(true));
 mem<int32_t>(0x7c9cd0)=0;serviceBattleMusic();assert(waitMusic(false));assert(fileMusicTrack()==0);
 mem<int32_t>(0x7c9cd0)=1;serviceBattleMusic();assert(waitMusic(true));
 mem<uint16_t>(0x4dec90)=9;assert(waitMusic(false)); // Menu must not overlap.
 mem<uint16_t>(0x4dec90)=3;playback=true;active=true;completed=false;serviceBattleMusic();assert(waitMusic(true));
 finish();assert(waitMusic(false));serviceBattleMusic();assert(musicRequest==0);
 std::cout<<"PASS: real local audio playback/time progression, pause/resume, option OFF/ON, menu stop, replay start/completion stop\n";
}
