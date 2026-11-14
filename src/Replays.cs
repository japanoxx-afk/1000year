using System;
using System.IO;
using System.Diagnostics;
using System.Drawing;
using System.Windows.Forms;
using System.Web.Script.Serialization;
namespace Myth {
 public static class Replays {
  public static string Library=Path.Combine(Core.UserHome,"Replays");
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
   try{using(var p=Process.GetProcessById(pid)){if(!p.ProcessName.StartsWith("MMyth",StringComparison.OrdinalIgnoreCase))throw new IOException("리플레이 게임 프로세스 오류");p.WaitForExit();}}catch(ArgumentException){}
   string status=Path.Combine(session,"status.txt");if(!File.Exists(status)||File.ReadAllText(status)!="COMPLETE")throw new IOException("정상 종료되지 않은 기록을 보존했습니다: "+session);
   var info=new JavaScriptSerializer().Deserialize<ReplayInfo>(File.ReadAllText(Path.Combine(session,"identity.json")));
   Directory.CreateDirectory(Library);string target=Path.Combine(Library,DateTime.Now.ToString("yyyyMMdd-HHmmss")+"-"+Guid.NewGuid().ToString("N").Substring(0,6)+".mythreplay");
   ReplayArchive.Create(target,session,info);Core.Log("리플레이 저장 완료: "+target);
  }catch(Exception ex){Core.Log("리플레이 저장 확인 필요: "+ex);}}
  public static void Play(string file,string directory,bool fullscreen){
   if(Core.GameRunning(directory))throw new IOException("게임을 종료한 뒤 리플레이를 재생하세요.");
   string session=Session();ReplayInfo info=ReplayArchive.Read(file,session);string engine=Engine();
   string exe=Core.Prepare(directory,info.Mode,fullscreen);
   if(Core.Hash(Path.Combine(directory,"MMyth.exe"))!=info.GameSHA256||Core.Hash(exe)!=info.PatchSHA256||Core.Hash(engine)!=info.EngineSHA256)throw new IOException("현재 게임·패치·리플레이 엔진 버전이 기록과 다릅니다.");
   var process=ReplayProcess.Start(exe,engine,session,true);
   new ReplayControls(process,session,info).Show();
  }
 }
 public sealed class ReplayLibrary:Form {
  ListBox list=new ListBox();Label detail=new Label();string directory;bool fullscreen;
  public ReplayLibrary(string game,bool full){
   directory=game;fullscreen=full;Text="천년의신화 리플레이";ClientSize=new Size(660,420);StartPosition=FormStartPosition.CenterParent;Font=new Font("맑은 고딕",10);
   list.SetBounds(20,20,620,240);Controls.Add(list);detail.SetBounds(20,272,620,65);Controls.Add(detail);
   var play=new Button{Text="재생",Bounds=new Rectangle(20,350,170,40)};Controls.Add(play);
   var open=new Button{Text="파일 열기",Bounds=new Rectangle(210,350,170,40)};Controls.Add(open);
   var folder=new Button{Text="저장 폴더",Bounds=new Rectangle(400,350,170,40)};Controls.Add(folder);
   Directory.CreateDirectory(Replays.Library);var files=Directory.GetFiles(Replays.Library,"*.mythreplay");Array.Sort(files);Array.Reverse(files);list.Items.AddRange(files);
   list.Format+=(s,e)=>e.Value=Path.GetFileName(Convert.ToString(e.ListItem));list.FormattingEnabled=true;
   list.SelectedIndexChanged+=(s,e)=>{try{var i=ReplayArchive.Read((string)list.SelectedItem,null);detail.Text=DateTime.Parse(i.RecordedAt).ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss")+"\r\n"+((long)(i.LastTick-i.FirstTick)*i.TickMilliseconds/1000)+"초 · 명령 플레이어 "+i.Players.Length+"명";}catch(Exception ex){detail.Text=ex.Message;}};
   play.Click+=(s,e)=>{if(list.SelectedItem!=null)Start((string)list.SelectedItem);};
   open.Click+=(s,e)=>{using(var d=new OpenFileDialog{Filter="천년의신화 리플레이|*.mythreplay",InitialDirectory=Replays.Library})if(d.ShowDialog(this)==DialogResult.OK)Start(d.FileName);};
   folder.Click+=(s,e)=>Process.Start(new ProcessStartInfo(Replays.Library){UseShellExecute=true});
   if(list.Items.Count>0)list.SelectedIndex=0;else detail.Text="기록한 경기가 없습니다. 리플레이 기록을 켜고 게임을 시작하세요.";
  }
  void Start(string file){try{Replays.Play(file,directory,fullscreen);}catch(Exception ex){MessageBox.Show(this,ex.Message,"재생 실패");}}
 }
 public sealed class ReplayControls:Form {
  [System.Runtime.InteropServices.DllImport("user32.dll")]static extern bool SetForegroundWindow(IntPtr window);
  Process game;string session;Label state=new Label();Timer timer=new Timer();
  public ReplayControls(Process process,string work,ReplayInfo info){game=process;session=work;Text="리플레이 재생";ClientSize=new Size(540,210);Font=new Font("맑은 고딕",10);
   state.SetBounds(16,12,510,65);state.Text="저장된 경기를 불러오고 있습니다.";Controls.Add(state);
   int x=16;foreach(string command in new[]{"play","pause","step"}){string value=command;var b=new Button{Text=command=="play"?"재생":command=="pause"?"일시정지":"한 프레임",Bounds=new Rectangle(x,92,150,40)};Controls.Add(b);b.Click+=(s,e)=>{try{File.WriteAllText(Path.Combine(session,"control.txt"),value);if(value!="pause"&&!game.HasExited)SetForegroundWindow(game.MainWindowHandle);}catch(Exception ex){state.Text=ex.Message;}};x+=170;}
   var speed=new ComboBox{DropDownStyle=ComboBoxStyle.DropDownList,Bounds=new Rectangle(16,150,150,30)};speed.Items.AddRange(new object[]{"1배속","2배속","4배속","8배속"});speed.SelectedIndex=0;Controls.Add(speed);speed.SelectedIndexChanged+=(s,e)=>File.WriteAllText(Path.Combine(session,"control.txt"),"speed"+(1<<speed.SelectedIndex));
   var close=new Button{Text="게임 닫기",Bounds=new Rectangle(186,145,150,40)};Controls.Add(close);close.Click+=(s,e)=>{if(!game.HasExited)game.CloseMainWindow();};
   timer.Interval=500;timer.Tick+=(s,e)=>{try{if(game.HasExited){state.Text="게임이 종료되었습니다.";timer.Stop();return;}string f=Path.Combine(session,"status.txt");if(File.Exists(f)){string text=File.ReadAllText(f);if(text=="READY")state.Text="저장된 경기를 불러오고 있습니다.";else if(text=="COMPLETE")state.Text="리플레이 재생 완료. ‘게임 닫기’로 종료할 수 있습니다.";else if(text.StartsWith("ERROR")){state.Text="기록과 게임 상태가 일치하지 않아 재생을 중단했습니다.";Core.Log(text);}else if(text.StartsWith("PLAYING")){string[] parts=text.Split(' ');int tick;if(parts.Length==3&&Int32.TryParse(parts[2],out tick))state.Text="재생 중 · "+((long)(tick-info.FirstTick)*info.TickMilliseconds/1000)+" / "+((long)(info.LastTick-info.FirstTick)*info.TickMilliseconds/1000)+"초";else state.Text="재생 중";}}}catch(IOException){}};timer.Start();FormClosed+=(s,e)=>timer.Dispose();
  }
 }
}
