"""Map documented airport deployments with explicit reference points, never antenna positions."""
import csv
from supplemental import source
from release import retained_cycle,csv_dir,csv_url
def add_airport_references(features,raw):
    cycle=retained_cycle(raw)
    with (csv_dir(raw,cycle,'APT')/'APT_BASE.csv').open(encoding='utf-8-sig') as file:
        airports={r['ARPT_ID']:r for r in csv.DictReader(file) if r['COUNTRY_CODE']=='US'}
    count=0
    for f in features:
        is_airport_radar=f['source']['table']=='RDR' and f['attributes'].get('FACILITY_TYPE')=='AIRPORT'
        if f['geometry'] or not(f['feature_type']=='towers' or f['source']['table']=='FAA_SURFACE' or is_airport_radar):continue
        r=airports.get(f['identifiers'][0])
        if not r or (f['state'] and f['state']!=r['STATE_CODE']):continue
        # Tower SITE_NO must agree: identifiers alone cannot relocate a different facility.
        if f['feature_type']=='towers' and f['attributes'].get('SITE_NO')!=r['SITE_NO']:continue
        point=[float(r['LONG_DECIMAL']),float(r['LAT_DECIMAL'])]
        f['geometry']={'type':'Point','coordinates':point}
        f['equipment_geometry']=None
        f['coordinate_role']='Airport reference point only; equipment position unknown'
        f['location_accuracy']='Airport reference only'
        f['location_date']=r['POSITION_SRC_DATE'] or cycle
        f['quality']['mapped']=True
        f['quality']['review_notes'].append('Map reference is the FAA airport reference point, not the tower building or any sensor antenna.')
        f['attributes']['MAP_REFERENCE']='FAA airport reference point; equipment coordinates not supplied'
        f['sources'].append(source('FAA NASR · airport reference point','Federal Aviation Administration',csv_url(cycle,'APT'),cycle,['airport identity','map reference point (not equipment position)'],r['ARPT_ID']))
        count+=1
    return count
