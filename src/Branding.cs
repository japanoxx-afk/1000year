using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
namespace Myth {
 // The launcher runs as MMyth_launcher_<version>.exe and shows the game's own
 // icon. The icon is copied on the player's PC from their MMyth.exe, so the
 // published launcher never redistributes game artwork. Update packages keep the
 // MythLauncher(-version).exe names that older installers require.
 public static class Branding {
  public static string FileName{get{return "MMyth_launcher_"+Core.Version+".exe";}}
  const uint LoadAsData=0x22; // data file + image resource: always the file on disk, never an already loaded module
  static readonly IntPtr IconType=(IntPtr)3,GroupType=(IntPtr)14;
  delegate bool EnumNames(IntPtr module,IntPtr type,IntPtr name,IntPtr param);
  [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]static extern IntPtr LoadLibraryEx(string path,IntPtr file,uint flags);
  [DllImport("kernel32.dll")]static extern bool FreeLibrary(IntPtr module);
  [DllImport("kernel32.dll")]static extern bool EnumResourceNames(IntPtr module,IntPtr type,EnumNames callback,IntPtr param);
  [DllImport("kernel32.dll")]static extern IntPtr FindResource(IntPtr module,IntPtr name,IntPtr type);
  [DllImport("kernel32.dll")]static extern IntPtr LoadResource(IntPtr module,IntPtr resource);
  [DllImport("kernel32.dll")]static extern IntPtr LockResource(IntPtr data);
  [DllImport("kernel32.dll")]static extern uint SizeofResource(IntPtr module,IntPtr resource);
  [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]static extern IntPtr BeginUpdateResource(string file,bool deleteExisting);
  [DllImport("kernel32.dll",SetLastError=true)]static extern bool UpdateResource(IntPtr update,IntPtr type,IntPtr name,ushort language,byte[] data,uint size);
  [DllImport("kernel32.dll",SetLastError=true)]static extern bool EndUpdateResource(IntPtr update,bool discard);
  [DllImport("shell32.dll",CharSet=CharSet.Unicode)]static extern void SHChangeNotify(int eventId,uint flags,string item1,IntPtr item2);
  // Explorer caches icons by path; announce the new icon for the rewritten file.
  static void RefreshShell(string file){try{SHChangeNotify(0x2000,0x0005,file,IntPtr.Zero);SHChangeNotify(0x08000000,0,null,IntPtr.Zero);}catch{}}
  static byte[] Read(IntPtr module,IntPtr name,IntPtr type){IntPtr r=FindResource(module,name,type);if(r==IntPtr.Zero)return null;IntPtr h=LoadResource(module,r);uint n=SizeofResource(module,r);IntPtr p=LockResource(h);if(p==IntPtr.Zero||n==0)return null;var b=new byte[n];Marshal.Copy(p,b,0,(int)n);return b;}
  static IntPtr FirstGroup(IntPtr module){IntPtr found=IntPtr.Zero;EnumResourceNames(module,GroupType,(m,t,n,p)=>{found=n;return false;},IntPtr.Zero);return found;}
  public static bool HasIcon(string exe){IntPtr m=LoadLibraryEx(exe,IntPtr.Zero,LoadAsData);if(m==IntPtr.Zero)return false;try{return FirstGroup(m)!=IntPtr.Zero;}finally{FreeLibrary(m);}}
  // Copy the first icon group (and its images) from source into target.
  public static void CopyIcon(string source,string target){
   IntPtr m=LoadLibraryEx(source,IntPtr.Zero,LoadAsData);if(m==IntPtr.Zero)throw new IOException("게임 아이콘을 읽을 수 없습니다.");
   byte[] group;var images=new List<byte[]>();
   try{
    IntPtr name=FirstGroup(m);if(name==IntPtr.Zero)throw new IOException("게임 실행 파일에 아이콘이 없습니다.");
    group=Read(m,name,GroupType);int count=group!=null&&group.Length>=6?BitConverter.ToUInt16(group,4):0;
    if(count<1||count>64||group.Length<6+14*count)throw new IOException("게임 아이콘 형식이 올바르지 않습니다.");
    for(int i=0;i<count;i++){byte[] image=Read(m,(IntPtr)BitConverter.ToUInt16(group,6+14*i+12),IconType);if(image==null)throw new IOException("게임 아이콘 이미지 누락");images.Add(image);}
   }finally{FreeLibrary(m);}
   group=(byte[])group.Clone();
   IntPtr update=BeginUpdateResource(target,false);if(update==IntPtr.Zero)throw new IOException("런처 아이콘을 쓸 수 없습니다: "+Marshal.GetLastWin32Error());
   bool ok=false;
   try{
    for(int i=0;i<images.Count;i++){ushort id=(ushort)(1001+i);BitConverter.GetBytes(id).CopyTo(group,6+14*i+12);if(!UpdateResource(update,IconType,(IntPtr)id,0,images[i],(uint)images[i].Length))throw new IOException("아이콘 이미지 쓰기 실패");}
    if(!UpdateResource(update,GroupType,(IntPtr)1,0,group,(uint)group.Length))throw new IOException("아이콘 그룹 쓰기 실패");
    ok=true;
   }finally{bool written=EndUpdateResource(update,!ok);if(ok&&!written)throw new IOException("아이콘 저장 실패: "+Marshal.GetLastWin32Error());}
  }
  static string GameExecutable(){
   try{string dir=Core.Load().GameDirectory;if(!String.IsNullOrWhiteSpace(dir)){string exe=Path.Combine(dir,"MMyth.exe");if(File.Exists(exe))return exe;}}catch{}
   string local=Path.Combine(Core.Home,"MMyth.exe");return File.Exists(local)?local:null;
  }
  // Returns true when a renamed/branded copy was started and this process should exit.
  public static bool Apply(string current,bool alreadyRestarted){
   try{
    string folder=Path.GetDirectoryName(current),desired=Path.Combine(folder,FileName);
    foreach(string old in Directory.GetFiles(folder,"MMyth_launcher_*.exe.old"))try{File.Delete(old);}catch{}
    if(alreadyRestarted)return false;
    bool named=String.Equals(Path.GetFullPath(current),Path.GetFullPath(desired),StringComparison.OrdinalIgnoreCase);
    string game=GameExecutable();
    if(named&&(game==null||HasIcon(current)))return false;
    if(!named&&File.Exists(desired)&&(game==null||HasIcon(desired))){Start(desired);return true;}
    string staged=desired+".new";File.Copy(current,staged,true);
    // A fresh executable is often held briefly by antivirus scanning; retry.
    if(game!=null){Exception last=null;for(int attempt=0;attempt<8;attempt++){try{CopyIcon(game,staged);if(HasIcon(staged)){last=null;break;}last=new IOException("아이콘 확인 실패");}catch(Exception ex){last=ex;}System.Threading.Thread.Sleep(400);}if(last!=null)Core.Log("아이콘 적용 생략: "+last.Message);}
    // A running executable can be renamed but not overwritten.
    if(named)File.Move(current,current+".old");else if(File.Exists(desired))File.Delete(desired);
    try{File.Move(staged,desired);}catch{if(named&&!File.Exists(current))File.Move(current+".old",current);throw;}
    RefreshShell(desired);Core.Log("Launcher renamed: "+desired+(game!=null?" icon="+HasIcon(desired):""));Start(desired);return true;
   }catch(Exception ex){Core.Log("런처 이름·아이콘 적용 실패: "+ex.Message);return false;}
  }
  static void Start(string exe){Process.Start(new ProcessStartInfo(exe,"--branded"){WorkingDirectory=Path.GetDirectoryName(exe),UseShellExecute=false});}
 }
}
