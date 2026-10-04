"""Re-fetch the pinned release into a staging directory; failed downloads never replace sources."""
import concurrent.futures,datetime,hashlib,json,pathlib,shutil,tempfile,urllib.request,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE='https://nfdc.faa.gov/webContent/28DaySub/'
URLS=[BASE+'extra/01_Oct_2026_'+g+'_CSV.zip' for g in ['NAV','RDR','ARB','COM','AWOS','ILS','ATC']]+[BASE+'2026-10-01/'+f for f in ['AFF.zip','README.txt','Layout_Data/aff_rf.txt','Layout_Data/arb_rf.txt']]+[BASE+'TXT_to_CSV_Mapping.pdf']
def main():
 with tempfile.TemporaryDirectory(dir=ROOT/'data') as tmp:
  stage=pathlib.Path(tmp)
  def fetch(url):
   request=urllib.request.Request(url,headers={'User-Agent':'AirwaysAtlas/1.0 public-source-import'})
   with urllib.request.urlopen(request,timeout=90) as response:content=response.read()
   path=stage/url.rsplit('/',1)[-1];path.write_bytes(content)
   if path.suffix=='.zip':
    with zipfile.ZipFile(path) as z:
     if z.testzip():raise ValueError('Archive checksum failed')
     for member in z.infolist():
      target=(path.with_suffix('')/member.filename).resolve()
      if not target.is_relative_to(stage.resolve()):raise ValueError('Unsafe archive path')
     z.extractall(path.with_suffix(''))
   return {'url':url,'file':'data/raw/'+path.name,'sha256':hashlib.sha256(content).hexdigest(),'bytes':len(content),'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cycle':'2026-10-01'}
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:manifest=list(executor.map(fetch,URLS))
  (stage/'manifest.json').write_text(json.dumps(manifest,indent=2))
  # Supplemental evidence is independent of the pinned NASR acquisition.
  for entry in json.loads((ROOT/'data/supplemental/manifest.json').read_text()):
   original=ROOT/entry['file']
   if original.parent==ROOT/'data/raw':shutil.copy2(original,stage/original.name)
  raw=ROOT/'data/raw';backup=ROOT/'data/raw.previous'
  if backup.exists():shutil.rmtree(backup)
  if raw.exists():raw.rename(backup)
  try:shutil.move(str(stage),str(raw))
  except Exception:
   if backup.exists():backup.rename(raw)
   raise
  print('Pinned cycle acquired; original files, layouts and checksums retained.')
if __name__=='__main__':main()
