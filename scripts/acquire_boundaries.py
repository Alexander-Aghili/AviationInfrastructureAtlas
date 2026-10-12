"""Retain FAA chart-boundary polygons separately from the NASR publication."""
import datetime,hashlib,json,pathlib,urllib.parse,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
SERVICE='https://services6.arcgis.com/ssFJjBXIUyZDrSYZ/ArcGIS/rest/services/Boundary_Airspace/FeatureServer'
ITEM='https://www.arcgis.com/sharing/rest/content/items/67885972e4e940b2aa6d74024901c561?f=pjson'
def main():
 query=SERVICE+'/0/query?'+urllib.parse.urlencode({'where':"COUNTRY = 'United States' AND TYPE_CODE IN ('ARTCC','CTA','FIR','OCA')",'outFields':'*','returnGeometry':'true','outSR':'4326','f':'geojson','resultRecordCount':2000})
 inputs=[('faa-boundary-service.json',SERVICE+'?f=pjson'),('faa-boundary-layer.json',SERVICE+'/0?f=pjson'),('faa-boundary-item.json',ITEM),('faa-airspace-boundaries.geojson',query)]
 downloaded=[]
 for name,url in inputs:
  content=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'AirwaysAtlas source acquisition'}),timeout=60).read();value=json.loads(content)
  if 'error' in value:raise ValueError(value['error'])
  downloaded.append((name,url,content,value))
 if downloaded[2][3].get('owner')!='AeronauticalInformationServices_FAA':raise ValueError('Unexpected source publisher')
 geo=downloaded[3][3]
 if geo.get('exceededTransferLimit') or len(geo.get('features',[]))<60:raise ValueError('Incomplete boundary query')
 manifest=[]
 for name,url,content,_ in downloaded:
  path=ROOT/'data/raw'/name;path.write_bytes(content);manifest.append(dict(file=str(path.relative_to(ROOT)),url=url,sha256=hashlib.sha256(content).hexdigest(),bytes=len(content),retrieved_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),dataset='FAA chart airspace boundaries'))
 (ROOT/'data/boundaries').mkdir(exist_ok=True)
 (ROOT/'data/boundaries/manifest.json').write_text(json.dumps(manifest,indent=2))
 print(f'Retained {len(geo["features"])} FAA boundary polygons and publisher metadata.')
if __name__=='__main__':main()
