"""Probe a deliberately launched test replay through its documented control file.
No window/UI input. The game process must belong to the isolated test installation.
"""
import ctypes, pathlib, sys, time
pid=int(sys.argv[1]);session=pathlib.Path(sys.argv[2])
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.restype=ctypes.c_void_p
k.ReadProcessMemory.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p]
k.CloseHandle.argtypes=[ctypes.c_void_p]
h=k.OpenProcess(0x410,False,pid)
assert h,'Cannot open test replay'
def tick():
 b=ctypes.c_uint32();done=ctypes.c_size_t()
 assert k.ReadProcessMemory(h,0xa6ea50,ctypes.byref(b),4,ctypes.byref(done)) and done.value==4
 return b.value
def command(value): (session/'control.txt').write_text(value,encoding='ascii')
try:
 command('pause');time.sleep(.3);first=tick();time.sleep(.3);assert tick()==first,'Pause advanced the world'
 command('step');time.sleep(.4);assert tick()==first+1,'Single step did not advance exactly one tick'
 command('speed8');time.sleep(.2);command('play');time.sleep(.4);assert tick()>first+2,'Resume did not advance'
 deadline=time.monotonic()+20
 while time.monotonic()<deadline:
  status=(session/'status.txt').read_text()
  assert not status.startswith('ERROR'),status
  if status=='COMPLETE':break
  time.sleep(.2)
 else:raise AssertionError('Replay completion timeout')
 print('PASS live game: pause, exact single step, resume, 8x playback, complete state agreement; final tick',tick())
finally:k.CloseHandle(h)
