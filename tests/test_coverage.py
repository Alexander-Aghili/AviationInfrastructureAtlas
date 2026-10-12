import unittest,sys,pathlib
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from coverage_model import visibility,horizon_range_m,destination,bearing_distance,FT
class CoverageModelTests(unittest.TestCase):
 def test_flat_terrain_matches_radar_horizon(self):
  ranges=np.arange(100,200_000,100.0);terrain=np.zeros((4,len(ranges)))
  seen=visibility(ranges,terrain,20.0,[1000*FT])[0]
  last=ranges[seen[0]].max()
  self.assertAlmostEqual(last,horizon_range_m(20,1000*FT),delta=150)
  self.assertTrue((seen==seen[0]).all())
  self.assertAlmostEqual(horizon_range_m(20,1000*FT)/1000,90.4,delta=0.2)
 def test_ridge_shadows_low_targets_then_targets_reemerge(self):
  ranges=np.arange(100,100_000,100.0);terrain=np.zeros((1,len(ranges)))
  terrain[0,(ranges>=20_000)&(ranges<=21_000)]=600.0
  low,high=visibility(ranges,terrain,20.0,[300.0,3000.0])
  behind=(ranges>21_000)&(ranges<40_000)
  self.assertTrue(low[0,ranges<20_000].all());self.assertFalse(low[0,behind].any())
  self.assertTrue(high[0,ranges>30_000][:100].all())
 def test_geodesy_round_trip(self):
  lat,lon=destination(37.923889,-122.596389,np.array([0,90,225]),np.array([1000,250_000,400_000]))
  az,d=bearing_distance(37.923889,-122.596389,lat,lon)
  np.testing.assert_allclose(d,[1000,250_000,400_000],rtol=1e-6)
  np.testing.assert_allclose(az,[0,90,225],atol=1e-6)
 def test_generated_coverage_is_limited_to_precisely_located_documented_radars(self):
  import json
  index=json.loads((ROOT/'public/data/coverage/index.json').read_text())
  radars={f['feature_id']:f for f in json.loads((ROOT/'public/data/radar.json').read_text())}
  self.assertIn('not FAA-published',index['label']);self.assertGreaterEqual(len(index['radars']),90)
  for fid,r in index['radars'].items():
   f=radars[fid]
   self.assertIn(f['location_accuracy'],['Published radar-site coordinates','Published antenna coordinates'])
   self.assertIn(r['model'],['ARSR-4','CARSR','ASR-8','ASR-9','ASR-11'])
   for ft in index['slices_ft_agl']:self.assertTrue((ROOT/'public/data/coverage'/r['images'][str(ft)]).exists())
   fractions=[r['covered_fraction'][str(ft)] for ft in index['slices_ft_agl']]
   self.assertEqual(fractions,sorted(fractions))  # Higher targets are never less visible.
  tam=index['radars']['JPL_RADAR:MILLVALLEY'];self.assertAlmostEqual(tam['ground_m'],784,delta=30);self.assertEqual(tam['range_km'],420)
  self.assertFalse(any(radars[fid]['location_accuracy']=='Airport reference only' for fid in index['radars']))
