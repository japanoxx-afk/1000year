#include "../native/replay.cpp"
#include <cassert>
#include <iostream>
volatile unsigned char musicFixtureAddressSpace[14*1024*1024];
bool waitMusic(bool playing){for(unsigned n=0;n<50;++n){if((musicPlaying!=0)==playing)return true;Sleep(100);}return false;}
void checkVolume(int percent,long expected){FILE* f=_wfopen(musicVolumePath.c_str(),L"wb");assert(f);fprintf(f,"%d",percent);fclose(f);for(unsigned n=0;n<30&&musicPercent!=percent;++n)Sleep(100);assert(musicPercent==percent&&musicDecibels==expected);assert(musicPlaying);}
int wmain(int argc,wchar_t** argv){
 assert(argc==2||argc==3);musicFixtureAddressSpace[0]=0;
 wchar_t temporary[MAX_PATH];GetTempPathW(MAX_PATH,temporary);root=temporary;
 musicVolumePath=root+L"myth-music-volume-test-"+std::to_wstring(GetCurrentProcessId())+L".txt";
 battleMusicPath=argv[1];musicAvailable=true;playback=false;
 mem<uint16_t>(0x4dec90)=3;mem<int32_t>(0x7c9cd0)=0;
 serviceBattleMusic();assert(musicThreadStarted==0); // Never override music OFF.
 mem<int32_t>(0x7c9cd0)=1;serviceBattleMusic();assert(waitMusic(true));
 if(argc==3){for(unsigned n=0;n<50&&musicLoops==0;++n)Sleep(100);assert(musicLoops>0);fileMusicStop();assert(waitMusic(false));std::cout<<"PASS: end-of-stream loops local audio and stops cleanly\n";return 0;}
 Sleep(500);LONGLONG first=musicPosition;Sleep(500);assert(musicPosition>first);
 checkVolume(0,-10000);LONGLONG muted=musicPosition;Sleep(400);assert(musicPosition>muted);
 checkVolume(25,-1204);checkVolume(50,-602);checkVolume(100,0);
 fileMusicPause();assert(waitMusic(false));LONGLONG frozen=musicPosition;Sleep(400);assert(musicPosition==frozen);
 serviceBattleMusic();assert(waitMusic(true));
 mem<int32_t>(0x7c9cd0)=0;serviceBattleMusic();assert(waitMusic(false));assert(fileMusicTrack()==0);
 mem<int32_t>(0x7c9cd0)=1;serviceBattleMusic();assert(waitMusic(true));
 mem<uint16_t>(0x4dec90)=9;assert(waitMusic(false)); // Menu must not overlap.
 mem<uint16_t>(0x4dec90)=3;playback=true;active=true;completed=false;serviceBattleMusic();assert(waitMusic(true));
 finish();assert(waitMusic(false));serviceBattleMusic();assert(musicRequest==0);
 DeleteFileW(musicVolumePath.c_str());
 std::cout<<"PASS: real local audio playback/time progression, pause/resume, option OFF/ON, menu stop, replay start/completion stop\n";
}
