import unittest,datetime,json,sys,pathlib,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from release import cycle_on,next_cycle,is_cycle,prefix,csv_url,retained_cycle,cycle_from_url
class ReleaseCycleTests(unittest.TestCase):
 def test_cycle_arithmetic(self):
  self.assertEqual(cycle_on(datetime.date(2026,10,1)),'2026-10-01')
  self.assertEqual(cycle_on(datetime.date(2026,10,28)),'2026-10-01')
  self.assertEqual(cycle_on(datetime.date(2026,10,29)),'2026-10-29')
  self.assertEqual(cycle_on(datetime.date(2026,9,30)),'2026-09-03')
  self.assertEqual(next_cycle('2026-10-01'),'2026-10-29')
  self.assertTrue(is_cycle('2026-11-26'));self.assertFalse(is_cycle('2026-11-27'))
 def test_faa_file_names(self):
  self.assertEqual(prefix('2026-10-01'),'01_Oct_2026');self.assertEqual(prefix('2026-12-24'),'24_Dec_2026')
  self.assertEqual(csv_url('2026-10-29','RDR'),'https://nfdc.faa.gov/webContent/28DaySub/extra/29_Oct_2026_RDR_CSV.zip')
  self.assertEqual(cycle_from_url('https://nfdc.faa.gov/webContent/28DaySub/2026-10-29/AFF.zip'),'2026-10-29')
  self.assertEqual(cycle_from_url('https://nfdc.faa.gov/webContent/28DaySub/extra/01_Oct_2026_NAV_CSV.zip'),'2026-10-01')
 def test_retained_cycle_requires_one_release(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=pathlib.Path(tmp)/'manifest.json'
   path.write_text(json.dumps([{'url':csv_url('2026-10-01','NAV')},{'url':'https://nfdc.faa.gov/webContent/28DaySub/2026-10-01/AFF.zip'},{'url':'https://nfdc.faa.gov/webContent/28DaySub/TXT_to_CSV_Mapping.pdf'}]))
   self.assertEqual(retained_cycle(tmp),'2026-10-01')
   path.write_text(json.dumps([{'url':csv_url('2026-10-01','NAV')},{'url':csv_url('2026-10-29','RDR')}]))
   with self.assertRaises(ValueError):retained_cycle(tmp)
 def test_current_raw_release(self):
  self.assertEqual(retained_cycle(ROOT/'data/raw'),json.loads((ROOT/'public/data/audit.json').read_text())['cycle'])
from release_diff import diff,markdown,summary
def record(fid,kind='navigation',**extra):
 return {'feature_id':fid,'source_key':fid,'source':{'table':'NAV_BASE'},'feature_type':kind,'name':'Woodside','subtype':'VORTAC','identifiers':[fid],'state':'CA','geometry':{'type':'Point','coordinates':[-122.3,37.4]},'location_accuracy':'Published coordinates','relationships':[],'attributes':{'EFF_DATE':'2026/10/01','FREQ':'113.9'},**extra}
class ReleaseDiffTests(unittest.TestCase):
 def test_added_removed_changed_and_cycle_noise(self):
  old=[record('OSI'),record('SFO'),record('PYE')]
  moved=record('SFO',geometry={'type':'Point','coordinates':[-122.4,37.6]},attributes={'EFF_DATE':'2026/10/29','FREQ':'115.8'})
  new=[record('OSI',attributes={'EFF_DATE':'2026/10/29','FREQ':'113.9'}),moved,record('ZZV',kind='radar')]
  report=diff(old,new)
  self.assertEqual([f['feature_id'] for f in report['radar']['added']],['ZZV'])
  self.assertEqual([f['feature_id'] for f in report['navigation']['removed']],['PYE'])
  changed=report['navigation']['changed']
  self.assertEqual([f['feature_id'] for f,_ in changed],['SFO'])
  self.assertEqual({k for k,_,_ in changed[0][1]},{'position','attribute FREQ'})
  self.assertEqual(summary(report),'navigation +0 −1 ~1, radar +1 −0 ~0')
  audit={'records':3,'mapped':3,'unlocated':0}
  text=markdown(report,'2026-10-01','2026-10-29',audit,audit)
  self.assertIn('# NASR release 2026-10-29',text);self.assertIn('| navigation | 0 | 1 | 1 |',text)
  self.assertIn('  - attribute FREQ: 113.9 → 115.8',text);self.assertIn('position: 37.400000, -122.300000 → 37.600000, -122.400000',text)
 def test_identical_builds(self):
  self.assertEqual(diff([record('OSI')],[record('OSI')]),{})
  self.assertIn('No facility records changed.',markdown({},'a','b',{'records':1,'mapped':1,'unlocated':0},{'records':1,'mapped':1,'unlocated':0}))
 def test_rekeyed_records_pair_only_when_unambiguous(self):
  old=[record('ILS:1|06|LS',identifiers=['IABC']),record('A',identifiers=['DUP']),record('B',identifiers=['DUP'])]
  new=[record('ILS:1|07|LS',identifiers=['IABC'],name='Renumbered'),record('C',identifiers=['DUP'])]
  report=diff(old,new)['navigation']
  (f,fields),=report['changed']
  self.assertEqual(f['feature_id'],'ILS:1|07|LS')
  self.assertIn(('source key','ILS:1|06|LS','ILS:1|07|LS'),fields);self.assertIn(('name','Woodside','Renumbered'),fields)
  self.assertEqual([x['feature_id'] for x in report['added']],['C']);self.assertEqual(sorted(x['feature_id'] for x in report['removed']),['A','B'])
