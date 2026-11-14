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
 var serializer=new JavaScriptSerializer();var source=(args.Length==0||String.IsNullOrEmpty(args[0]))?null:File.ReadAllBytes(args[0]);
 if(source!=null)foreach(var name in new[]{"portable","hd","wide"}) {var r=serializer.Deserialize<Recipe>(File.ReadAllText("compat/"+name+".json"));var patched=Core.Patch(source,r);Check(Core.HashBytes(patched)==r.OutputSHA256,name+" output");var tampered=(byte[])source.Clone();tampered[100]^=1;Reject(()=>Core.Patch(tampered,r),name+" rejects different game");r.Edits[0].Before="00";Reject(()=>Core.Patch(source,r),name+" rejects mismatched bytes");}
 Reject(()=>Updates.Parse("{\"tag_name\":\"../../bad\"}"),"unsafe version rejected");Reject(()=>Updates.Parse("{\"tag_name\":\"v1.0.0\",\"prerelease\":true}"),"preview release rejected");
 var missing=new Fixture{Code=HttpStatusCode.NotFound,Body=""};using(var c=new HttpClient(missing)){Check(Updates.Prepare(c,"0.1.0",".tools/update-test",r=>true,s=>{},CancellationToken.None).GetAwaiter().GetResult()==null,"no release keeps launcher available");}
 var current=new Fixture{Body="{\"tag_name\":\"v0.1.0\"}"};using(var c=new HttpClient(current)){Check(Updates.Prepare(c,"0.1.0",".tools/update-test",r=>true,s=>{},CancellationToken.None).GetAwaiter().GetResult()==null,"current release does not install");}
 var wrong=new Fixture{Body="{\"tag_name\":\"v99.0.0\",\"assets\":[{\"name\":\"MythLauncher.zip\",\"browser_download_url\":\"https://example.com/bad.zip\"}]}"};using(var c=new HttpClient(wrong)){Reject(()=>Updates.Prepare(c,"0.1.0",".tools/update-test",r=>true,s=>{},CancellationToken.None).GetAwaiter().GetResult(),"foreign repository rejected");}
 Console.WriteLine(count+" checks passed");
 }
}



