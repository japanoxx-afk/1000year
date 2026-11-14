using System;
using System.IO;
using System.Text;
using System.Linq;
using System.Collections.Generic;
using System.Web.Script.Serialization;
namespace Myth {
 public sealed class ReplayInfo {
  public int Format=1,Rules=1,Mode,Frames,FirstTick,LastTick,TickMilliseconds=60;
  public string GameSHA256,PatchSHA256,EngineSHA256,InitialSHA256,CommandsSHA256,RecordedAt;
  public int[] Players;
 }
 public static class ReplayArchive {
  public const int Limit=128*1024*1024;
  static readonly byte[] Magic=Encoding.ASCII.GetBytes("MYTHPK01");
  static bool Digest(string text){return text!=null&&text.Length==64&&text.All(c=>c>='0'&&c<='9'||c>='a'&&c<='f');}
  static byte[] ReadBytes(BinaryReader reader,int max){int n=reader.ReadInt32();if(n<1||n>max||n>reader.BaseStream.Length-reader.BaseStream.Position)throw new InvalidDataException("리플레이 데이터 크기가 올바르지 않습니다.");byte[] b=reader.ReadBytes(n);if(b.Length!=n)throw new EndOfStreamException();return b;}
  static void Put(BinaryWriter writer,byte[] data){writer.Write(data.Length);writer.Write(data);}
  public static ReplayInfo InspectCommands(byte[] bytes){
   if(bytes.Length<12||bytes.Length>Limit||Encoding.ASCII.GetString(bytes,0,8)!="MYTHRP01")throw new InvalidDataException("명령 기록 형식이 올바르지 않습니다.");
   var info=new ReplayInfo();var players=new SortedSet<int>();uint previousTick=0;bool first=true,ended=false;
   using(var r=new BinaryReader(new MemoryStream(bytes))){r.ReadBytes(8);while(r.BaseStream.Position<r.BaseStream.Length){
    uint tag=r.ReadUInt32();if(tag==UInt32.MaxValue){ended=true;break;}if(tag!=1)throw new InvalidDataException("명령 기록 태그 오류");
    uint tick=r.ReadUInt32();r.ReadUInt32();uint units=r.ReadUInt32();r.ReadUInt32();
    uint after=r.ReadUInt32();r.ReadUInt32();uint afterUnits=r.ReadUInt32();r.ReadUInt32();
    uint result=r.ReadUInt32(),count=r.ReadUInt32();
    if(units>1199||afterUnits>1199||tick>Int32.MaxValue||after>Int32.MaxValue||after<tick||after-tick>1||(!first&&tick!=previousTick)||result>1||count>400)throw new InvalidDataException("프레임 순서 또는 명령 개수 오류");
    if(first)info.FirstTick=(int)tick;first=false;previousTick=after;info.LastTick=(int)after;info.Frames++;
    int[] used=new int[8];for(uint i=0;i<count;i++){
     uint player=r.ReadUInt32();byte[] p=r.ReadBytes(104);if(p.Length!=104||player>=8||++used[player]>50)throw new InvalidDataException("플레이어 명령 오류");
     int command=BitConverter.ToUInt16(p,0),selected=BitConverter.ToUInt16(p,20);
     // Native command table ends at B8FF88: (B8FF88-B8DD80)/24=363.
     if(command<1||command>363||selected>20||BitConverter.ToUInt16(p,12)!=player)throw new InvalidDataException("게임 명령 범위 오류");
     for(int j=0;j<selected;j++){int id=BitConverter.ToUInt16(p,22+4*j);if(id<1||id>1199)throw new InvalidDataException("유닛 식별자 오류");}
     players.Add((int)player);
    }
   }if(!ended||r.BaseStream.Position!=r.BaseStream.Length||first)throw new InvalidDataException("정상 종료되지 않은 리플레이입니다.");}
   info.Players=players.ToArray();return info;
  }
  public static void Create(string target,string session,ReplayInfo identity){
   byte[] initial=File.ReadAllBytes(Path.Combine(session,"initial.dat")),commands=File.ReadAllBytes(Path.Combine(session,"commands.partial"));
   if(initial.Length<1||initial.Length>32*1024*1024)throw new InvalidDataException("시작 세이브 크기 오류");
   var stats=InspectCommands(commands);identity.Frames=stats.Frames;identity.FirstTick=stats.FirstTick;identity.LastTick=stats.LastTick;identity.Players=stats.Players;
   string timing=Path.Combine(session,"timing.txt");int milliseconds;if(File.Exists(timing)&&Int32.TryParse(File.ReadAllText(timing),out milliseconds))identity.TickMilliseconds=milliseconds;
   identity.InitialSHA256=Core.HashBytes(initial);identity.CommandsSHA256=Core.HashBytes(commands);
   byte[] metadata=Encoding.UTF8.GetBytes(new JavaScriptSerializer().Serialize(identity));
   string partial=target+"."+Guid.NewGuid().ToString("N")+".partial";
   try{using(var stream=new FileStream(partial,FileMode.CreateNew,FileAccess.Write,FileShare.None))using(var w=new BinaryWriter(stream)){w.Write(Magic);Put(w,metadata);Put(w,initial);Put(w,commands);w.Flush();stream.Flush(true);}Read(partial,null);File.Move(partial,target);}finally{if(File.Exists(partial))File.Delete(partial);}
  }
  public static ReplayInfo Read(string file,string staging){
   byte[] initial,commands;ReplayInfo info;
   using(var stream=File.OpenRead(file))using(var r=new BinaryReader(stream)){
    if(stream.Length>Limit+33L*1024*1024||!r.ReadBytes(8).SequenceEqual(Magic))throw new InvalidDataException("지원하지 않는 리플레이 파일입니다.");
    info=new JavaScriptSerializer().Deserialize<ReplayInfo>(Encoding.UTF8.GetString(ReadBytes(r,65536)));
    if(info==null||info.Format!=1||info.Rules!=1||info.Mode<0||info.Mode>3||info.TickMilliseconds<10||info.TickMilliseconds>1000||!Digest(info.GameSHA256)||!Digest(info.PatchSHA256)||!Digest(info.EngineSHA256)||!Digest(info.InitialSHA256)||!Digest(info.CommandsSHA256))throw new InvalidDataException("리플레이 호환 정보 오류");
    DateTime date;if(!DateTime.TryParse(info.RecordedAt,out date))throw new InvalidDataException("리플레이 날짜 오류");
    initial=ReadBytes(r,32*1024*1024);commands=ReadBytes(r,Limit);
    if(stream.Position!=stream.Length||Core.HashBytes(initial)!=info.InitialSHA256||Core.HashBytes(commands)!=info.CommandsSHA256)throw new InvalidDataException("리플레이 파일이 손상되었습니다.");
   }
   var stats=InspectCommands(commands);
   if(info.Frames!=stats.Frames||info.FirstTick!=stats.FirstTick||info.LastTick!=stats.LastTick||info.Players==null||!info.Players.SequenceEqual(stats.Players))throw new InvalidDataException("리플레이 통계가 기록과 일치하지 않습니다.");
   if(staging!=null){Directory.CreateDirectory(staging);File.WriteAllBytes(Path.Combine(staging,"initial.dat"),initial);File.WriteAllBytes(Path.Combine(staging,"commands.bin"),commands);File.WriteAllText(Path.Combine(staging,"timing.txt"),info.TickMilliseconds.ToString());}
   return info;
  }
 }
}
