using System;
using System.Drawing;
using System.Windows.Forms;
using System.IO;
using System.Diagnostics;
using System.Net;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
namespace Myth {
 static class Program {
  [System.Runtime.InteropServices.DllImport("user32.dll")]static extern bool SetProcessDPIAware();
  [STAThread] static void Main(string[] args) {bool branded=args.Length==1&&args[0]=="--branded";if((args.Length==0||branded)&&Branding.Apply(Application.ExecutablePath,branded))return;if(args.Length==3&&args[0]=="--replay-watch"){Replays.Watch(Int32.Parse(args[1]),args[2]);return;}SetProcessDPIAware();Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);if(args.Length==2&&args[0]=="--replay"){try{var settings=Core.Load();string game=String.IsNullOrWhiteSpace(settings.GameDirectory)?Core.Home:settings.GameDirectory;Application.Run(Replays.Play(Path.GetFullPath(args[1]),game,settings.Fullscreen,false));}catch(Exception ex){MessageBox.Show(ex.Message,"리플레이 실행 실패");}return;}bool created;using(var mutex=new Mutex(true,"Local\\1000year-Launcher",out created)){if(!created){MessageBox.Show("런처가 이미 실행 중입니다.");return;}Application.Run(new Launcher());}}
 }
 public sealed class Launcher:Form {
  static readonly int[] ModeOrder={0,4,1,2,3};
  int SelectedMode{get{return ModeOrder[Math.Max(0,mode.SelectedIndex)];}}
  Settings settings=Core.Load();TextBox path;ComboBox mode;CheckBox full,stretch,heroBar,clip,auto,record;TrackBar musicVolume;Label musicLevel,status;Button play,update,replays,hotkeys,editor;bool busy;FileSystemWatcher replayWatcher;CancellationTokenSource stop=new CancellationTokenSource();
  public Launcher() {
   Text="천년의신화 런처 · "+Core.Version;try{Icon=Icon.ExtractAssociatedIcon(Application.ExecutablePath);}catch{}ClientSize=new Size(720,680);MinimumSize=Size;MaximumSize=Size;StartPosition=FormStartPosition.CenterScreen;BackColor=Color.FromArgb(23,29,35);ForeColor=Color.FromArgb(236,229,214);Font=new Font("맑은 고딕",10);
   Controls.Add(new Label{Text="천년의신화",Font=new Font("맑은 고딕",27,FontStyle.Bold),Location=new Point(30,22),Size=new Size(480,58)});
   Controls.Add(new Label{Text="MILLENNIUM MYTH  /  V1.070KR",ForeColor=Color.FromArgb(190,157,98),Location=new Point(34,84),Size=new Size(500,25)});
   Controls.Add(new Label{Text="게임 설치 폴더",Location=new Point(34,126),Size=new Size(200,24)});
   path=new TextBox{Location=new Point(34,156),Size=new Size(550,30),Text=settings.GameDirectory};Controls.Add(path);
   var browse=Button("찾아보기",594,153,94);browse.Click+=(s,e)=>{using(var dlg=new FolderBrowserDialog{Description="MMyth.exe가 있는 폴더를 선택하세요.",SelectedPath=path.Text}){if(dlg.ShowDialog()==DialogResult.OK)path.Text=dlg.SelectedPath;}};
   if(String.IsNullOrWhiteSpace(path.Text)){var guess=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),"Downloads","DGGL","Games","MMyth107_Win_231023");path.Text=File.Exists(Path.Combine(Core.Home,"MMyth.exe"))?Core.Home:guess;}
   Controls.Add(new Label{Text="화면 설정",Location=new Point(34,205),Size=new Size(180,24)});
   mode=new ComboBox{DropDownStyle=ComboBoxStyle.DropDownList,Location=new Point(34,236),Size=new Size(380,32)};mode.Items.AddRange(new object[]{"640 × 480 · 원본 해상도","800 × 600 · 내부 해상도","1024 × 768 · 화면 확대 (기존 시야)","1024 × 768 · 내부 해상도 (넓은 전장)","1280 × 720 · 16:9 내부 해상도"});mode.SelectedIndex=Math.Max(0,Array.IndexOf(ModeOrder,Math.Max(0,Math.Min(4,settings.Mode))));Controls.Add(mode);
   full=new CheckBox{Text="전체 화면",Location=new Point(438,238),Size=new Size(260,28),Checked=settings.Fullscreen};Controls.Add(full);
   stretch=new CheckBox{Text="화면 꽉 채우기 (검은 여백 없이 늘리기)",Location=new Point(438,272),Size=new Size(270,28),Checked=settings.Stretch};Controls.Add(stretch);
   heroBar=new CheckBox{Text="영웅 초상화 표시 (클릭하면 영웅 위치로 이동)",Location=new Point(34,272),Size=new Size(390,28),Checked=settings.HeroBar};Controls.Add(heroBar);
   clip=new CheckBox{Text="전투 중 마우스를 게임 창 안에 가두기 (Alt+Tab으로 해제)",Location=new Point(34,306),Size=new Size(560,28),Checked=settings.ClipCursor};Controls.Add(clip);
   auto=new CheckBox{Text="런처 시작 시 자동 업데이트",Location=new Point(34,354),Size=new Size(330,28),Checked=settings.AutoUpdate};Controls.Add(auto);
   var restore=Button("원래 그래픽 복원",438,352,250);restore.Click+=(s,e)=>{try{Core.RestoreGraphics(path.Text);Say("원래 그래픽 파일로 복원했습니다. 런처 실행 시 호환 설정이 다시 적용됩니다.");}catch(Exception ex){Say(ex.Message);}};
   play=Button("게임 시작",34,403,270);play.Height=52;play.BackColor=Color.FromArgb(162,119,54);play.Font=new Font(Font,FontStyle.Bold);play.Click+=(s,e)=>Launch();
   update=Button("업데이트 확인",320,403,176);update.Height=52;update.Click+=async(s,e)=>await CheckUpdate();
   var notes=Button("패치노트",512,403,176);notes.Height=52;notes.Click+=(s,e)=>Process.Start(new ProcessStartInfo("https://github.com/japanoxx-afk/1000year/releases"){UseShellExecute=true});
   record=new CheckBox{Text="경기 리플레이 기록",Location=new Point(34,472),Size=new Size(200,30),Checked=settings.RecordReplay};Controls.Add(record);
   hotkeys=Button("단축키 설정",250,469,176);hotkeys.Click+=(s,e)=>{using(var dialog=new HotkeyDialog(settings.KeyBindings)){if(dialog.ShowDialog(this)==DialogResult.OK){settings.KeyBindings=dialog.Bindings;Save();Say(String.IsNullOrEmpty(settings.KeyBindings)?"기본 단축키를 사용합니다.":"단축키를 저장했습니다. 다음 게임 실행부터 적용됩니다.");}}};
   replays=Button("리플레이 목록",438,469,124);
   editor=Button("맵 에디터",568,469,120);editor.Click+=(s,e)=>OpenEditor();replays.Click+=(s,e)=>new ReplayLibrary(path.Text,full.Checked).Show(this);
   Controls.Add(new Label{Text="전장 배경음악 음량",Location=new Point(34,525),Size=new Size(180,28)});
   musicVolume=new TrackBar{Minimum=0,Maximum=100,TickFrequency=10,SmallChange=5,LargeChange=10,Value=Math.Max(0,Math.Min(100,settings.MusicVolume)),Location=new Point(210,519),Size=new Size(400,45),BackColor=BackColor,AccessibleName="전장 배경음악 음량"};Controls.Add(musicVolume);
   musicLevel=new Label{Text=musicVolume.Value+"%",Location=new Point(625,525),Size=new Size(64,28)};Controls.Add(musicLevel);
   Controls.Add(new Label{Text="0%: 음소거 · 실행 중인 게임과 리플레이에도 바로 적용",Location=new Point(34,565),Size=new Size(654,25),ForeColor=Color.FromArgb(189,198,205)});
   status=new Label{Text="단축키: . 쉬는 일꾼 / ` 군사 유닛 / Tab 영웅 전체 선택 · 단축키 설정에서 바꿀 수 있습니다",Location=new Point(34,610),Size=new Size(654,60),ForeColor=Color.FromArgb(189,198,205)};Controls.Add(status);
   musicVolume.ValueChanged+=(s,e)=>{musicLevel.Text=musicVolume.Value+"%";Save();};
   Directory.CreateDirectory(Replays.Library);replayWatcher=new FileSystemWatcher(Replays.Library,"*.mythreplay");replayWatcher.Created+=(s,e)=>{if(!IsDisposed&&IsHandleCreated)try{BeginInvoke((Action)(()=>Say("리플레이 자동 저장 완료: "+e.Name)));}catch(InvalidOperationException){}};replayWatcher.EnableRaisingEvents=true;
   Shown+=async(s,e)=>{try{ReplayAssociation.Register();}catch(Exception ex){Core.Log("리플레이 파일 연결 실패: "+ex.Message);}await Task.Run(()=>Replays.Recover());if(!IsDisposed&&auto.Checked)await CheckUpdate();};FormClosing+=(s,e)=>{if(busy){e.Cancel=true;return;}Save();stop.Cancel();replayWatcher.Dispose();};
  }
  Button Button(string text,int x,int y,int width) {var b=new Button{Text=text,Location=new Point(x,y),Size=new Size(width,34),FlatStyle=FlatStyle.Flat,BackColor=Color.FromArgb(44,54,64),ForeColor=ForeColor};Controls.Add(b);return b;}
  void Save(){settings.GameDirectory=path.Text;settings.Mode=SelectedMode;settings.Fullscreen=full.Checked;settings.Stretch=stretch.Checked;settings.HeroBar=heroBar.Checked;settings.ClipCursor=clip.Checked;settings.AutoUpdate=auto.Checked;settings.RecordReplay=record.Checked;settings.MusicVolume=musicVolume.Value;try{Core.Save(settings);}catch(Exception ex){Core.Log(ex.ToString());}}
  void Say(string s){status.Text=s;Core.Log(s);}
  void SetBusy(bool b){busy=b;play.Enabled=update.Enabled=replays.Enabled=hotkeys.Enabled=editor.Enabled=!b;path.Enabled=mode.Enabled=full.Enabled=stretch.Enabled=heroBar.Enabled=clip.Enabled=record.Enabled=!b;}
  void Launch(){try{Save();if(Core.GameRunning(path.Text))throw new IOException("선택한 폴더의 게임이 이미 실행 중입니다.");string exe=Core.Prepare(path.Text,SelectedMode,full.Checked,null,stretch.Checked);if(record.Checked)Replays.Record(exe,SelectedMode,message=>{Core.Log(message);if(!IsDisposed&&IsHandleCreated)BeginInvoke((Action)(()=>Say(message)));});else Replays.PlayGame(exe);Say(record.Checked?"게임을 실행했습니다. 게임 종료 시 첫 경기의 리플레이를 저장합니다.":"게임을 실행했습니다. 설정은 다음 실행부터 적용됩니다.");}catch(Exception ex){Say("실행 실패: "+ex.Message);MessageBox.Show(this,ex.Message,"게임 실행",MessageBoxButtons.OK,MessageBoxIcon.Warning);}}
  void OpenEditor(){try{Save();string exe=Core.PrepareEditor(path.Text);Process.Start(new ProcessStartInfo(exe){WorkingDirectory=Path.GetDirectoryName(exe),UseShellExecute=false});Say("맵 에디터를 실행했습니다.");}catch(Exception ex){Say("맵 에디터 실행 실패: "+ex.Message);MessageBox.Show(this,ex.Message,"맵 에디터",MessageBoxButtons.OK,MessageBoxIcon.Warning);}}
  async Task CheckUpdate(){if(busy)return;SetBusy(true);Save();try{if(Core.GameRunning(path.Text)){Say("게임 종료 후 업데이트를 확인하세요.");return;}Say("최신 버전을 확인하고 있습니다…");ServicePointManager.SecurityProtocol=SecurityProtocolType.Tls12;using(var client=new HttpClient()){client.DefaultRequestHeaders.UserAgent.ParseAdd("1000year-Launcher/"+Core.Version);string session=Path.Combine(Core.UserHome,"Updates",Guid.NewGuid().ToString("N"));string package=await Updates.Prepare(client,Core.Version,session,r=>true,Say,stop.Token);if(package!=null){await Updates.StartInstaller(package,Core.Home,Path.GetFileName(Application.ExecutablePath),Process.GetCurrentProcess().Id,stop.Token);SetBusy(false);Application.Exit();}}}catch(Exception ex){Say("업데이트 확인 실패 · 게임은 실행할 수 있습니다. "+ex.Message);}finally{SetBusy(false);}}
 }
}


