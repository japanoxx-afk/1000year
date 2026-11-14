using System;
using System.IO;
using System.Diagnostics;
using System.Linq;
using System.Collections.Generic;
using System.Drawing;
using System.Windows.Forms;
using System.Web.Script.Serialization;
namespace Myth {
 public static class Replays {
  public static string Library=Path.Combine(Core.UserHome,"Replays");
  public static string[] LibraryFiles(string game){
   var files=new List<string>();var seen=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
   foreach(string dir in new[]{Library,Path.Combine(Path.GetFullPath(game),"Replays")}.Distinct(StringComparer.OrdinalIgnoreCase)){
    if(!Directory.Exists(dir))continue;
    try{foreach(string file in Directory.GetFiles(dir)){if(!String.Equals(Path.GetExtension(file),".mythreplay",StringComparison.OrdinalIgnoreCase))continue;
     string key;try{key=Core.Hash(file);}catch(IOException){key=Path.GetFullPath(file);}catch(UnauthorizedAccessException){key=Path.GetFullPath(file);}
     if(seen.Add(key))files.Add(file);
    }}catch(IOException ex){Core.Log("리플레이 목록 확인 필요: "+dir+" · "+ex.Message);}catch(UnauthorizedAccessException ex){Core.Log("리플레이 목록 확인 필요: "+dir+" · "+ex.Message);}
   }return files.OrderByDescending(Path.GetFileName,StringComparer.OrdinalIgnoreCase).ToArray();
  }
  static string Session(){string dir=Path.Combine(Core.UserHome,"R",Guid.NewGuid().ToString("N").Substring(0,12));Directory.CreateDirectory(dir);return dir;}
  static string Engine(){byte[] bytes=Core.Resource("Myth.ReplayEngine");string dir=Path.Combine(Core.UserHome,"Engine",Core.HashBytes(bytes).Substring(0,12));Directory.CreateDirectory(dir);string path=Path.Combine(dir,"MythReplay.dll");if(!File.Exists(path)||Core.Hash(path)!=Core.HashBytes(bytes))File.WriteAllBytes(path,bytes);return path;}
  public static Process Record(string executable,int mode,Action<string> notice){
   string session=Session(),engine=Engine();
   var info=new ReplayInfo{Mode=mode,RecordedAt=DateTime.UtcNow.ToString("o"),GameSHA256=Core.Hash(Path.Combine(Path.GetDirectoryName(executable),"MMyth.exe")),PatchSHA256=Core.Hash(executable),EngineSHA256=Core.Hash(engine)};
   File.WriteAllText(Path.Combine(session,"identity.json"),new JavaScriptSerializer().Serialize(info));
   Process game=ReplayProcess.Start(executable,engine,session,false);
   Process.Start(new ProcessStartInfo(Application.ExecutablePath,"--replay-watch "+game.Id+" \""+session+"\""){UseShellExecute=false,CreateNoWindow=true,WindowStyle=ProcessWindowStyle.Hidden});
   notice("리플레이 기록 준비 완료");return game;
  }
  public static void Watch(int pid,string session){try{
   string allowed=Path.GetFullPath(Path.Combine(Core.UserHome,"R"))+Path.DirectorySeparatorChar;session=Path.GetFullPath(session);
   if(!session.StartsWith(allowed,StringComparison.OrdinalIgnoreCase))throw new IOException("리플레이 세션 경로 오류");
   try{using(var p=Process.GetProcessById(pid)){if(!p.ProcessName.StartsWith("MMyth",StringComparison.OrdinalIgnoreCase))throw new IOException("리플레이 게임 프로세스 오류");while(!p.WaitForExit(500)){string f=Path.Combine(session,"status.txt");if(File.Exists(f)&&File.ReadAllText(f)=="COMPLETE")break;}}}catch(ArgumentException){}
   Publish(session);
  }catch(Exception ex){Core.Log("리플레이 저장 확인 필요: "+ex);}}
  public static string Publish(string session){
   string allowed=Path.GetFullPath(Path.Combine(Core.UserHome,"R"))+Path.DirectorySeparatorChar;session=Path.GetFullPath(session);
   if(!session.StartsWith(allowed,StringComparison.OrdinalIgnoreCase))throw new IOException("리플레이 세션 경로 오류");
   using(var publishLock=new FileStream(Path.Combine(session,"publish.lock"),FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None)){
   string status=Path.Combine(session,"status.txt");if(!File.Exists(status)||File.ReadAllText(status)!="COMPLETE")throw new IOException("정상 종료되지 않은 기록을 보존했습니다: "+session);
   var info=new JavaScriptSerializer().Deserialize<ReplayInfo>(File.ReadAllText(Path.Combine(session,"identity.json")));
   Directory.CreateDirectory(Library);string target=Path.Combine(Library,DateTime.Parse(info.RecordedAt).ToLocalTime().ToString("yyyyMMdd-HHmmss")+"-"+Path.GetFileName(session)+".mythreplay");
   if(File.Exists(target)){var existing=ReplayArchive.Read(target,null);if(existing.CommandsSHA256!=Core.Hash(Path.Combine(session,"commands.partial")))throw new IOException("기존 리플레이와 기록이 다릅니다.");return target;}
   ReplayArchive.Create(target,session,info);Core.Log("리플레이 저장 완료: "+target);return target;
   }
  }
  public static void Recover(){string root=Path.Combine(Core.UserHome,"R");if(!Directory.Exists(root))return;foreach(string session in Directory.GetDirectories(root)){try{string status=Path.Combine(session,"status.txt");if(File.Exists(Path.Combine(session,"identity.json"))&&File.Exists(Path.Combine(session,"commands.partial"))&&File.Exists(status)&&File.ReadAllText(status)=="COMPLETE")Publish(session);}catch(Exception ex){Core.Log("리플레이 복구 확인 필요: "+ex.Message);}}}
  public static ReplayControls Play(string file,string directory,bool fullscreen,bool show=true){
   if(Core.GameRunning(directory))throw new IOException("게임을 종료한 뒤 리플레이를 재생하세요.");
   string session=Session();ReplayInfo info=ReplayArchive.Read(file,session);string engine=Engine();
   string exe=Core.Prepare(directory,info.Mode,fullscreen,info.PatchSHA256);
   if(Core.Hash(Path.Combine(directory,"MMyth.exe"))!=info.GameSHA256||Core.Hash(exe)!=info.PatchSHA256||info.Rules!=1)throw new IOException("현재 게임·패치·리플레이 규칙이 기록과 다릅니다.");
   var process=ReplayProcess.Start(exe,engine,session,true);
   var controls=new ReplayControls(process,session,info);if(show)controls.Show();return controls;
  }
 }
 public sealed class ReplayLibrary:Form {
  ListBox list=new ListBox();Label detail=new Label(),location=new Label();Timer refreshTimer=new Timer();string directory;bool fullscreen;string[] listed=new string[0];
  public ReplayLibrary(string game,bool full){
   directory=game;fullscreen=full;Text="천년의신화 리플레이";ClientSize=new Size(760,440);StartPosition=FormStartPosition.CenterParent;Font=new Font("맑은 고딕",10);
   list.SetBounds(20,20,720,220);Controls.Add(list);location.SetBounds(20,250,720,45);Controls.Add(location);detail.SetBounds(20,300,720,55);Controls.Add(detail);
   var play=new Button{Text="재생",Bounds=new Rectangle(20,380,160,40)};Controls.Add(play);
   var open=new Button{Text="파일 열기",Bounds=new Rectangle(195,380,160,40)};Controls.Add(open);
   var folder=new Button{Text="저장 폴더",Bounds=new Rectangle(370,380,160,40)};Controls.Add(folder);
   var refresh=new Button{Text="새로고침",Bounds=new Rectangle(545,380,160,40)};Controls.Add(refresh);
   refresh.Click+=(s,e)=>RefreshLibrary(true);
   Directory.CreateDirectory(Replays.Library);
   list.Format+=(s,e)=>e.Value=Path.GetFileName(Convert.ToString(e.ListItem));list.FormattingEnabled=true;
   list.SelectedIndexChanged+=(s,e)=>{try{var i=ReplayArchive.Read((string)list.SelectedItem,null);detail.Text=DateTime.Parse(i.RecordedAt).ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss")+"\r\n"+((long)(i.LastTick-i.FirstTick)*i.TickMilliseconds/1000)+"초 · 명령 플레이어 "+i.Players.Length+"명";}catch(Exception ex){detail.Text=ex.Message;}};
   play.Click+=(s,e)=>{if(list.SelectedItem!=null)Start((string)list.SelectedItem);};
   list.DoubleClick+=(s,e)=>{if(list.SelectedItem!=null)Start((string)list.SelectedItem);};
   open.Click+=(s,e)=>{using(var d=new OpenFileDialog{Filter="천년의신화 리플레이|*.mythreplay",InitialDirectory=Replays.Library})if(d.ShowDialog(this)==DialogResult.OK)Start(d.FileName);};
   folder.Click+=(s,e)=>Process.Start(new ProcessStartInfo(Replays.Library){UseShellExecute=true});
   RefreshLibrary(true);refreshTimer.Interval=2000;refreshTimer.Tick+=(s,e)=>RefreshLibrary(false);refreshTimer.Start();
   Activated+=(s,e)=>RefreshLibrary(false);FormClosed+=(s,e)=>refreshTimer.Dispose();
  }
  public void RefreshLibrary(bool recover){
   try{
    if(recover)Replays.Recover();string[] files=Replays.LibraryFiles(directory);
    location.Text="저장된 리플레이 "+files.Length+"개 · 자동 갱신\r\n"+Replays.Library;
    if(!listed.SequenceEqual(files,StringComparer.OrdinalIgnoreCase)){
     string selected=list.SelectedItem as string;list.BeginUpdate();try{list.Items.Clear();list.Items.AddRange(files);listed=files;int index=selected==null?-1:Array.FindIndex(files,f=>String.Equals(f,selected,StringComparison.OrdinalIgnoreCase));if(files.Length>0)list.SelectedIndex=index<0?0:index;}finally{list.EndUpdate();}
    }
    if(files.Length==0)detail.Text="이 저장 폴더와 게임 폴더의 Replays에서 기록을 찾지 못했습니다. 파일 열기로 다른 위치의 기록을 선택할 수 있습니다.";
   }catch(Exception ex){detail.Text="목록을 갱신하지 못했습니다: "+ex.Message;Core.Log(detail.Text);}
  }
  void Start(string file){try{Replays.Play(file,directory,fullscreen);}catch(Exception ex){MessageBox.Show(this,ex.Message,"재생 실패");}}
 }
 public sealed class ReplayControls:Form {
  [System.Runtime.InteropServices.DllImport("user32.dll")]static extern bool SetForegroundWindow(IntPtr window);
  Process game;string session;Label state=new Label();Timer timer=new Timer();bool syncingSpeed;
  void SyncSpeed(ComboBox combo){string file=Path.Combine(session,"control.txt");if(!File.Exists(file))return;string value=File.ReadAllText(file);int index=value=="speed1.5"||value=="speed1"?0:value=="speed2"?1:value=="speed4"?2:-1;if(index>=0&&combo.SelectedIndex!=index){syncingSpeed=true;try{combo.SelectedIndex=index;}finally{syncingSpeed=false;}}}
  public ReplayControls(Process process,string work,ReplayInfo info){game=process;session=work;Text="리플레이 재생";ClientSize=new Size(540,210);Font=new Font("맑은 고딕",10);
   state.SetBounds(16,12,510,65);state.Text="저장된 경기를 불러오고 있습니다.";Controls.Add(state);
   int x=16;foreach(string command in new[]{"play","pause","step"}){string value=command;var b=new Button{Text=command=="play"?"재생":command=="pause"?"일시정지":"한 프레임",Bounds=new Rectangle(x,92,150,40)};Controls.Add(b);b.Click+=(s,e)=>{try{File.WriteAllText(Path.Combine(session,"control.txt"),value);if(value!="pause"&&!game.HasExited)SetForegroundWindow(game.MainWindowHandle);}catch(Exception ex){state.Text=ex.Message;}};x+=170;}
   var speed=new ComboBox{DropDownStyle=ComboBoxStyle.DropDownList,Bounds=new Rectangle(16,150,150,30)};speed.Items.AddRange(new object[]{"1.5배속 (1)","2배속 (2)","4배속 (4)"});speed.SelectedIndex=0;Controls.Add(speed);speed.SelectedIndexChanged+=(s,e)=>{if(!syncingSpeed){File.WriteAllText(Path.Combine(session,"control.txt"),speed.SelectedIndex==0?"speed1.5":"speed"+(1<<speed.SelectedIndex));if(!game.HasExited)SetForegroundWindow(game.MainWindowHandle);}};
   var close=new Button{Text="게임 닫기",Bounds=new Rectangle(186,145,150,40)};Controls.Add(close);close.Click+=(s,e)=>{if(!game.HasExited)game.CloseMainWindow();};
   timer.Interval=500;timer.Tick+=(s,e)=>{try{SyncSpeed(speed);if(game.HasExited){state.Text="게임이 종료되었습니다.";timer.Stop();return;}string f=Path.Combine(session,"status.txt");if(File.Exists(f)){string text=File.ReadAllText(f);if(text=="READY")state.Text="저장된 경기를 불러오고 있습니다.";else if(text=="COMPLETE"){timer.Stop();state.Text="리플레이 재생이 완료되었습니다.";Activate();MessageBox.Show(this,"리플레이 재생이 완료되었습니다. 확인을 누르면 게임을 종료합니다.","리플레이 종료",MessageBoxButtons.OK,MessageBoxIcon.Information);if(!game.HasExited)game.CloseMainWindow();Close();return;}else if(text.StartsWith("ERROR")){state.Text="기록과 게임 상태가 일치하지 않아 재생을 중단했습니다.";Core.Log(text);}else if(text.StartsWith("PLAYING")){string[] parts=text.Split(' ');int tick;if(parts.Length==3&&Int32.TryParse(parts[2],out tick))state.Text="재생 중 · "+((long)(tick-info.FirstTick)*info.TickMilliseconds/1000)+" / "+((long)(info.LastTick-info.FirstTick)*info.TickMilliseconds/1000)+"초";else state.Text="재생 중";}}}catch(IOException){}};timer.Start();FormClosed+=(s,e)=>timer.Dispose();
  }
 }
 public static class ReplayAssociation {
  [System.Runtime.InteropServices.DllImport("shell32.dll")]static extern void SHChangeNotify(uint action,uint flags,IntPtr first,IntPtr second);
  public static string OpenCommand(string executable){return "\""+Path.GetFullPath(executable)+"\" --replay \"%1\"";}
  public static void Register(){
   using(var extension=Microsoft.Win32.Registry.CurrentUser.CreateSubKey(@"Software\Classes\.mythreplay"))extension.SetValue("","1000year.Replay");
   using(var type=Microsoft.Win32.Registry.CurrentUser.CreateSubKey(@"Software\Classes\1000year.Replay"))type.SetValue("","천년의신화 리플레이");
   using(var command=Microsoft.Win32.Registry.CurrentUser.CreateSubKey(@"Software\Classes\1000year.Replay\shell\open\command"))command.SetValue("",OpenCommand(Path.Combine(Core.Home,"MythLauncher.exe")));
   SHChangeNotify(0x08000000,0,IntPtr.Zero,IntPtr.Zero);
  }
 }
}
