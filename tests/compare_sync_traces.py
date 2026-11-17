"""Compare completed MYTH_SYNC_TEST game sessions (not network emulation)."""
import pathlib,sys
assert len(sys.argv)>=3,'Provide at least two completed session directories'
traces=[]
for argument in sys.argv[1:]:
 root=pathlib.Path(argument);assert (root/'status.txt').read_text()=='COMPLETE',str(root)
 rows={}
 for line in (root/'sync-trace.txt').read_text().splitlines():
  index,tick,seed,state,unitsum,frame_seed=line.split()
  value=(int(tick),int(seed),int(state,16),int(unitsum,16),int(frame_seed,16))
  index=int(index)
  # Older test loggers also emitted native timer attempts that changed no
  # state. Those must exactly equal the previous accepted frame, then retry.
  if index in rows:assert rows[index]==value or rows[index]==rows.get(index-1),(root,index,'inconsistent repeated frame')
  rows[index]=value
 assert rows and sorted(rows)==list(range(len(rows))),str(root)
 traces.append(rows)
for argument,rows in zip(sys.argv[2:],traces[1:]):
 assert len(rows)==len(traces[0]),(argument,'frame count differs')
 for index,value in traces[0].items():assert value==rows[index],(argument,index,value,rows[index])
print('PASS:',len(traces[0]),'frames agree across',len(traces),'resolutions: tick, RNG, unit/resource state, native unit accumulator and network RNG')
