"""Normalize retained FAA polygon geometry; no reconstruction from prose segments."""
import collections,datetime,hashlib,json,math,re
from acquire_boundaries import SERVICE

def name_key(value):
 return re.sub(r'\b(OCEANIC|CTA|FIR|ARTCC|CERAP|HIGH|LOW)\b','',value.upper()).strip()

def load_boundaries(root,facilities,arb_rows):
 manifest=json.loads((root/'data/boundaries/manifest.json').read_text())
 for entry in manifest:
  if hashlib.sha256((root/entry['file']).read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('Boundary checksum mismatch: '+entry['file'])
 service=json.loads((root/'data/raw/faa-boundary-service.json').read_text())
 description=service['description'];dates=re.search(r'Current Effective Date: 0901Z (\d{2} \w{3} \d{4}) to 0901Z (\d{2} \w{3} \d{4})',description)
 if not dates:raise ValueError('Boundary effective-date metadata changed')
 start,end=[datetime.datetime.strptime(d,'%d %b %Y').date().isoformat() for d in dates.groups()]
 geo=json.loads((root/'data/raw/faa-airspace-boundaries.geojson').read_text())
 names={name_key(r['LOCATION_NAME']):r['LOCATION_ID'] for r in arb_rows}
 facilities_by_id={identifier:f for f in facilities if f['feature_type']=='centers' or f['subtype']=='CERAP' for identifier in f['identifiers']}
 facilities_by_name={name_key(f['name']):f for f in facilities if f['feature_type']=='centers' or f['subtype']=='CERAP'}
 output=[]
 for f in geo['features']:
  a=f['properties'];ident=a.get('IDENT') or a.get('ICAO_ID');record=facilities_by_id.get(ident) or facilities_by_id.get(a.get('ICAO_ID')) or facilities_by_name.get(name_key(a['NAME']));center=record['identifiers'][0] if record else names.get(name_key(a['NAME']))
  if not center:raise ValueError('Unmatched FAA boundary: '+a['NAME'])
  g=f['geometry']
  if g['type'] not in ['Polygon','MultiPolygon']:raise ValueError('Unexpected geometry')
  polygons=[g['coordinates']] if g['type']=='Polygon' else g['coordinates']
  for rings in polygons:
   for ring in rings:
    if len(ring)<4 or ring[0][:2]!=ring[-1][:2]:raise ValueError('Open FAA polygon ring: '+a['NAME'])
    for p in ring:
     if not all(math.isfinite(v) for v in p[:2]) or abs(p[0])>180 or abs(p[1])>90:raise ValueError('Invalid coordinate')
  def xy(coords):return coords[:2] if isinstance(coords[0],(int,float)) else [xy(c) for c in coords]
  local=a['LOCAL_TYPE'];alt='HIGH' if local=='ARTCC_H' else 'LOW' if local=='ARTCC_L' else 'BOTH'
  properties=dict(center=center,source_identifier=ident,center_feature_id=record['feature_id'] if record else None,name=a['NAME'].strip().title(),altitude=alt,boundary_type=a['TYPE_CODE'],local_type=local,effective_date=start,valid_until=end,source_object_id=a['OBJECTID'],source_url=SERVICE+'/0/'+str(a['OBJECTID']),source_publisher='Federal Aviation Administration · Aeronautical Information Services',upper={k:a[k] for k in ['UPPER_VAL','UPPER_UOM','UPPER_CODE','UPPER_DESC']},lower={k:a[k] for k in ['LOWER_VAL','LOWER_UOM','LOWER_CODE','LOWER_DESC']},source_attributes=a,note='FAA chart-published polygon. Center/flight-information-region boundary, not an internal controller sector or live configuration.')
  output.append(dict(type='Feature',geometry={'type':g['type'],'coordinates':xy(g['coordinates'])},properties=properties))
 ids={p['properties']['center'] for p in output}
 if not {'ZSE','ZLC','ZBW','ZWY','ZSU'}<=ids:raise ValueError('Missing required FAA center regions')
 return output,manifest,dict(source=SERVICE,effective_date=start,valid_until=end,source_polygon_records=len(output),centers=sorted(ids),geometry='FAA-published closed polygons; no prose-derived segments',variants=len({(f['properties']['center'],f['properties']['altitude'],f['properties']['boundary_type']) for f in output}))
