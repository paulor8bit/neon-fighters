"""Build the versioned game assets with the verified upstream Android runtime."""
from pathlib import Path
import argparse,getpass,hashlib,os,re,shutil,subprocess,urllib.request,zipfile
ROOT=Path(__file__).resolve().parents[1]
BASE='https://github.com/ikemen-engine/Ikemen-GO/releases/download/v1.0.0/'
ARCHIVE='Ikemen_GO-v1.0.0-android.zip'

def download(url,path):
 if not path.exists():
  tmp=path.with_suffix(path.suffix+'.part')
  with urllib.request.urlopen(url,timeout=120) as response,tmp.open('wb') as out:shutil.copyfileobj(response,out)
  tmp.replace(path)
 return path

def fingerprint(assets):
 h=hashlib.sha256();main=assets/'external/script/main.lua'
 for p in sorted(assets.rglob('*')):
  if not p.is_file() or p.name=='manifest.txt' or p==main or 'save' in p.relative_to(assets).parts:continue
  h.update(str(p.relative_to(assets)).encode());h.update(p.read_bytes())
 script=re.sub(r'^-- Neon Fighters asset revision [^\n]*\n','',main.read_text())
 main.write_text('-- Neon Fighters asset revision '+h.hexdigest()+'\n'+script)
 manifest=sorted(str(p.relative_to(assets)) for p in assets.rglob('*') if p.is_file() and p.name!='manifest.txt')
 (assets/'manifest.txt').write_text('\n'.join(manifest)+'\n')

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--keystore',required=True,type=Path);parser.add_argument('--alias',required=True);args=parser.parse_args()
 if not args.keystore.is_file():parser.error('Keystore not found')
 cache=ROOT/'.cache';cache.mkdir(exist_ok=True)
 archive=download(BASE+ARCHIVE,cache/ARCHIVE)
 sums=download(BASE+'SHA256SUMS.txt',cache/'SHA256SUMS.txt').read_text()
 expected=next(line.split()[0] for line in sums.splitlines() if line.split()[-1].lstrip('*')==ARCHIVE)
 assert hashlib.sha256(archive.read_bytes()).hexdigest()==expected,'Upstream SHA-256 mismatch'
 apktool=os.environ.get('APKTOOL_JAR')
 if not apktool:apktool=str(download('https://github.com/iBotPeaches/Apktool/releases/download/v3.0.3/apktool_3.0.3.jar',cache/'apktool.jar'))
 aapt=os.environ.get('AAPT2') or shutil.which('aapt2');signer=os.environ.get('APKSIGNER') or shutil.which('apksigner')
 if not aapt or not signer:parser.error('aapt2 and apksigner must be installed')
 fingerprint(ROOT/'android/assets')
 stage=cache/'android-build'
 if stage.exists():shutil.rmtree(stage)
 stage.mkdir()
 for name in ['assets','res']:shutil.copytree(ROOT/'android'/name,stage/name)
 for name in ['AndroidManifest.xml','apktool.yml']:shutil.copy2(ROOT/'android'/name,stage/name)
 with zipfile.ZipFile(archive) as z:
  apk=cache/'upstream.apk';apk.write_bytes(z.read('ikemen-go.apk'))
 with zipfile.ZipFile(apk) as z:
  for name in z.namelist():
   if name.startswith('lib/') or re.fullmatch(r'classes\d*\.dex',name):
    if name.endswith('/'):continue
    target=stage/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(name))
 out=ROOT/'releases';out.mkdir(exist_ok=True);unsigned=out/'unsigned.apk';aligned=out/'aligned.apk';final=out/'Neon-Fighters.apk'
 subprocess.run(['java','-jar',apktool,'b','-f',str(stage),'--aapt',aapt,'-o',str(unsigned)],check=True)
 with zipfile.ZipFile(unsigned) as src,zipfile.ZipFile(aligned,'w') as dst:
  for info in src.infolist():
   if info.filename.startswith('META-INF/') and info.filename.endswith(('.RSA','.SF','.MF')):continue
   data=src.read(info.filename);info.extra=b''
   if info.compress_type==zipfile.ZIP_STORED:
    pad=(-(dst.fp.tell()+30+len(info.filename.encode())+4))%4
    info.extra=b'\xfe\xca'+pad.to_bytes(2,'little')+b'\0'*pad
   dst.writestr(info,data)
 env=os.environ.copy()
 if not env.get('NEON_KS_PASS'):env['NEON_KS_PASS']=getpass.getpass('Keystore password: ')
 if not env.get('NEON_KEY_PASS'):env['NEON_KEY_PASS']=env['NEON_KS_PASS']
 subprocess.run([signer,'sign','--ks',str(args.keystore.resolve()),'--ks-key-alias',args.alias,'--ks-pass','env:NEON_KS_PASS','--key-pass','env:NEON_KEY_PASS','--out',str(final),str(aligned)],env=env,check=True)
 subprocess.run([signer,'verify',str(final)],check=True)
 with zipfile.ZipFile(final) as z:
  assert z.testzip() is None
  for name in z.read('assets/manifest.txt').decode().splitlines():assert z.read('assets/'+name)==(ROOT/'android/assets'/name).read_bytes(),name
 (out/'SHA256SUMS.txt').write_text(hashlib.sha256(final.read_bytes()).hexdigest()+'  Neon-Fighters.apk\n')
 print('Verified APK:',final)
if __name__=='__main__':main()
