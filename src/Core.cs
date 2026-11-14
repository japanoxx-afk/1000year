using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Web.Script.Serialization;
using System.Diagnostics;
namespace Myth {
 public sealed class Edit { public int Offset; public string Before,After,Note; }
 public sealed class Recipe { public string SourceSHA256,OutputSHA256,AppendHex; public Edit[] Edits; }
 public sealed class Settings { public string GameDirectory=""; public int Mode=3; public bool Fullscreen=false; public bool AutoUpdate=true; }
 public static class Core {
  public const string Version="0.3.1";
  public static string Home=AppDomain.CurrentDomain.BaseDirectory;
  public static string UserHome=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"1000year");
  public static string Hash(string path) {using(var s=File.OpenRead(path))using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(s)).Replace("-","").ToLowerInvariant();}
  public static string HashBytes(byte[] data) {using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(data)).Replace("-","").ToLowerInvariant();}
  public static byte[] Hex(string s) {return Enumerable.Range(0,s.Length/2).Select(i=>Convert.ToByte(s.Substring(i*2,2),16)).ToArray();}
  public static Settings Load() { try{return new JavaScriptSerializer().Deserialize<Settings>(File.ReadAllText(Path.Combine(UserHome,"settings.json")))??new Settings();}catch{return new Settings();} }
  public static void Save(Settings s) {Directory.CreateDirectory(UserHome); File.WriteAllText(Path.Combine(UserHome,"settings.json"),new JavaScriptSerializer().Serialize(s));}
  public static void Log(string s) {try{Directory.CreateDirectory(UserHome);File.AppendAllText(Path.Combine(UserHome,"launcher.log"),DateTime.Now.ToString("s")+" "+s+Environment.NewLine);}catch{}}
  public static byte[] Patch(byte[] source,Recipe r) {
   if(HashBytes(source)!=r.SourceSHA256)throw new IOException("지원하지 않는 게임 실행 파일입니다. V1.070KR 원본 MMyth.exe가 필요합니다.");
   var result=(byte[])source.Clone();
   foreach(var e in r.Edits) {var before=Hex(e.Before);var after=Hex(e.After);if(before.Length!=after.Length||e.Offset<0||e.Offset>result.Length-before.Length||!result.Skip(e.Offset).Take(before.Length).SequenceEqual(before))throw new IOException("패치 원본 바이트 검증 실패: "+e.Note);Buffer.BlockCopy(after,0,result,e.Offset,after.Length);}
   if(!String.IsNullOrEmpty(r.AppendHex))result=result.Concat(Hex(r.AppendHex)).ToArray();
   if(HashBytes(result)!=r.OutputSHA256)throw new IOException("패치 결과 검증 실패");return result;
  }
  public static byte[] Resource(string name) {using(var s=typeof(Core).Assembly.GetManifestResourceStream(name)){if(s==null)throw new IOException("구성 파일 누락: "+name);using(var m=new MemoryStream()){s.CopyTo(m);return m.ToArray();}}}
  public static string Prepare(string directory,int mode,bool fullscreen) {
   if(mode<0 || mode>3)throw new IOException("지원하지 않는 해상도 설정입니다.");
   directory=Path.GetFullPath(directory);string source=Path.Combine(directory,"MMyth.exe");if(!File.Exists(source)||!Directory.Exists(Path.Combine(directory,"tile")))throw new IOException("MMyth.exe와 tile 폴더가 있는 게임 폴더를 선택하세요.");
   var recipe=new JavaScriptSerializer().Deserialize<Recipe>(System.Text.Encoding.UTF8.GetString(Resource(mode==3?"Myth.WideRecipe":mode==2?"Myth.HDRecipe":"Myth.PortableRecipe")));
   byte[] patched=Patch(File.ReadAllBytes(source),recipe);
   string target=Path.Combine(directory,mode==3?"MMyth.Wide.exe":mode==2?"MMyth.HD.exe":"MMyth.Portable.exe");
   File.WriteAllBytes(target+".partial",patched);if(File.Exists(target))File.Delete(target);File.Move(target+".partial",target);
   string dll=Path.Combine(directory,"ddraw.dll"),ini=Path.Combine(directory,"ddraw.ini");
   byte[] wrapper=Resource("Myth.DDraw");
   BackupGraphics(dll);BackupGraphics(ini);
   File.WriteAllBytes(dll,wrapper);
   File.WriteAllText(ini,"[ddraw]\r\nwidth="+(mode==3?1280:mode==0?640:1024)+"\r\nheight="+(mode==3?720:mode==0?480:768)+"\r\nwindowed=true\r\nfullscreen="+fullscreen.ToString().ToLowerInvariant()+"\r\nmaintas=true\r\nboxing=false\r\nadjmouse=true\r\nrenderer=auto\r\nmaxfps=60\r\nvsync=false\r\n",System.Text.Encoding.ASCII);
   File.WriteAllText(dll+".1000year-managed",Hash(dll));File.WriteAllText(ini+".1000year-managed",Hash(ini));
   Log("Prepared mode="+mode+" exe="+target+" SHA256="+Hash(target));return target;
  }
  static void BackupGraphics(string file){if(File.Exists(file+".1000year-original")||File.Exists(file+".1000year-absent"))return;if(File.Exists(file))File.Copy(file,file+".1000year-original");else File.WriteAllText(file+".1000year-absent","");}
  public static void RestoreGraphics(string directory) {
   if(GameRunning(directory))throw new IOException("게임을 종료한 뒤 복원하세요.");
   foreach(string name in new[]{"ddraw.dll","ddraw.ini"}){string file=Path.Combine(directory,name),backup=file+".1000year-original";if(File.Exists(backup))File.Copy(backup,file,true);else if(File.Exists(file+".1000year-absent")&&File.Exists(file)&&File.Exists(file+".1000year-managed")&&Hash(file)==File.ReadAllText(file+".1000year-managed"))File.Delete(file);}
   Log("Original graphics restored: "+directory);
  }
  public static bool GameRunning(string directory) {foreach(var p in Process.GetProcesses()){using(p){try{if((p.ProcessName.StartsWith("MMyth",StringComparison.OrdinalIgnoreCase))&&String.Equals(Path.GetDirectoryName(p.MainModule.FileName),Path.GetFullPath(directory),StringComparison.OrdinalIgnoreCase))return true;}catch{}}}return false;}
 }
}

