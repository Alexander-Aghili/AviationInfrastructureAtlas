"""Fetch one NASR release into a staging directory; failed downloads never replace sources."""
import argparse,concurrent.futures,datetime,hashlib,json,pathlib,shutil,tempfile,urllib.request,zipfile
from release import BASE,csv_url,is_cycle,retained_cycle
ROOT=pathlib.Path(__file__).resolve().parents[1]
GROUPS=['NAV','RDR','ARB','COM','AWOS','ILS','ATC','APT']
def urls(cycle):return [csv_url(cycle,g) for g in GROUPS]+[BASE+cycle+'/'+f for f in ['AFF.zip','README.txt','Layout_Data/aff_rf.txt','Layout_Data/arb_rf.txt']]+[BASE+'TXT_to_CSV_Mapping.pdf']
def main(cycle=None):
 cycle=cycle or retained_cycle(ROOT/'data/raw')
 if not is_cycle(cycle):raise ValueError('Not a NASR 28-day effective date: '+cycle)
 with tempfile.TemporaryDirectory(dir=ROOT/'data') as tmp:
  stage=pathlib.Path(tmp)
  def fetch(url):
   request=urllib.request.Request(url,headers={'User-Agent':'AirwaysAtlas/1.0 public-source-import'})
   with urllib.request.urlopen(request,timeout=90) as response:content=response.read()
   # Layout files share names across folders; keep the published basename like earlier releases.
   path=stage/url.rsplit('/',1)[-1];path.write_bytes(content)
   if path.suffix=='.zip':
    with zipfile.ZipFile(path) as z:
     if z.testzip():raise ValueError('Archive checksum failed')
     for member in z.infolist():
      target=(path.with_suffix('')/member.filename).resolve()
      if not target.is_relative_to(stage.resolve()):raise ValueError('Unsafe archive path')
     z.extractall(path.with_suffix(''))
   return {'url':url,'file':'data/raw/'+path.name,'sha256':hashlib.sha256(content).hexdigest(),'bytes':len(content),'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cycle':cycle}
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:manifest=list(executor.map(fetch,urls(cycle)))
  (stage/'manifest.json').write_text(json.dumps(manifest,indent=2))
  # Everything except the previous NASR files is independent evidence and carries over unchanged.
  raw=ROOT/'data/raw';backup=ROOT/'data/raw.previous'
  previous=set()
  if (raw/'manifest.json').exists():
   for entry in json.loads((raw/'manifest.json').read_text()):
    name=pathlib.Path(entry['file']).name;previous|={name,pathlib.Path(name).stem if name.endswith('.zip') else name}
  for original in raw.iterdir() if raw.exists() else []:
   if original.name in previous or original.name=='manifest.json' or (stage/original.name).exists():continue
   (shutil.copytree if original.is_dir() else shutil.copy2)(original,stage/original.name)
  if backup.exists():shutil.rmtree(backup)
  if raw.exists():raw.rename(backup)
  try:shutil.move(str(stage),str(raw))
  except Exception:
   if backup.exists():backup.rename(raw)
   raise
 # Airport reference points come from this release's APT file.
 (ROOT/'data/supplemental/airport-reference-manifest.json').write_text(json.dumps([{k:e[k] for k in ['file','url','sha256','bytes','retrieved_at']} for e in manifest if e['url']==csv_url(cycle,'APT')],indent=2))
 print(f'NASR cycle {cycle} acquired; original files, layouts and checksums retained.')
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cycle',help='NASR effective date (YYYY-MM-DD); defaults to the retained cycle')
 main(parser.parse_args().cycle)
