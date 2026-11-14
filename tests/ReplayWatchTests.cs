using System;
using System.IO;
using System.Linq;
using System.Web.Script.Serialization;
using Myth;
class ReplayWatchTests {
 static int Main(string[] args){string root=Path.Combine(Path.GetTempPath(),"MythWatchTest-"+Guid.NewGuid().ToString("N"));
  try{
   Core.UserHome=root;Replays.Library=Path.Combine(root,"Replays");string session=Path.Combine(root,"R","fixture");Directory.CreateDirectory(session);
   File.Copy(Path.Combine(args[0],"initial.dat"),Path.Combine(session,"initial.dat"));File.Copy(Path.Combine(args[0],"commands.bin"),Path.Combine(session,"commands.partial"));File.WriteAllText(Path.Combine(session,"status.txt"),"COMPLETE");
   var info=new ReplayInfo{Mode=3,RecordedAt=DateTime.UtcNow.ToString("o"),GameSHA256=Core.Hash(args[1]),PatchSHA256=Core.Hash(args[2]),EngineSHA256=Core.Hash(args[3])};
   File.WriteAllText(Path.Combine(session,"identity.json"),new JavaScriptSerializer().Serialize(info));
   Replays.Watch(Int32.MaxValue,session);string file=Directory.GetFiles(Replays.Library,"*.mythreplay").Single();
   var read=ReplayArchive.Read(file,null);if(read.Players.Length!=8||read.LastTick!=1080)throw new Exception("Watcher did not preserve actual eight-slot game trace");
   Console.WriteLine("PASS: watcher publishes complete actual game trace after launcher/game exit");return 0;
  }catch(Exception ex){Console.Error.WriteLine(ex);return 1;}finally{if(Directory.Exists(root))Directory.Delete(root,true);}
 }
}
