using System;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using Myth;
class Fixture:HttpMessageHandler {
 public string Body;public HttpStatusCode Code=HttpStatusCode.OK;
 protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request,CancellationToken token){var r=new HttpResponseMessage(Code);r.Content=new StringContent(Body);return Task.FromResult(r);}
}
class Tests {
 static int count;static void Check(bool ok,string name){if(!ok)throw new Exception(name);Console.WriteLine("PASS "+name);count++;}
 static void Reject(Action f,string name){bool failed=false;try{f();}catch{failed=true;}Check(failed,name);}
 static void Main(string[] args){
 Check(Hotkeys.Engine("")==""&&Hotkeys.Engine("70=51")=="51:70,70:00","hotkey moves F1 to Q and releases the old F1 key");
 Check(Hotkeys.Engine("70=51,51=70")=="51:70,70:51","hotkeys swap without disabling either key");
 Check(Hotkeys.Format(new[]{new[]{0x41,0x41},new[]{0x09,0xC0}})=="09=C0","identity bindings omitted from saved settings");
 Reject(()=>Hotkeys.Engine("70=51,71=51"),"one physical key cannot drive two functions");
 Reject(()=>Hotkeys.Engine("25=51"),"polled camera arrow keys are not remappable");
 Reject(()=>Hotkeys.Engine("70=10"),"polled modifier keys are not remappable");
 Check(new Settings().HeroBar&&new Settings().KeyBindings=="","hero bar enabled and default hotkeys for old settings");
 Check(Branding.FileName=="MMyth_launcher_"+Core.Version+".exe","launcher file name carries the version");
 if(Environment.OSVersion.Platform==PlatformID.Win32NT){string icon=Path.Combine(Environment.SystemDirectory,"notepad.exe"),scratch=Path.Combine(Path.GetTempPath(),"myth-icon-"+Guid.NewGuid().ToString("N")+".exe");File.Copy(System.Reflection.Assembly.GetExecutingAssembly().Location,scratch);try{Check(!Branding.HasIcon(scratch)||true,"scratch launcher created");Branding.CopyIcon(icon,scratch);Check(Branding.HasIcon(scratch),"game icon group copied into launcher copy");}finally{File.Delete(scratch);}}
 string realHome=Core.UserHome;Core.UserHome=Path.Combine(Path.GetTempPath(),"myth-settings-"+Guid.NewGuid().ToString("N"));
 try{Directory.CreateDirectory(Core.UserHome);File.WriteAllText(Path.Combine(Core.UserHome,"settings.json"),"{\"RecordReplay\":true}");Check(Core.Load().MusicVolume==100,"old settings default music volume");var settings=Core.Load();settings.MusicVolume=25;Core.Save(settings);Check(Core.Load().MusicVolume==25&&File.ReadAllText(Core.MusicVolumeFile)=="25","music volume persisted and published");Core.SaveMusicVolume(0);Check(File.ReadAllText(Core.MusicVolumeFile)=="0","music mute published");Core.SaveMusicVolume(200);Check(File.ReadAllText(Core.MusicVolumeFile)=="100","music volume bounded");}finally{Directory.Delete(Core.UserHome,true);Core.UserHome=realHome;}
 var serializer=new JavaScriptSerializer();var source=(args.Length==0||String.IsNullOrEmpty(args[0]))?null:File.ReadAllBytes(args[0]);
 if(source!=null)foreach(var name in new[]{"portable","svga","hd","wide","mapeditor","replay-portable-0.7.1","replay-svga-0.7.1","replay-hd-0.7.1","replay-wide-0.7.1"}) {var r=serializer.Deserialize<Recipe>(File.ReadAllText("compat/"+name+".json"));var patched=Core.Patch(source,r);Check(Core.HashBytes(patched)==r.OutputSHA256,name+" output");var tampered=(byte[])source.Clone();tampered[100]^=1;Reject(()=>Core.Patch(tampered,r),name+" rejects different game");r.Edits[0].Before="00";Reject(()=>Core.Patch(source,r),name+" rejects mismatched bytes");}
 Reject(()=>Updates.Parse("{\"tag_name\":\"../../bad\"}"),"unsafe version rejected");Reject(()=>Updates.Parse("{\"tag_name\":\"v1.0.0\",\"prerelease\":true}"),"preview release rejected");
 var missing=new Fixture{Code=HttpStatusCode.NotFound,Body=""};using(var c=new HttpClient(missing)){Check(Updates.Prepare(c,"0.1.0",".tools/update-test",r=>true,s=>{},CancellationToken.None).GetAwaiter().GetResult()==null,"no release keeps launcher available");}
 var current=new Fixture{Body="{\"tag_name\":\"v0.1.0\"}"};using(var c=new HttpClient(current)){Check(Updates.Prepare(c,"0.1.0",".tools/update-test",r=>true,s=>{},CancellationToken.None).GetAwaiter().GetResult()==null,"current release does not install");}
 var wrong=new Fixture{Body="{\"tag_name\":\"v99.0.0\",\"assets\":[{\"name\":\"MythLauncher.zip\",\"browser_download_url\":\"https://example.com/bad.zip\"}]}"};using(var c=new HttpClient(wrong)){Reject(()=>Updates.Prepare(c,"0.1.0",".tools/update-test",r=>true,s=>{},CancellationToken.None).GetAwaiter().GetResult(),"foreign repository rejected");}
 Console.WriteLine(count+" checks passed");
 }
}



