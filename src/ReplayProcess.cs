using System;
using System.IO;
using System.Text;
using System.Diagnostics;
using System.Runtime.InteropServices;
namespace Myth {
 public static class ReplayProcess {
  [DllImport("kernel32.dll",SetLastError=true)]static extern IntPtr OpenProcess(uint access,bool inherit,int pid);
  [DllImport("kernel32.dll",SetLastError=true)]static extern IntPtr VirtualAllocEx(IntPtr process,IntPtr address,UIntPtr size,uint allocation,uint protect);
  [DllImport("kernel32.dll",SetLastError=true)]static extern bool VirtualFreeEx(IntPtr process,IntPtr address,UIntPtr size,uint type);
  [DllImport("kernel32.dll",SetLastError=true)]static extern bool WriteProcessMemory(IntPtr process,IntPtr address,byte[] bytes,UIntPtr size,out UIntPtr written);
  [DllImport("kernel32.dll",CharSet=CharSet.Ansi)]static extern IntPtr GetProcAddress(IntPtr module,string name);
  [DllImport("kernel32.dll",CharSet=CharSet.Unicode)]static extern IntPtr GetModuleHandle(string name);
  [DllImport("kernel32.dll",SetLastError=true)]static extern IntPtr CreateRemoteThread(IntPtr process,IntPtr attributes,UIntPtr stack,IntPtr start,IntPtr argument,uint flags,IntPtr threadId);
  [DllImport("kernel32.dll")]static extern uint WaitForSingleObject(IntPtr handle,uint timeout);
  [DllImport("kernel32.dll")]static extern bool GetExitCodeThread(IntPtr thread,out uint code);
  [DllImport("kernel32.dll")]static extern bool CloseHandle(IntPtr handle);
  public static Process Start(string executable,string engine,string session,bool playback,string mode=null) {
   if(IntPtr.Size!=4)throw new InvalidOperationException("Replay helper must be x86.");
   executable=Path.GetFullPath(executable);engine=Path.GetFullPath(engine);session=Path.GetFullPath(session);
   Directory.CreateDirectory(session);
   var settings=Core.Load();Core.SaveMusicVolume(settings.MusicVolume);
   var start=new ProcessStartInfo(executable){WorkingDirectory=Path.GetDirectoryName(executable),UseShellExecute=false};
   start.EnvironmentVariables["MYTH_REPLAY_DIR"]=session;start.EnvironmentVariables["MYTH_REPLAY_MODE"]=mode??(playback?"play":"record");
   start.EnvironmentVariables["MYTH_MUSIC_VOLUME_FILE"]=Core.MusicVolumeFile;
   string keys="";try{keys=Hotkeys.Engine(settings.KeyBindings);}catch(FormatException ex){Core.Log("단축키 설정 무시: "+ex.Message);}
   start.EnvironmentVariables["MYTH_KEYMAP"]=keys;start.EnvironmentVariables["MYTH_HERO_BAR"]=settings.HeroBar?"1":"0";start.EnvironmentVariables["MYTH_CLIP_CURSOR"]=settings.ClipCursor?"1":"0";
   var process=Process.Start(start);
   // The game is still in its menu; attach before a battle can run.
   try{if(!process.WaitForInputIdle(15000))throw new IOException("게임 초기화 시간을 초과했습니다.");Inject(process,engine);return process;}
   catch{try{if(!process.HasExited)process.CloseMainWindow();}catch{}throw;}
  }
  static void Inject(Process process,string engine){
   IntPtr handle=OpenProcess(0x43a,false,process.Id),remote=IntPtr.Zero,thread=IntPtr.Zero;
   if(handle==IntPtr.Zero)throw new IOException("리플레이 엔진 연결 실패: "+Marshal.GetLastWin32Error());
   bool completed=false;
   try {
    byte[] path=Encoding.Unicode.GetBytes(engine+"\0");UIntPtr written;
    remote=VirtualAllocEx(handle,IntPtr.Zero,(UIntPtr)path.Length,0x3000,4);
    if(remote==IntPtr.Zero||!WriteProcessMemory(handle,remote,path,(UIntPtr)path.Length,out written)||written.ToUInt32()!=path.Length)throw new IOException("리플레이 엔진 경로 전달 실패");
    thread=CreateRemoteThread(handle,IntPtr.Zero,UIntPtr.Zero,GetProcAddress(GetModuleHandle("kernel32.dll"),"LoadLibraryW"),remote,0,IntPtr.Zero);
    if(thread==IntPtr.Zero)throw new IOException("리플레이 엔진 시작 실패");
    if(WaitForSingleObject(thread,15000)!=0)throw new IOException("리플레이 엔진 응답 시간 초과");
    completed=true;uint result;
    if(!GetExitCodeThread(thread,out result)||result==0)throw new IOException("리플레이 엔진이 실행 파일 또는 세션을 거부했습니다.");
   }finally{if(thread!=IntPtr.Zero)CloseHandle(thread);if(remote!=IntPtr.Zero&&(thread==IntPtr.Zero||completed))VirtualFreeEx(handle,remote,UIntPtr.Zero,0x8000);CloseHandle(handle);}
  }
 }
}
