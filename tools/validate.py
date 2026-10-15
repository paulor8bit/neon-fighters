from pathlib import Path
from PIL import Image
import struct,io,re
root=Path(__file__).resolve().parents[1];a=root/'android/assets'
manifest=(a/'manifest.txt').read_text().splitlines()
assert len(manifest)==len(set(manifest))
assert all((a/f).is_file() for f in manifest)
for name in ['ayla','rubi']:
 p=a/'chars'/name;b=(p/'kfm.sff').read_bytes();off,n=struct.unpack_from('<II',b,36);lo,to=struct.unpack_from('<I',b,52)[0],struct.unpack_from('<I',b,60)[0];keys=set();replaced=0
 for i in range(n):
  g,num,w,h,x,y,link,fmt,depth,pos,size,pal,flags=struct.unpack_from('<HHHHhhHBBIIHH',b,off+i*28);keys.add((g,num))
  if fmt==12 and size:
   start=(to if flags&1 else lo)+pos
   im=Image.open(io.BytesIO(b[start+4:start+size]));im.load();assert im.size==(w,h);assert im.mode=='RGBA';replaced+=1
 air=(p/'kfm.air').read_text()
 missing=set()
 for line in air.splitlines():
  m=re.match(r'^\s*(-?\d+)\s*,\s*(-?\d+)\s*,',line)
  if m:
   k=tuple(map(int,m.groups()))
   if k[0]>=0 and k not in keys:missing.add(k)
 assert not missing,(name,missing)
 assert '[Statedef -1]' in (p/'kfm.cmd').read_text()
 assert not re.search(r'type\s*=\s*Explod.*?anim\s*=\s*19[12]',(p/'kfm.cns').read_text(),re.S)
 print(name,n,'sprite records;',replaced,'valid PNG sprites; all AIR references present')
print('Asset manifest:',len(manifest),'valid files')
