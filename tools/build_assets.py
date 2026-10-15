"""Slice generated atlases and integrate them with IKEMEN's bundled KFM mechanics.
The original SFF palette/data tables and effects are preserved; fighter images are PNG32.
"""
from pathlib import Path
from PIL import Image
import struct,io,re,shutil,json
ROOT=Path(__file__).resolve().parents[1]
AS=ROOT/'android/assets'
ART=ROOT/'art'

def png(im):
 b=io.BytesIO();im.save(b,format='PNG');return struct.pack('<I',im.width*im.height*4)+b.getvalue()

def replace_sff(source,target,replacements):
 b=bytearray(Path(source).read_bytes());off,n=struct.unpack_from('<II',b,36);lo=struct.unpack_from('<I',b,52)[0]
 seen=set()
 for i in range(n):
  h=off+28*i;g,num=struct.unpack_from('<HH',b,h)
  if (g,num) not in replacements:continue
  im,ax,ay=replacements[g,num];im=im.convert('RGBA');blob=png(im);pos=len(b)-lo;b.extend(blob)
  struct.pack_into('<HHHHhhHBBIIHH',b,h,g,num,im.width,im.height,ax,ay,0,12,32,pos,len(blob),0,0);seen.add((g,num))
 # Additional sprites can be inserted via a new sprite-header table at end.
 extra=[]
 for (g,num),(im,ax,ay) in replacements.items():
  if (g,num) in seen:continue
  im=im.convert('RGBA');blob=png(im);pos=len(b)-lo;b.extend(blob)
  extra.append(struct.pack('<HHHHhhHBBIIHH',g,num,im.width,im.height,ax,ay,0,12,32,pos,len(blob),0,0))
 if extra:
  headers=bytes(b[off:off+n*28])+b''.join(extra);off2=len(b);b.extend(headers);struct.pack_into('<II',b,36,off2,n+len(extra))
 struct.pack_into('<I',b,56,len(b)-lo)
 # No translated data in this bundled SFF; keep its pointer after ldata.
 if struct.unpack_from('<I',b,64)[0]==0:struct.pack_into('<I',b,60,len(b))
 Path(target).write_bytes(b)

