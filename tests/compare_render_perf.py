"""Compare completed, input-isolated normal-game performance fixtures."""
import pathlib,sys,subprocess,re
assert len(sys.argv)==3,'BASELINE_SESSION OPTIMIZED_SESSION'
baseline,optimized=map(pathlib.Path,sys.argv[1:])
subprocess.run([sys.executable,'tests/compare_sync_traces.py',str(baseline),str(optimized)],check=True)
for tick in (100,300,500,700,900):
 before=(baseline/f'terrain-{tick}.raw').read_bytes();after=(optimized/f'terrain-{tick}.raw').read_bytes()
 assert before and before==after,('terrain pixels differ',tick)
def metrics(root):
 text=(root/'render-perf.txt').read_text()
 summary={key:float(value) for key,value in re.findall(r'(elapsed_ms|process_cpu_ms|redraws|reuses|timerMaskBuilds)=([0-9.]+)',text)}
 summary['timer_us']=float(re.search(r'timer calls=\d+ mean_us=([0-9.]+)',text).group(1))
 return summary
before,after=metrics(baseline),metrics(optimized)
assert abs(after['elapsed_ms']/before['elapsed_ms']-1)<.05,'Game pace changed'
assert after['process_cpu_ms']<before['process_cpu_ms'],'CPU improvement not demonstrated'
assert after['timer_us']<before['timer_us'],'Timer improvement not demonstrated'
assert after['reuses']>0
print('PASS: five terrain snapshots match byte-for-byte across camera moves/map edges; game pace preserved')
print('Process CPU ms:',before['process_cpu_ms'],'->',after['process_cpu_ms'],'reduction %.1f%%'%(100*(1-after['process_cpu_ms']/before['process_cpu_ms'])))
print('Timer mean us:',before['timer_us'],'->',after['timer_us'])
