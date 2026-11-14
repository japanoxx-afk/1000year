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
  [STAThread] static void Main() {SetProcessDPIAware();Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);bool created;using(var mutex=new Mutex(true,"Local\\1000year-Launcher",out created)){if(!created){MessageBox.Show("런처가 이미 실행 중입니다.");return;}Application.Run(new Launcher());}}
 }
 public sealed class Launcher:Form {
  Settings settings=Core.Load();TextBox path;ComboBox mode;CheckBox full,auto;Label status;Button play,update;bool busy;CancellationTokenSource stop=new CancellationTokenSource();
  public Launcher() {
   Text="천년의신화 런처 · "+Core.Version;ClientSize=new Size(720,470);MinimumSize=Size;MaximumSize=Size;StartPosition=FormStartPosition.CenterScreen;BackColor=Color.FromArgb(23,29,35);ForeColor=Color.FromArgb(236,229,214);Font=new Font("맑은 고딕",10);
   Controls.Add(new Label{Text="천년의신화",Font=new Font("맑은 고딕",27,FontStyle.Bold),Location=new Point(30,22),Size=new Size(480,58)});
   Controls.Add(new Label{Text="MILLENNIUM MYTH  /  V1.070KR",ForeColor=Color.FromArgb(190,157,98),Location=new Point(34,84),Size=new Size(500,25)});
   Controls.Add(new Label{Text="게임 설치 폴더",Location=new Point(34,126),Size=new Size(200,24)});
   path=new TextBox{Location=new Point(34,156),Size=new Size(550,30),Text=settings.GameDirectory};Controls.Add(path);
   var browse=Button("찾아보기",594,153,94);browse.Click+=(s,e)=>{using(var dlg=new FolderBrowserDialog{Description="MMyth.exe가 있는 폴더를 선택하세요.",SelectedPath=path.Text}){if(dlg.ShowDialog()==DialogResult.OK)path.Text=dlg.SelectedPath;}};
   if(String.IsNullOrWhiteSpace(path.Text)){var guess=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),"Downloads","DGGL","Games","MMyth107_Win_231023");path.Text=File.Exists(Path.Combine(Core.Home,"MMyth.exe"))?Core.Home:guess;}
   Controls.Add(new Label{Text="화면 설정",Location=new Point(34,205),Size=new Size(180,24)});
   mode=new ComboBox{DropDownStyle=ComboBoxStyle.DropDownList,Location=new Point(34,236),Size=new Size(380,32)};mode.Items.AddRange(new object[]{"640 × 480 · 원본 해상도","1024 × 768 · 화면 확대 (기존 시야)","1024 × 768 · 내부 해상도 (넓은 전장)"});mode.SelectedIndex=Math.Max(0,Math.Min(2,settings.Mode));Controls.Add(mode);
   full=new CheckBox{Text="전체 화면 (4:3)",Location=new Point(438,238),Size=new Size(260,28),Checked=settings.Fullscreen};Controls.Add(full);
   auto=new CheckBox{Text="런처 시작 시 자동 업데이트",Location=new Point(34,284),Size=new Size(330,28),Checked=settings.AutoUpdate};Controls.Add(auto);
   var restore=Button("원래 그래픽 복원",438,282,250);restore.Click+=(s,e)=>{try{Core.RestoreGraphics(path.Text);Say("원래 그래픽 파일로 복원했습니다. 런처 실행 시 호환 설정이 다시 적용됩니다.");}catch(Exception ex){Say(ex.Message);}};
   play=Button("게임 시작",34,333,270);play.Height=52;play.BackColor=Color.FromArgb(162,119,54);play.Font=new Font(Font,FontStyle.Bold);play.Click+=(s,e)=>Launch();
   update=Button("업데이트 확인",320,333,176);update.Height=52;update.Click+=async(s,e)=>await CheckUpdate();
   var notes=Button("패치노트",512,333,176);notes.Height=52;notes.Click+=(s,e)=>Process.Start(new ProcessStartInfo("https://github.com/japanoxx-afk/1000year/releases"){UseShellExecute=true});
   status=new Label{Text="게임 폴더와 화면 설정을 선택하세요.",Location=new Point(34,405),Size=new Size(654,54),ForeColor=Color.FromArgb(189,198,205)};Controls.Add(status);
   Shown+=async(s,e)=>{if(auto.Checked)await CheckUpdate();};FormClosing+=(s,e)=>{if(busy){e.Cancel=true;return;}Save();stop.Cancel();};
  }
  Button Button(string text,int x,int y,int width) {var b=new Button{Text=text,Location=new Point(x,y),Size=new Size(width,34),FlatStyle=FlatStyle.Flat,BackColor=Color.FromArgb(44,54,64),ForeColor=ForeColor};Controls.Add(b);return b;}
  void Save(){settings.GameDirectory=path.Text;settings.Mode=mode.SelectedIndex;settings.Fullscreen=full.Checked;settings.AutoUpdate=auto.Checked;try{Core.Save(settings);}catch(Exception ex){Core.Log(ex.ToString());}}
  void Say(string s){status.Text=s;Core.Log(s);}
  void SetBusy(bool b){busy=b;play.Enabled=update.Enabled=!b;path.Enabled=mode.Enabled=full.Enabled=!b;}
  void Launch(){try{Save();if(Core.GameRunning(path.Text))throw new IOException("선택한 폴더의 게임이 이미 실행 중입니다.");string exe=Core.Prepare(path.Text,mode.SelectedIndex,full.Checked);Process.Start(new ProcessStartInfo(exe){WorkingDirectory=Path.GetFullPath(path.Text),UseShellExecute=false});Say("게임을 실행했습니다. 설정은 다음 실행부터 적용됩니다.");}catch(Exception ex){Say("실행 실패: "+ex.Message);MessageBox.Show(this,ex.Message,"게임 실행",MessageBoxButtons.OK,MessageBoxIcon.Warning);}}
  async Task CheckUpdate(){if(busy)return;SetBusy(true);Save();try{if(Core.GameRunning(path.Text)){Say("게임 종료 후 업데이트를 확인하세요.");return;}Say("최신 버전을 확인하고 있습니다…");ServicePointManager.SecurityProtocol=SecurityProtocolType.Tls12;using(var client=new HttpClient()){client.DefaultRequestHeaders.UserAgent.ParseAdd("1000year-Launcher/"+Core.Version);string session=Path.Combine(Core.UserHome,"Updates",Guid.NewGuid().ToString("N"));string package=await Updates.Prepare(client,Core.Version,session,r=>true,Say,stop.Token);if(package!=null){await Updates.StartInstaller(package,Core.Home,Path.GetFileName(Application.ExecutablePath),Process.GetCurrentProcess().Id,stop.Token);SetBusy(false);Application.Exit();}}}catch(Exception ex){Say("업데이트 확인 실패 · 게임은 실행할 수 있습니다. "+ex.Message);}finally{SetBusy(false);}}
 }
}


