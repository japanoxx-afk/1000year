using System;
using System.IO;
using System.Linq;
using System.Web.Script.Serialization;
using Myth;
class ReplayWatchTests {
 static int Main(string[] args){string root=Path.Combine(Path.GetTempPath(),"MythWatchTest-"+Guid.NewGuid().ToString("N"));
  try{
   if(ReplayAssociation.OpenCommand(@"C:\Games\천년의 신화\MythLauncher.exe")!="\"C:\\Games\\천년의 신화\\MythLauncher.exe\" --replay \"%1\"")throw new Exception("Replay association command quoting failed");
   Core.UserHome=root;Replays.Library=Path.Combine(root,"Replays");string session=Path.Combine(root,"R","fixture");Directory.CreateDirectory(session);
   File.Copy(Path.Combine(args[0],"initial.dat"),Path.Combine(session,"initial.dat"));File.Copy(Path.Combine(args[0],"commands.bin"),Path.Combine(session,"commands.partial"));File.WriteAllText(Path.Combine(session,"status.txt"),"COMPLETE");
   var info=new ReplayInfo{Mode=3,RecordedAt=DateTime.UtcNow.ToString("o"),GameSHA256=Core.Hash(args[1]),PatchSHA256=Core.Hash(args[2]),EngineSHA256=Core.Hash(args[3])};
   File.WriteAllText(Path.Combine(session,"identity.json"),new JavaScriptSerializer().Serialize(info));
   Replays.Watch(args.Length>4?Int32.Parse(args[4]):Int32.MaxValue,session);string file=Directory.GetFiles(Replays.Library,"*.mythreplay").Single();
   var expected=ReplayArchive.InspectCommands(File.ReadAllBytes(Path.Combine(session,"commands.partial")));
   var read=ReplayArchive.Read(file,null);if(!read.Players.SequenceEqual(expected.Players)||read.LastTick!=expected.LastTick)throw new Exception("Watcher did not preserve actual game trace");
   Replays.Recover();Replays.Recover();if(Directory.GetFiles(Replays.Library,"*.mythreplay").Length!=1)throw new Exception("Recovery duplicated a replay");
   File.WriteAllText(Path.Combine(session,"status.txt"),"RECORDING");Replays.Recover();if(Directory.GetFiles(Replays.Library,"*.mythreplay").Length!=1)throw new Exception("Recovery published an unfinished recording");
   Console.WriteLine("PASS: actual trace publication, recovery, duplicate prevention, incomplete-session exclusion");return 0;
  }catch(Exception ex){Console.Error.WriteLine(ex);return 1;}finally{if(Directory.Exists(root))Directory.Delete(root,true);}
 }
}