def atlas(name):
 im=Image.open(ART/f'{name}-sheet.png').convert('RGBA');frames=[]
 # Generated atlases have slight row-spacing differences. Cut at actual alpha gaps.
 alpha=im.getchannel('A');rows=[0]
 for target in [im.height//4,im.height//2,im.height*3//4]:
  candidates=[]
  for yy in range(target-40,target+41):
   if not alpha.crop((0,yy,im.width,yy+1)).point(lambda v: 255 if v>128 else 0).getbbox():candidates.append(yy)
  runs=[]
  for yy in candidates:
   if not runs or yy>runs[-1][-1]+1:runs.append([yy])
   else:runs[-1].append(yy)
  cut=min(runs,key=lambda r:abs((r[0]+r[-1])/2-target)) if runs else [target]
  rows.append((cut[0]+cut[-1])//2)
 rows.append(im.height)
 print(name,'atlas row boundaries',rows)
 for i in range(16):
  box=(i%4*im.width//4,rows[i//4],(i%4+1)*im.width//4,rows[i//4+1])
  f=im.crop(box);f=f.resize((104,104),Image.Resampling.NEAREST)
  # Feet and attack origin are aligned per pose; all frames use the same scale.
  bbox=f.getbbox()
  bottom=bbox[3] if bbox else 120
  center=(bbox[0]+bbox[2])//2 if bbox else 64
  # Attack frames' origin belongs to the supporting foot, rather than the extended hand/foot.
  if i in (9,10):center=32
  frames.append((f,center,bottom))
 out=ART/name;out.mkdir(exist_ok=True)
 for i,(f,ax,ay) in enumerate(frames):f.save(out/f'{i:02}.png')
 return frames

def choose(g,num):
 if g==0:return num%4
 if g in (5,):return 2
 if g in (6,11,120,121,122):return 11
 if g in (20,21,100):return 4+num%4
 if g in (41,42,43):return 12
 if g in (181,):return 15
 if g in (191,192):return 2
 if 5000<=g<5030:return 13
 if 5030<=g<5100:return 14
 if g==5300:return 13
 if g in (230,240,400,410,430,440,630,640):return 8 if num==0 else 10
 if g in (200,210,600,610,800,1000,1050,1052,1055,1100,1210,1300,1320,1340,1400):return 8 if num==0 else 9
 return 2

def fighter(slug,display):
 src=ROOT/'package/assets/chars/kfm';out=AS/'chars'/slug
 if out.exists():shutil.rmtree(out)
 shutil.copytree(src,out)
 frames=atlas(slug)
 b=(src/'kfm.sff').read_bytes();off,n=struct.unpack_from('<II',b,36);repl={}
 for i in range(n):
  g,num=struct.unpack_from('<HH',b,off+i*28)
  if g<9000:repl[g,num]=frames[choose(g,num)]
 # Portrait assets use engine's standard dimensions.
 base=frames[2][0];bb=base.getbbox();person=base.crop(bb)
 portrait=Image.new('RGBA',(120,140));person.thumbnail((116,136),Image.Resampling.NEAREST);portrait.alpha_composite(person,((120-person.width)//2,140-person.height))
 repl[9000,1]=(portrait,0,0)
 face=base.crop((36,0,92,56)).resize((25,25),Image.Resampling.NEAREST)
 repl[9000,0]=(face,0,0)
 replace_sff(src/'kfm.sff',out/'kfm.sff',repl)
 d=(out/'kfm.def').read_text(encoding='utf-8-sig')
 d=re.sub(r'(?m)^name\s*=.*',f'name = "{display}"',d);d=re.sub(r'(?m)^displayname\s*=.*',f'displayname = "{display}"',d)
 d=re.sub(r'(?m)^author\s*=.*','author = "Neon Fighters; mechanics based on Elecbyte KFM"',d)
 d=re.sub(r'(?m)^(intro.storyboard|ending.storyboard|ai)\s*=.*',r'; \g<0>',d)
 (out/f'{slug}.def').write_text(d);(out/'kfm.def').unlink()
 c=(out/'kfm.cns').read_text(encoding='utf-8-sig')
 # Remove example wood board explods and male voice samples, while retaining hit effects and common sounds.
 c=re.sub(r'(?ims)^\[State 191, (?:Wood [12]|Snd [12])\].*?(?=^\[)', '',c)
 c=re.sub(r'(?ims)^\[State[^\]]*\]\s*(?:;[^\n]*)?\s*type\s*=\s*PlaySnd\b.*?(?=^\[|\Z)', '',c)
 c=re.sub(r'(?m)^victory\d+\s*=.*','',c)
 c+='\n[Quotes]\nvictory1 = "A noite ainda e nossa."\n'
 (out/'kfm.cns').write_text(c)
 # Short clean intro without board-breaking animation.
 a=(out/'kfm.air').read_text(encoding='utf-8-sig')
 a=re.sub(r'(?ims)^\[Begin Action 190\].*?(?=^\[Begin Action|\Z)','[Begin Action 190]\n0,2,0,0,30\n\n',a)
 (out/'kfm.air').write_text(a)
 # Alternative single-button command shortcuts are comfortable on touch controls.
 cmd=(out/'kfm.cmd').read_text(encoding='utf-8-sig')
 pos=cmd.lower().find('[statedef -1]')
 cmd=cmd[:pos]+'[Command]\nname = "TripleKFPalm"\ncommand = z\ntime = 1\n\n[Command]\nname = "SmashKFUpper"\ncommand = c\ntime = 1\n\n'+cmd[pos:]
 (out/'kfm.cmd').write_text(cmd)
 return len(repl)

if __name__=='__main__':
 for name,display in [('ayla','Ayla'),('rubi','Rubi')]:print(name,fighter(name,display),'sprites integrated')
 stage=Image.open(ART/'stage.png').convert('RGBA').resize((640,480),Image.Resampling.NEAREST)
 # Use an existing valid SFF as a container; stage refers only to our added group.
 replace_sff(ROOT/'package/assets/stages/kfm.sff',AS/'stages/neon-garden.sff',{(8000,0):(stage,0,0)})
 (AS/'stages/neon-garden.def').write_text('''[Info]
name = "Jardim Neon"
displayname = "Jardim Neon"
author = "Neon Fighters"
mugenversion = 1.1
[Camera]
startx = 0
starty = 0
boundleft = 0
boundright = 0
boundhigh = -20
boundlow = 0
verticalfollow = .1
tension = 50
[PlayerInfo]
p1startx = -70
p1starty = 0
p2startx = 70
p2starty = 0
p1facing = 1
p2facing = -1
leftbound = -145
rightbound = 145
[Bound]
screenleft = 15
screenright = 15
[StageInfo]
zoffset = 200
autoturn = 1
resetBG = 1
localcoord = 320,240
[Shadow]
intensity = 130
color = 15,5,35
yscale = .25
[Reflection]
intensity = 0
[Music]
[BGdef]
spr = neon-garden.sff
bgclearcolor = 12,8,30
[BG Rooftop]
type = normal
spriteno = 8000,0
start = -160,0
delta = 1,1
scalestart = .5,.5
''')
 (AS/'data/select.def').write_text('''[Characters]
ayla, stages/neon-garden.def, order=1
rubi, stages/neon-garden.def, order=1
randomselect
[ExtraStages]
stages/neon-garden.def
[Options]
arcade.maxmatches = 2,0,0,0,0,0,0,0,0,0
team.maxmatches = 2,0,0,0,0,0,0,0,0,0
''')
 # Reskin the title background while preserving the bundled menu layout and fonts.
 s=AS/'data/ikemen1/system.def';text=s.read_text(encoding='utf-8-sig')
 text=text.replace('name = IKEMEN1','name = Neon Fighters')
 titles={'ARCADE':'ARCADE','SINGLE MODE':'SOLO','VS MODE':'VERSUS','QUICK MATCH':'LUTA RAPIDA','PRACTICE':'TREINAR','TRAINING':'TREINO','WATCH MODE':'ASSISTIR','CPU MATCH':'CPU VS CPU','OPTIONS':'OPCOES','EXIT':'SAIR','BACK':'VOLTAR'}
 for a,b in titles.items():text=re.sub(r'(?m)^(menu.itemname[^=]*=\s*)'+re.escape(a)+r'\s*$',lambda m:m[1]+b,text)
 s.write_text(text)
 # Replace only the sky sprite so the existing motif composition remains valid.
 bg=Image.open(ART/'stage.png').convert('RGBA').resize((1280,720),Image.Resampling.NEAREST)
 replace_sff(ROOT/'package/assets/data/ikemen1/system.sff',AS/'data/ikemen1/system.sff',{(100,0):(bg,0,0)})
 files=sorted(str(p.relative_to(AS)) for p in AS.rglob('*') if p.is_file() and p.name!='manifest.txt')
 (AS/'manifest.txt').write_text('\n'.join(files)+'\n')
 print('Manifest:',len(files),'assets')
