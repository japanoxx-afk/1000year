"""Generate the portable recipe, including the shared fire-arrow balance change."""
import argparse, pathlib, hashlib, json
import pefile, keystone
parser=argparse.ArgumentParser()
parser.add_argument('--source',required=True)
parser.add_argument('--output',default='compat/portable.json')
args=parser.parse_args()
source=pathlib.Path(args.source).read_bytes()
assert hashlib.sha256(source).hexdigest()=='1b70b78e8ec040697fced744cbc5f0d2a7ff3477cce35fce3185200f031ceabf'
p=pefile.PE(data=source);b=bytearray(source);edits=[]
def patch(va,after,note):
 off=p.get_offset_from_rva(va-0x400000);before=bytes(b[off:off+len(after)])
 b[off:off+len(after)]=after
 edits.append(dict(Offset=off,Before=before.hex(),After=after.hex(),Note=note))
patch(0x48c580,bytes.fromhex('8b442404c7002e5c00008b442408c7002e5c0000b801000000c3'),'Portable paths')
patch(0x44fea0,bytes.fromhex('31c0c3'),'Skip legacy movies')
ks=keystone.Ks(keystone.KS_ARCH_X86,keystone.KS_MODE_32)
patch(0x401468,bytes(ks.asm('je 0x4013cf',0x401468)[0]),'Fire arrows double against siege engines and ships')
pathlib.Path(args.output).write_text(json.dumps(dict(SourceSHA256=hashlib.sha256(source).hexdigest(),OutputSHA256=hashlib.sha256(b).hexdigest(),Edits=edits),indent=2))
