using System;
using System.IO;
using Myth;
class ReplayHarness {
 static int Main(string[] args){try{Directory.CreateDirectory(args[2]);string engine=Path.Combine(args[2],"engine-"+Guid.NewGuid().ToString("N")+".dll");File.Copy(args[1],engine);var p=ReplayProcess.Start(args[0],engine,args[2],args.Length>3&&args[3]=="play");Console.WriteLine("PID="+p.Id);return 0;}catch(Exception e){Console.Error.WriteLine(e);return 1;}}
}
