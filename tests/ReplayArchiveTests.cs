using System;
using System.IO;
using System.Linq;
using Myth;
class ReplayArchiveTests {
 static int passed;
 static void Check(bool result,string text){if(!result)throw new Exception(text);passed++;}
 static void Reject(Action action,string text){try{action();}catch(InvalidDataException){passed++;return;}catch(EndOfStreamException){passed++;return;}throw new Exception(text);}
 static int Main(string[] args){string root=Path.Combine(Path.GetTempPath(),"MythReplayTest-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(root);
  try{
   byte[] commands;using(var m=new MemoryStream())using(var w=new BinaryWriter(m)){w.Write(System.Text.Encoding.ASCII.GetBytes("MYTHRP01"));w.Write(1u);foreach(uint v in new uint[]{0,123,8,456,1,789,8,654,1,8})w.Write(v);
    for(int player=0;player<8;player++){w.Write(player);byte[] p=new byte[104];Buffer.BlockCopy(BitConverter.GetBytes((ushort)3),0,p,0,2);Buffer.BlockCopy(BitConverter.GetBytes((ushort)player),0,p,12,2);Buffer.BlockCopy(BitConverter.GetBytes((ushort)1),0,p,20,2);Buffer.BlockCopy(BitConverter.GetBytes(0x12340001),0,p,22,4);w.Write(p);}w.Write(UInt32.MaxValue);commands=m.ToArray();}
   var stats=ReplayArchive.InspectCommands(commands);Check(stats.Frames==1&&stats.Players.SequenceEqual(Enumerable.Range(0,8)),"eight players");
   Reject(()=>ReplayArchive.InspectCommands(commands.Take(commands.Length-1).ToArray()),"truncated seal");
   byte[] bad=(byte[])commands.Clone();bad[52]=8;Reject(()=>ReplayArchive.InspectCommands(bad),"player bounds");
   bad=(byte[])commands.Clone();bad[76]=21;Reject(()=>ReplayArchive.InspectCommands(bad),"selection bounds");
   File.WriteAllBytes(Path.Combine(root,"initial.dat"),new byte[]{1,2,3,4});File.WriteAllBytes(Path.Combine(root,"commands.partial"),commands);
   string digest=new string('a',64),file=Path.Combine(root,"test.mythreplay");
   ReplayArchive.Create(file,root,new ReplayInfo{Mode=3,RecordedAt=DateTime.UtcNow.ToString("o"),GameSHA256=digest,PatchSHA256=digest,EngineSHA256=digest});
   var info=ReplayArchive.Read(file,Path.Combine(root,"stage"));Check(info.Frames==1&&info.Mode==3,"archive round trip");Check(File.ReadAllBytes(Path.Combine(root,"stage","commands.bin")).SequenceEqual(commands),"exact command extraction");
   byte[] archive=File.ReadAllBytes(file);bad=(byte[])archive.Clone();bad[bad.Length-8]^=1;string corrupt=Path.Combine(root,"bad.mythreplay");File.WriteAllBytes(corrupt,bad);Reject(()=>ReplayArchive.Read(corrupt,null),"hash mismatch");
   File.WriteAllBytes(corrupt,archive.Concat(new byte[]{0}).ToArray());Reject(()=>ReplayArchive.Read(corrupt,null),"trailing bytes");
   bad=(byte[])archive.Clone();Buffer.BlockCopy(BitConverter.GetBytes(Int32.MaxValue),0,bad,8,4);File.WriteAllBytes(corrupt,bad);Reject(()=>ReplayArchive.Read(corrupt,null),"oversized metadata");
   if(args.Length>0){var actual=ReplayArchive.InspectCommands(File.ReadAllBytes(args[0]));Check(actual.Frames>0,"actual game trace");Console.WriteLine("Actual game: "+actual.Frames+" frames, tick "+actual.LastTick);}
   Console.WriteLine("PASS: "+passed+" replay archive checks");return 0;
  }catch(Exception ex){Console.Error.WriteLine(ex);return 1;}finally{Directory.Delete(root,true);}
 }
}
