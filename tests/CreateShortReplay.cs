using System;
using System.IO;
using System.Web.Script.Serialization;
using Myth;
class CreateShortReplay {
 static int Main(string[] args){string stage=Path.Combine(Path.GetTempPath(),"MythShort-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(stage);
  try{byte[] data=File.ReadAllBytes(Path.Combine(args[0],"commands.partial"));int pos=8,count=0,limit=Int32.Parse(args[2]);if(limit<1||limit>1000)throw new Exception("Frame limit");
   while(count<limit&&pos+44<=data.Length&&BitConverter.ToUInt32(data,pos)==1){uint commands=BitConverter.ToUInt32(data,pos+40);if(commands>400)throw new Exception("Command limit");pos=checked(pos+44+(int)commands*108);if(pos>data.Length)throw new Exception("Truncated trace");count++;}
   using(var file=File.Create(Path.Combine(stage,"commands.partial"))){file.Write(data,0,pos);file.Write(BitConverter.GetBytes(UInt32.MaxValue),0,4);}
   File.Copy(Path.Combine(args[0],"initial.dat"),Path.Combine(stage,"initial.dat"));File.Copy(Path.Combine(args[0],"timing.txt"),Path.Combine(stage,"timing.txt"));
   var info=new JavaScriptSerializer().Deserialize<ReplayInfo>(File.ReadAllText(Path.Combine(args[0],"identity.json")));ReplayArchive.Create(args[1],stage,info);Console.WriteLine("Created "+count+"-frame completion fixture");return 0;
  }catch(Exception ex){Console.Error.WriteLine(ex);return 1;}finally{foreach(string file in Directory.GetFiles(stage))File.Delete(file);Directory.Delete(stage);}
 }
}
