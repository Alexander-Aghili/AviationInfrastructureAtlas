"""Retain official TRACON address sources and position evidence for data/supplemental/tracon_sources.json.

Addresses come from FAA Letters to Airmen letterheads and the FAA PIV service-center list.
Positions are either a unique Census address match or EPA Facility Registry Service coordinates,
as recorded per facility in tracon_sources.json. Both are labeled estimates, never surveys.
"""
import datetime,hashlib,json,pathlib,time,urllib.error,urllib.parse,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1];RAW=ROOT/'data/raw/tracon';SUPP=ROOT/'data/supplemental'
EPA='https://frs-public.epa.gov/ords/frs_public2/frs_rest_services.get_facilities?'
CENSUS='https://geocoding.geo.census.gov/geocoder/locations/address?'
def fetch(url,name):
    path=RAW/name
    for attempt in range(6):
        if path.exists():return path
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'AirwaysAtlas/1.0 public-source-import'})
            with urllib.request.urlopen(request,timeout=60) as response:path.write_bytes(response.read())
        except urllib.error.HTTPError as error:
            # EPA rate-limits bursts; back off rather than fail the acquisition.
            if error.code!=429 or attempt==5:raise
            time.sleep(5*2**attempt)
    return path
def main():
    RAW.mkdir(parents=True,exist_ok=True);now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    retained={};locations=[]
    for item in json.loads((SUPP/'tracon_sources.json').read_text()):
        for s in item['sources']:
            if s['url'] not in retained:
                retained[s['url']]=fetch(s['url'],'source-'+hashlib.sha256(s['url'].encode()).hexdigest()[:16]+('.pdf' if 'service-center-hours' in s['url'] else '.html'))
            s['file']=str(retained[s['url']].relative_to(ROOT))
        point=None;evidence=None
        if item['position']=='epa':
            url=EPA+urllib.parse.urlencode({'registry_id':item['epa_registry_id'],'output':'JSON'})
            path=fetch(url,f'epa-frs-{item["epa_registry_id"]}.json');facility=json.loads(path.read_text())['Results']['FRSFacility'][0]
            point=[float(facility['Longitude83']),float(facility['Latitude83'])]
            evidence={'title':f'EPA Facility Registry Service · {facility["RegistryId"]}','publisher':'US Environmental Protection Agency','url':url,'date':now[:10],'file':str(path.relative_to(ROOT)),
                      'role':'EPA Facility Registry Service coordinates (NAD83) for this FAA facility; collection method not stated'}
        elif item['position']=='census':
            url=CENSUS+urllib.parse.urlencode(item['census_address']|{'benchmark':'Public_AR_Current','format':'json'})
            path=fetch(url,f'census-{item["identifier"]}.json');matches=json.loads(path.read_text())['result']['addressMatches']
            # Ambiguous matches are rejected rather than resolved by choice.
            if len(matches)==1:point=[matches[0]['coordinates']['x'],matches[0]['coordinates']['y']]
            evidence={'title':'US Census Geocoder · address match','publisher':'US Census Bureau','url':url,'date':now[:10],'file':str(path.relative_to(ROOT)),
                      'role':'Census street-range estimate of the FAA-published facility address'}
        locations.append({**item,'coordinates':point,'position_evidence':evidence if point else None})
    (SUPP/'tracon_locations.json').write_text(json.dumps(locations,indent=1))
    files=sorted({str(p.relative_to(ROOT)) for p in RAW.iterdir()})+['data/supplemental/tracon_sources.json','data/supplemental/tracon_locations.json']
    (SUPP/'tracon-manifest.json').write_text(json.dumps([{'file':f,'sha256':hashlib.sha256((ROOT/f).read_bytes()).hexdigest(),'bytes':(ROOT/f).stat().st_size,'retrieved_at':now} for f in files],indent=1))
    print(f'{len(locations)} TRACON address records; {sum(bool(x["coordinates"]) for x in locations)} positioned; {len(retained)} source documents retained.')
if __name__=='__main__':main()
