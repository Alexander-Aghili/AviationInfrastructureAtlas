import unittest,json,sys,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from import_faa import coords,dms,seconds
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
  self.assertTrue(any(s['publisher']=='US Census Bureau' for s in nct['sources']))
  rno=next(f for f in r if f['source']['table']=='RDR' and f['identifiers'][0]=='RNO')
  self.assertEqual(rno['equipment_model'],'ASR-11');self.assertEqual(rno['location_date'],'2017-11-02')
  self.assertAlmostEqual(rno['geometry']['coordinates'][1],39+30/60+4.55/3600)
