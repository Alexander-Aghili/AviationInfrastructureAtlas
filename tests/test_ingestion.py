import unittest,json,sys,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from import_faa import coords,dms,seconds
from release import retained_cycle,csv_dir
RAW=ROOT/'data/raw';CYCLE=retained_cycle(RAW)
class IngestionTests(unittest.TestCase):
 def test_coordinate_forms(self):
  self.assertAlmostEqual(dms('075-27-54.660W'),-75.465183333)
  self.assertAlmostEqual(seconds('271674.660W'),-75.465183333)
  self.assertIsNone(coords({'LAT_DECIMAL':'91','LONG_DECIMAL':'0'}))
  self.assertIsNone(coords({'LAT_DECIMAL':'nan','LONG_DECIMAL':'0'}))
 def test_release_integrity(self):
  r=json.loads((ROOT/'public/data/facilities.json').read_text());a=json.loads((ROOT/'public/data/audit.json').read_text())
  self.assertEqual(len(r),a['records']);self.assertEqual(len({f['feature_id'] for f in r}),len(r))
  self.assertEqual(sum(f['geometry'] is not None for f in r),a['mapped'])
  for f in r:
   self.assertTrue(f['sources'])
   if f['geometry'] and f['source']['table'] in ['RDR','ATC_BASE']:self.assertGreater(len(f['sources']),1)
   if f['geometry']:
    lon,lat=f['geometry']['coordinates'];self.assertLessEqual(abs(lon),180);self.assertLessEqual(abs(lat),90)
 def test_artcc_sample(self):
  r=json.loads((ROOT/'public/data/facilities.json').read_text());f=next(f for f in r if f['feature_type']=='centers' and 'ZAB' in f['identifiers'])
  self.assertAlmostEqual(f['geometry']['coordinates'][1],dms('35-10-24.150N'))
  self.assertAlmostEqual(f['geometry']['coordinates'][0],dms('106-34-03.080W'))

 def test_supplemental_evidence(self):
  r=json.loads((ROOT/'public/data/facilities.json').read_text())
  tam=next(f for f in r if f['feature_id']=='JPL_RADAR:MILLVALLEY')
  self.assertEqual(tam['equipment_model'],'ARSR-4');self.assertEqual(tam['model_date'],'2015-05-26')
  self.assertAlmostEqual(tam['geometry']['coordinates'][1],37.923889)
  nct=next(f for f in r if f['source']['table']=='ATC_BASE' and 'NCT' in f['identifiers'])
  self.assertEqual(nct['subtype'],'TRACON');self.assertEqual(nct['location_accuracy'],'Address estimate')
  self.assertEqual(nct['geometry']['coordinates'],[-121.257064501901,38.559587845887]);self.assertIsNone(nct['equipment_geometry'])
  self.assertTrue(any('facility address' in s['fields'] for s in nct['sources']))
  rno=next(f for f in r if f['source']['table']=='RDR' and f['identifiers'][0]=='RNO')
  self.assertEqual(rno['equipment_model'],'ASR-11');self.assertEqual(rno['location_date'],'2017-11-02')
  self.assertAlmostEqual(rno['geometry']['coordinates'][1],39+30/60+4.55/3600)

 def test_faa_boundary_polygons(self):
  import hashlib
  boundaries=json.loads((ROOT/'public/data/boundaries.geojson').read_text())['features']
  source=json.loads((ROOT/'public/data/audit.json').read_text())['boundary_source']
  self.assertEqual(len(boundaries),source['source_polygon_records']);self.assertGreaterEqual(len(boundaries),60)
  for f in boundaries:
   self.assertEqual(f['properties']['effective_date'],source['effective_date'])
   rings=f['geometry']['coordinates'] if f['geometry']['type']=='Polygon' else [r for p in f['geometry']['coordinates'] for r in p]
   for ring in rings:self.assertEqual(ring[0],ring[-1])
  ids={f['properties']['center'] for f in boundaries}
  self.assertTrue({'ZSE','ZLC','ZBW','ZWY','ZSU'}<=ids)
  boston=next(f for f in boundaries if f['properties']['center']=='ZBW' and f['properties']['altitude']=='HIGH')
  self.assertGreater(len(boston['geometry']['coordinates'][0]),3000)
  for entry in json.loads((ROOT/'data/boundaries/manifest.json').read_text()):self.assertEqual(hashlib.sha256((ROOT/entry['file']).read_bytes()).hexdigest(),entry['sha256'])

 def test_nationwide_towers_and_surface_inventory(self):
  import csv
  records=json.loads((ROOT/'public/data/facilities.json').read_text())
  with (csv_dir(RAW,CYCLE,'RDR')/'RDR.csv').open() as file:
   raw=[r for r in csv.DictReader(file) if r['COUNTRY_CODE']=='US']
  self.assertEqual(len(raw),sum(f['source']['table']=='RDR' for f in records))
  towers=[f for f in records if f['feature_type']=='towers']
  with (csv_dir(RAW,CYCLE,'ATC')/'ATC_BASE.csv').open(encoding='utf-8-sig') as file:
   self.assertEqual(len(towers),sum(r['COUNTRY_CODE']=='US' and r['FACILITY_TYPE'].startswith('ATCT') for r in csv.DictReader(file)))
  self.assertEqual(sum(f['location_accuracy']=='Address estimate' for f in towers),0)
  self.assertTrue(all(f['location_accuracy'] in ['Airport reference only'] for f in towers if f['geometry']))
  surface=[f for f in records if f['source']['table']=='FAA_SURFACE']
  self.assertEqual(sum(f['subtype']=='ASDE-X' for f in surface),35)
  self.assertEqual(sum(f['subtype']=='ASSC' for f in surface),9)
  self.assertTrue(all(f['geometry'] and f['equipment_geometry'] is None and f['location_accuracy']=='Airport reference only' for f in surface))
  sfo=next(f for f in surface if 'SFO' in f['identifiers'])
  self.assertEqual(sfo['equipment_model'],'ASSC')
  tower=next(f for f in towers if 'SFO' in f['identifiers'])
  self.assertTrue(any(r['identifier']=='NCT' for r in tower['relationships']))
  self.assertEqual(tower['location_accuracy'],'Airport reference only')
  self.assertIsNone(tower['equipment_geometry'])
  self.assertEqual(tower['geometry'],sfo['geometry'])

 def test_estimated_markers_are_airport_references_only(self):
  import csv
  records=json.loads((ROOT/'public/data/facilities.json').read_text())
  with (csv_dir(RAW,CYCLE,'APT')/'APT_BASE.csv').open() as file:
   airports={r['ARPT_ID']:r for r in csv.DictReader(file) if r['COUNTRY_CODE']=='US'}
  # Only TRACON buildings use labeled estimates of their FAA-published address; directory geocodes come first.
  located={x['identifier']:x['coordinates'] for x in json.loads((ROOT/'data/supplemental/tracon_locations.json').read_text()) if x['coordinates']}
  located|={x['identifier']:x['coordinates'] for x in json.loads((ROOT/'data/supplemental/control_locations.json').read_text()) if x['coordinates']}
  estimates=[f for f in records if f['location_accuracy']=='Address estimate']
  self.assertEqual({f['identifiers'][0] for f in estimates},set(located));self.assertGreaterEqual(len(estimates),21)
  for f in estimates:
   self.assertEqual((f['feature_type'],f['subtype']),('control','TRACON'))
   self.assertEqual(f['geometry']['coordinates'],located[f['identifiers'][0]])
   self.assertTrue(f['attributes']['FACILITY_ADDRESS'])
   self.assertTrue(any('estimated map position' in s['fields'] for s in f['sources']))
   self.assertTrue(any('facility address' in s['fields'] and s['publisher'].startswith('Federal Aviation') for s in f['sources']))
  d21=next(f for f in records if f['source']['table']=='ATC_BASE' and f['identifiers'][0]=='D21')
  self.assertIsNone(d21['geometry']);self.assertIn('Building 801',d21['attributes']['FACILITY_ADDRESS'])
  references=[f for f in records if f['location_accuracy']=='Airport reference only']
  self.assertGreater(len(references),900)
  for f in references:
   r=airports[f['identifiers'][0]]
   self.assertEqual(f['geometry']['coordinates'],[float(r['LONG_DECIMAL']),float(r['LAT_DECIMAL'])])
   self.assertIsNone(f['equipment_geometry'])
   self.assertTrue(any('map reference point (not equipment position)' in s['fields'] for s in f['sources']))
  oak=next(f for f in records if f['source']['table']=='RDR' and 'OAK' in f['identifiers'] and f['facility_class']=='ASR')
  self.assertEqual(oak['location_accuracy'],'Published antenna coordinates')
