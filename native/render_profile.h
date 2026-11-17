// Isolated test-build measurements; excluded from shipped DLLs.
std::vector<uint32_t> renderTimes[3];
uintptr_t profileTerrainBase=0,profileCacheState=0;
uint64_t profileCpuStart=0;int64_t profileWallStart=0;
uint64_t profileCpu(){FILETIME created,exited,kernel,user;GetProcessTimes(GetCurrentProcess(),&created,&exited,&kernel,&user);ULARGE_INTEGER k{},u{};k.LowPart=kernel.dwLowDateTime;k.HighPart=kernel.dwHighDateTime;u.LowPart=user.dwLowDateTime;u.HighPart=user.dwHighDateTime;return k.QuadPart+u.QuadPart;}
void profileRender(unsigned part,int64_t started){
 static int64_t frequency=[](){LARGE_INTEGER f;QueryPerformanceFrequency(&f);return f.QuadPart;}();
 renderTimes[part].push_back((uint32_t)((counterNow()-started)*1000000/frequency));
 if(part!=0)return;
 if(!profileWallStart){profileCpuStart=profileCpu();profileWallStart=counterNow();}
 if(!profileTerrainBase){auto base=(uintptr_t)GetModuleHandleW(nullptr);auto nt=(IMAGE_NT_HEADERS32*)(base+((IMAGE_DOS_HEADER*)base)->e_lfanew);auto section=IMAGE_FIRST_SECTION(nt)+nt->FileHeader.NumberOfSections-1;
  if(!memcmp(section->Name,".hd",3)){profileTerrainBase=base+section->VirtualAddress+0x10000;profileCacheState=base+section->VirtualAddress+0xb000;}}
 static uint32_t lastDump=0;uint32_t tick=mem<uint32_t>(0xa6ea50);
 if(profileTerrainBase&&tick!=lastDump&&(tick==100||tick==300||tick==500||tick==700||tick==900)){
  wchar_t name[64];swprintf_s(name,L"\\terrain-%u.raw",tick);FILE* f=_wfopen((root+name).c_str(),L"wb");
  unsigned width=mem<uint32_t>(0x115e2fc),height=mem<uint32_t>(0x115e300);
  if(f){if(width*height<=0x100000)fwrite((void*)profileTerrainBase,1,width*height,f);fclose(f);}lastDump=tick;
 }
}
void profileFinish(){
 LARGE_INTEGER frequency;QueryPerformanceFrequency(&frequency);uint64_t cpu=profileCpu()-profileCpuStart;int64_t elapsed=counterNow()-profileWallStart;
 FILE* report=_wfopen((root+L"\\render-perf.txt").c_str(),L"wb");if(!report)return;
 fprintf(report,"elapsed_ms=%.3f process_cpu_ms=%.3f\n",elapsed*1000.0/frequency.QuadPart,cpu/10000.0);
 fprintf(report,"resourceMaskBuilds=%u timerMaskBuilds=%u\n",resourceMask.builds,timerMask.builds);
 for(unsigned i=0;i<3;++i){auto values=renderTimes[i];if(values.empty())continue;uint64_t sum=0;for(auto v:values)sum+=v;std::sort(values.begin(),values.end());fprintf(report,"%s calls=%u mean_us=%.3f p50_us=%u p95_us=%u\n",i==0?"fogTerrain":i==1?"resources":"timer",(unsigned)values.size(),(double)sum/values.size(),values[values.size()/2],values[values.size()*95/100]);}
 if(profileCacheState)fprintf(report,"cacheValid=%u attempts=%u redraws=%u reuses=%u yields=%u\n",mem<uint32_t>(profileCacheState),mem<uint32_t>(profileCacheState+40),mem<uint32_t>(profileCacheState+44),mem<uint32_t>(profileCacheState+48),mem<uint32_t>(profileCacheState+84));
 fclose(report);
}
