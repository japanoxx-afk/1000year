using System;using System.IO;using System.Linq;using System.Windows.Forms;using Myth;
class ReplayLibraryTests {
 [STAThread]static int Main(string[] args){string temp=Path.Combine(Path.GetTempPath(),"MythLibrary-"+Guid.NewGuid().ToString("N"));try{
  if(args.Length>0){var info=ReplayArchive.Read(args[0],null);Console.WriteLine("Verified existing archive: "+info.Frames+" frames, ticks "+info.FirstTick+".."+info.LastTick);}
  Core.UserHome=Path.Combine(temp,"user");Replays.Library=Path.Combine(Core.UserHome,"Replays");string game=Path.Combine(temp,"game");Directory.CreateDirectory(Replays.Library);Directory.CreateDirectory(Path.Combine(game,"Replays"));
  File.WriteAllText(Path.Combine(Replays.Library,"old.mythreplay"),"same existing archive");File.WriteAllText(Path.Combine(game,"Replays","old-copy.mythreplay"),"same existing archive");File.WriteAllText(Path.Combine(game,"Replays","new.MYTHREPLAY"),"another archive");
  if(Replays.LibraryFiles(game).Length!=2)throw new Exception("Shared/portable discovery or duplicate handling failed");
  using(var form=new ReplayLibrary(game,false)){var list=form.Controls.OfType<ListBox>().Single();if(list.Items.Count!=2)throw new Exception("Existing archives missing from form");string selection=(string)list.SelectedItem;File.WriteAllText(Path.Combine(Replays.Library,"latest.mythreplay"),"newly saved while open");form.RefreshLibrary(false);if(list.Items.Count!=3||(string)list.SelectedItem!=selection)throw new Exception("Refresh lost new record or selection");File.Delete(Path.Combine(Replays.Library,"latest.mythreplay"));form.RefreshLibrary(false);if(list.Items.Count!=2)throw new Exception("Removal refresh failed");}
  Console.WriteLine("PASS: existing records, two storage locations, mixed-case extension, duplicate archives, live list refresh and selection preservation");return 0;
 }catch(Exception ex){Console.Error.WriteLine(ex);return 1;}finally{if(Directory.Exists(temp))Directory.Delete(temp,true);}}
}
