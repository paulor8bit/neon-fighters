from build_assets import ROOT,AS,ART,replace_sff
from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
import re,struct
font='/system/fonts/SourceSansPro-Bold.ttf'
# A small rasterized wordmark is rendered at low resolution for chunky arcade lettering.
logo=Image.new('RGBA',(250,65));d=ImageDraw.Draw(logo);f=ImageFont.truetype(font,36)
d.text((4,-2),'NEON',font=f,fill='#f6d7e1',stroke_width=1,stroke_fill='#151135')
d.text((58,25),'FIGHTERS',font=f,fill='#e7afc8',stroke_width=1,stroke_fill='#151135')
logo=logo.resize((500,130),Image.Resampling.NEAREST);logo.save(ART/'logo.png')
transparent=Image.new('RGBA',(1,1))
source=AS/'data/ikemen1/system.sff'
replace_sff(source,source,{(0,0):(logo,0,0),(0,1):(transparent,0,0),(0,2):(transparent,0,0),(0,3):(transparent,0,0)})
# Distinct app identity avoids overwriting a separate IKEMEN installation.
p=ROOT/'android/AndroidManifest.xml';s=p.read_text();s=s.replace('package="org.ikemen_engine.ikemen_go"','package="com.neonfighters.arcade"');p.write_text(s)
p=ROOT/'android/apktool.yml';s=p.read_text();s=re.sub(r'  maxSdkVersion:.*\n','',s);s=s.replace('versionName: 1.0','versionName: 0.1');p.write_text(s)
p=ROOT/'android/res/values/strings.xml';s=p.read_text().replace('I.K.E.M.E.N-Go','Neon Fighters');p.write_text(s)
# Launcher icon derived from the actual Ayla sprite.
face=Image.open(ART/'ayla/02.png').convert('RGBA')
icon=Image.new('RGBA',(192,192),'#40364f');portrait=face.crop((27,0,104,90)).resize((170,198),Image.Resampling.NEAREST);icon.alpha_composite(portrait,(11,0))
for p in (ROOT/'android/res').glob('mipmap*/*.png'):
 if p.name.startswith('ic_launcher'):
  with Image.open(p) as old:size=old.size
  icon.resize(size,Image.Resampling.NEAREST).save(p)
# Preview composition of the integrated stage and sprites. This is not a runtime screenshot.
bg=Image.open(ART/'stage.png').convert('RGBA').resize((960,720),Image.Resampling.NEAREST)
for name,x,flip in [('ayla',215,False),('rubi',590,True)]:
 im=Image.open(ART/name/'02.png').convert('RGBA').resize((312,312),Image.Resampling.NEAREST)
 if flip:im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
 bg.alpha_composite(im,(x-120,294))
d=ImageDraw.Draw(bg);f=ImageFont.truetype(font,26)
d.rectangle((24,30,390,47),fill='#f0bfd4');d.rectangle((570,30,936,47),fill='#c3b5e4')
d.text((24,50),'AYLA',font=f,fill='white');d.text((866,50),'RUBI',font=f,fill='white')
d.text((435,20),'99',font=ImageFont.truetype(font,44),fill='white')
d.rectangle((0,678,960,720),fill='#40364f');d.text((20,685),'NEON FIGHTERS  |  PREVIA DOS ASSETS',font=f,fill='#bbd6ef')
bg.convert('RGB').save(ART/'preview.jpg',quality=94)
files=sorted(str(p.relative_to(AS)) for p in AS.rglob('*') if p.is_file() and p.name!='manifest.txt');(AS/'manifest.txt').write_text('\n'.join(files)+'\n')
print('Branding and preview complete')

# The Android updater checks script CRCs, so tie the script revision to all game assets.
import hashlib
fingerprint=hashlib.sha256()
for asset in sorted(AS.rglob('*')):
 if not asset.is_file() or asset.name=='manifest.txt' or 'save' in asset.relative_to(AS).parts or asset==AS/'external/script/main.lua':continue
 fingerprint.update(str(asset.relative_to(AS)).encode());fingerprint.update(asset.read_bytes())
main=AS/'external/script/main.lua'
script=re.sub(r'^-- Neon Fighters asset revision [^\n]*\n','',main.read_text())
main.write_text('-- Neon Fighters asset revision '+fingerprint.hexdigest()+'\n'+script)
