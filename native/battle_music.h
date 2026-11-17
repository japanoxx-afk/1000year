// Local MP3 replacement for the obsolete CD/_inmm battlefield music path.
// COM and decoding stay on a dedicated thread, outside the loader lock.
std::wstring battleMusicPath;
std::wstring musicVolumePath;
volatile LONG musicPercent=100,musicDecibels=0;
long musicAttenuation(int percent){return percent<=0?-10000:(long)std::lround(2000.0*std::log10(std::min(percent,100)/100.0));}
int readMusicVolume(){
 if(musicVolumePath.empty())return 100;
 HANDLE file=CreateFileW(musicVolumePath.c_str(),GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,nullptr,OPEN_EXISTING,0,nullptr);
 if(file==INVALID_HANDLE_VALUE)return musicPercent;
 char text[32]{};DWORD n=0;BOOL ok=ReadFile(file,text,sizeof(text)-1,&n,nullptr);CloseHandle(file);
 if(!ok||!n||n==sizeof(text)-1)return musicPercent;
 char* end=nullptr;long value=strtol(text,&end,10);if(end==text)return musicPercent;
 while(*end==' '||*end=='\r'||*end=='\n'||*end=='\t')++end;
 return *end?musicPercent:(int)std::max(0L,std::min(100L,value));
}
volatile LONG musicRequest=0,musicThreadStarted=0;
volatile LONG musicPlaying=0,musicError=0,musicLoops=0;
volatile LONGLONG musicPosition=0;
bool musicAvailable=false;
DWORD WINAPI musicWorker(void*){
 HRESULT initialized=CoInitializeEx(nullptr,COINIT_APARTMENTTHREADED);
 if(FAILED(initialized)){InterlockedExchange(&musicError,initialized);return 0;}
 if(musicVolumePath.empty()){wchar_t volumeFile[32768];DWORD n=GetEnvironmentVariableW(L"MYTH_MUSIC_VOLUME_FILE",volumeFile,32768);if(n&&n<32768)musicVolumePath=volumeFile;}
 IGraphBuilder* graph=nullptr;IMediaControl* control=nullptr;IMediaSeeking* seeking=nullptr;IMediaEvent* events=nullptr;IBasicAudio* audio=nullptr;
 LONG previous=-1;DWORD lastReport=0;
 for(;;){
  LONG requested=InterlockedCompareExchange(&musicRequest,0,0);
  uint16_t state=mem<uint16_t>(0x4dec90);
  if(state!=3&&state!=22&&state!=23)requested=0;
  if(!mem<int32_t>(0x7c9cd0))requested=0;
  if(requested&& !graph){
   HRESULT hr=CoCreateInstance(CLSID_FilterGraph,nullptr,CLSCTX_INPROC_SERVER,IID_IGraphBuilder,(void**)&graph);
   if(SUCCEEDED(hr))hr=graph->RenderFile(battleMusicPath.c_str(),nullptr);
   if(SUCCEEDED(hr))hr=graph->QueryInterface(IID_IMediaControl,(void**)&control);
   if(SUCCEEDED(hr))hr=graph->QueryInterface(IID_IMediaSeeking,(void**)&seeking);
   if(SUCCEEDED(hr))hr=graph->QueryInterface(IID_IMediaEvent,(void**)&events);
   if(SUCCEEDED(hr))hr=graph->QueryInterface(IID_IBasicAudio,(void**)&audio);
   InterlockedExchange(&musicError,hr);
   if(FAILED(hr)){if(audio){audio->Release();audio=nullptr;}if(events){events->Release();events=nullptr;}if(seeking){seeking->Release();seeking=nullptr;}if(control){control->Release();control=nullptr;}if(graph){graph->Release();graph=nullptr;}Sleep(2000);continue;}
   previous=-1;
  }
  if(audio){int percent=readMusicVolume();long db=musicAttenuation(percent);HRESULT hr=audio->put_Volume(db);if(SUCCEEDED(hr)){long applied=0;audio->get_Volume(&applied);InterlockedExchange(&musicDecibels,applied);InterlockedExchange(&musicPercent,percent);}else InterlockedExchange(&musicError,hr);}
  if(control&&requested!=previous){
   HRESULT hr=requested==1?control->Run():requested==2?control->Pause():control->Stop();
   InterlockedExchange(&musicError,hr);previous=requested;
  }
  if(seeking&&requested==1){
   LONGLONG position=0,duration=0;seeking->GetCurrentPosition(&position);seeking->GetDuration(&duration);
   InterlockedExchange64(&musicPosition,position);
   bool ended=duration>0&&position>=duration;long event=0;LONG_PTR first=0,second=0;
   while(events&&SUCCEEDED(events->GetEvent(&event,&first,&second,0))){if(event==EC_COMPLETE)ended=true;events->FreeEventParams(event,first,second);}
   if(ended){LONGLONG start=0;seeking->SetPositions(&start,AM_SEEKING_AbsolutePositioning,nullptr,AM_SEEKING_NoPositioning);control->Run();InterlockedIncrement(&musicLoops);}
  }
  OAFilterState actual=State_Stopped;
  if(control)control->GetState(0,&actual);
  InterlockedExchange(&musicPlaying,actual==State_Running);
  if(!requested&&graph){audio->Release();audio=nullptr;events->Release();events=nullptr;seeking->Release();seeking=nullptr;control->Release();control=nullptr;graph->Release();graph=nullptr;previous=-1;InterlockedExchange64(&musicPosition,0);}
  // Diagnostic state is separate from replay recording/completion status.
  if(GetTickCount()-lastReport>=2000){lastReport=GetTickCount();FILE* report=_wfopen((root+L"\\music-status.txt").c_str(),L"wb");
   if(report){fprintf(report,"request=%ld playing=%ld result=%08lx position100ns=%lld loops=%ld volume=%ld%% attenuation=%ld\n",requested,musicPlaying,(unsigned long)musicError,musicPosition,musicLoops,musicPercent,musicDecibels);fclose(report);}}
  Sleep(200);
 }
}
void requestMusic(LONG request){
 InterlockedExchange(&musicRequest,request);
 if(request&&InterlockedCompareExchange(&musicThreadStarted,1,0)==0){
  HANDLE thread=CreateThread(nullptr,0,musicWorker,nullptr,0,nullptr);
  if(thread)CloseHandle(thread);else{InterlockedExchange(&musicError,HRESULT_FROM_WIN32(GetLastError()));InterlockedExchange(&musicThreadStarted,0);}
 }
}
int __cdecl fileMusicPlay(int /*track*/,int /*loop*/){
 if(!mem<int32_t>(0x7c9cd0))return 1;
 mem<int32_t>(0x6c54a4)=2;mem<int32_t>(0x6c5494)=1;mem<int32_t>(0x6c5498)=0;
 requestMusic(1);return 1;
}
int __cdecl fileMusicStop(){requestMusic(0);mem<int32_t>(0x6c5494)=0;mem<int32_t>(0x6c5498)=0;return 1;}
int __cdecl fileMusicPause(){requestMusic(2);mem<int32_t>(0x6c5494)=0;mem<int32_t>(0x6c5498)=1;return 1;}
int __cdecl fileMusicTrack(){return musicRequest?2:0;}
void serviceBattleMusic(){
 if(!musicAvailable)return;
 uint16_t state=mem<uint16_t>(0x4dec90);bool battle=state==3||state==22||state==23;
 if(!battle||!mem<int32_t>(0x7c9cd0)||(playback&&(completed||failed))){if(musicRequest)fileMusicStop();return;}
 // Replay checkpoint loading bypasses the original CD-start call. This also
 // resumes after the native focus-pause path without restarting the track.
 if(musicRequest!=1)fileMusicPlay(2,1);
}
