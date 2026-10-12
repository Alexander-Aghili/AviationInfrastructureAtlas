"""Geocode only numeric street addresses explicitly listed for FAA tower facilities.
Locations are street-range address estimates, never airport/tower coordinates.
"""
import concurrent.futures,csv,datetime,hashlib,json,pathlib,re,urllib.parse,urllib.request
from release import retained_cycle,csv_dir
ROOT=pathlib.Path(__file__).resolve().parents[1];RAW=ROOT/'data/raw'
DIRECTORY='https://www.faa.gov/sites/faa.gov/files/service-center-list-12.19.23.pdf'
def directory_addresses():
 valid={r['FACILITY_ID'] for r in csv.DictReader((csv_dir(RAW,retained_cycle(RAW),'ATC')/'ATC_BASE.csv').open()) if r['COUNTRY_CODE']=='US' and r['FACILITY_TYPE'].startswith('ATCT')}
 lines=[re.split(r'\s{2,}',line.strip().lstrip('\f').strip())[0] for line in (RAW/'faa-service-centers.txt').read_text().splitlines() if line.strip()]
 found={}
 for i,line in enumerate(lines):
  if not re.search(r'ATCT|\bTower\b',line,re.I):continue
  match=re.search(r'\(([A-Z0-9]{3,4})(?:\s+ATCT)?\)',line)
  if not match or match[1] not in valid:continue
  street=None
  for following in lines[i+1:i+7]:
   if 'ATCT' in following or 'Facility Location' in following:break
   city=re.fullmatch(r'(.+?),\s*([A-Z]{2})\s+(\d{5})(?:-\d{4})?',following)
   if city:
    if street:found[match[1]]=dict(identifier=match[1],street=street,city=city[1],state=city[2],zip=city[3],source_heading=line)
    break
   if street is None and re.match(r'^\d+\s+\S',following):street=following
 return list(found.values())
def main():
 addresses=directory_addresses();entries=[];now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 def fetch(item):
  url='https://geocoding.geo.census.gov/geocoder/locations/address?'+urllib.parse.urlencode({k:item[k] for k in ['street','city','state','zip']}|{'benchmark':'Public_AR_Current','format':'json'})
  path=RAW/('geocode-tower-'+item['identifier']+'.json')
  try:
   content=path.read_bytes() if path.exists() else urllib.request.urlopen(url,timeout=20).read();reply=json.loads(content)
   path.write_bytes(content);matches=reply.get('result',{}).get('addressMatches',[])
   # Reject ambiguous matches instead of silently choosing a street.
   coords=matches[0]['coordinates'] if len(matches)==1 else None
   return {**item,'address':f"{item['street']}, {item['city']}, {item['state']} {item['zip']}",'coordinates':[coords['x'],coords['y']] if coords else None,'url':url,'retrieved_at':now,'response_file':str(path.relative_to(ROOT)),'match_status':'matched' if coords else 'no unique match'}
  except Exception as error:return {**item,'coordinates':None,'url':url,'retrieved_at':now,'match_status':'request failed','error':str(error)}
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:entries=list(pool.map(fetch,addresses))
 output=ROOT/'data/supplemental/tower_locations.json';output.write_text(json.dumps(entries,indent=2))
 manifest=[]
 for file,url in [('data/raw/faa-service-centers.pdf',DIRECTORY),('data/raw/faa-service-centers.txt',DIRECTORY),(str(output.relative_to(ROOT)),DIRECTORY)]+[(x['response_file'],x['url']) for x in entries if x.get('response_file')]:
  p=ROOT/file;manifest.append(dict(file=file,url=url,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size,retrieved_at=now))
 (ROOT/'data/supplemental/tower-manifest.json').write_text(json.dumps(manifest,indent=2))
 print(f'{len(addresses)} FAA tower street addresses; {sum(bool(x["coordinates"]) for x in entries)} unique Census address estimates.')
if __name__=='__main__':main()
