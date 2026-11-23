using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;
namespace Myth {
 // Edits Settings.KeyBindings. Each row keeps the game's original key and lets
 // the player choose which physical key performs it.
 public sealed class HotkeyDialog:Form {
  readonly DataGridView grid;
  public string Bindings{get;private set;}
  static IEnumerable<KeyValuePair<string,int>> Functions(){
   for(int i=1;i<=10;++i)yield return new KeyValuePair<string,int>("부대 "+(i%10)+" (Ctrl+지정 / 선택)",0x30+i%10);
   for(int i=1;i<=8;++i)yield return new KeyValuePair<string,int>("명령 버튼 "+i,0x6f+i);
   yield return new KeyValuePair<string,int>("쉬는 일꾼 전체 선택",0xbe);
   yield return new KeyValuePair<string,int>("군사 유닛 전체 선택",0xc0);
   yield return new KeyValuePair<string,int>("영웅 전체 선택",0x09);
   for(int k=0x41;k<=0x5a;++k)yield return new KeyValuePair<string,int>("명령·생산 버튼 단축키 "+(char)k,k);
  }
  public HotkeyDialog(string bindings) {
   Text="단축키 설정";ClientSize=new Size(560,600);StartPosition=FormStartPosition.CenterParent;FormBorderStyle=FormBorderStyle.FixedDialog;MaximizeBox=MinimizeBox=false;
   BackColor=Color.FromArgb(23,29,35);ForeColor=Color.FromArgb(236,229,214);Font=new Font("맑은 고딕",10);
   Controls.Add(new Label{Text="새 키를 누르면 원래 키의 기능이 실행됩니다. 바꾼 원래 키는 다른 기능에 쓰지 않으면 꺼집니다.\r\n내 컴퓨터의 키 입력만 바꾸므로 멀티플레이 상대와 동기화에 영향이 없습니다. 방향키·Ctrl·Shift·Alt·Enter·Esc는 바꿀 수 없습니다.",Location=new Point(16,12),Size=new Size(528,58),ForeColor=Color.FromArgb(189,198,205)});
   grid=new DataGridView{Location=new Point(16,76),Size=new Size(528,460),AllowUserToAddRows=false,AllowUserToDeleteRows=false,RowHeadersVisible=false,SelectionMode=DataGridViewSelectionMode.CellSelect,AutoSizeColumnsMode=DataGridViewAutoSizeColumnsMode.Fill,BackgroundColor=Color.FromArgb(32,40,48),EditMode=DataGridViewEditMode.EditOnEnter};
   grid.DefaultCellStyle.BackColor=Color.FromArgb(32,40,48);grid.DefaultCellStyle.ForeColor=ForeColor;grid.DefaultCellStyle.SelectionBackColor=Color.FromArgb(162,119,54);
   grid.ColumnHeadersDefaultCellStyle.BackColor=Color.FromArgb(44,54,64);grid.ColumnHeadersDefaultCellStyle.ForeColor=ForeColor;grid.EnableHeadersVisualStyles=false;
   grid.Columns.Add(new DataGridViewTextBoxColumn{HeaderText="기능",ReadOnly=true,FillWeight=200});
   grid.Columns.Add(new DataGridViewTextBoxColumn{HeaderText="원래 키",ReadOnly=true,FillWeight=70});
   var choice=new DataGridViewComboBoxColumn{HeaderText="새 키",FillWeight=90,FlatStyle=FlatStyle.Flat,DisplayStyleForCurrentCellOnly=false};
   foreach(int key in Hotkeys.Keys)choice.Items.Add(Hotkeys.Name(key));
   grid.Columns.Add(choice);
   Dictionary<int,int> current=new Dictionary<int,int>();
   try{foreach(var b in Hotkeys.Parse(bindings))current[b[0]]=b[1];}catch(FormatException){}
   foreach(var f in Functions()){int pressed;if(!current.TryGetValue(f.Value,out pressed))pressed=f.Value;int row=grid.Rows.Add(f.Key,Hotkeys.Name(f.Value),Hotkeys.Name(pressed));grid.Rows[row].Tag=f.Value;}
   Controls.Add(grid);
   var reset=MakeButton("기본값",16,548,120);reset.Click+=(s,e)=>{foreach(DataGridViewRow r in grid.Rows)r.Cells[2].Value=Hotkeys.Name((int)r.Tag);};
   var save=MakeButton("저장",304,548,116);save.BackColor=Color.FromArgb(162,119,54);save.Click+=(s,e)=>Save();
   var cancel=MakeButton("취소",428,548,116);cancel.Click+=(s,e)=>{DialogResult=DialogResult.Cancel;Close();};
   AcceptButton=save;CancelButton=cancel;
  }
  Button MakeButton(string text,int x,int y,int width){var b=new Button{Text=text,Location=new Point(x,y),Size=new Size(width,36),FlatStyle=FlatStyle.Flat,BackColor=Color.FromArgb(44,54,64),ForeColor=ForeColor};Controls.Add(b);return b;}
  void Save(){
   grid.EndEdit();var bindings=new List<int[]>();
   foreach(DataGridViewRow r in grid.Rows){string name=Convert.ToString(r.Cells[2].Value);int pressed=Hotkeys.Keys.FirstOrDefault(k=>Hotkeys.Name(k)==name);if(pressed==0)pressed=(int)r.Tag;bindings.Add(new[]{(int)r.Tag,pressed});}
   var duplicate=bindings.GroupBy(b=>b[1]).FirstOrDefault(g=>g.Count()>1);
   if(duplicate!=null){MessageBox.Show(this,Hotkeys.Name(duplicate.Key)+" 키가 두 기능에 지정되었습니다. 다른 기능의 키도 함께 바꿔 주세요.","단축키 설정",MessageBoxButtons.OK,MessageBoxIcon.Warning);return;}
   string text=Hotkeys.Format(bindings);
   try{Hotkeys.Parse(text);}catch(FormatException ex){MessageBox.Show(this,ex.Message,"단축키 설정",MessageBoxButtons.OK,MessageBoxIcon.Warning);return;}
   Bindings=text;DialogResult=DialogResult.OK;Close();
  }
 }
}
