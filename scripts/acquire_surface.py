"""Refresh FAA nationwide surface-system pages; validate lists before replacing sources."""
import datetime,hashlib,json,pathlib,tempfile,urllib.request
from surface_surveillance import PAGES,deployments
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
    with tempfile.TemporaryDirectory(dir=ROOT/'data') as temporary:
        stage=pathlib.Path(temporary);manifest=[]
        for model,file,url,heading,date,expected in PAGES:
            request=urllib.request.Request(url,headers={'User-Agent':'AirwaysAtlas/1.0'})
            with urllib.request.urlopen(request,timeout=60) as response:content=response.read()
            (stage/file).write_bytes(content)
            manifest.append(dict(file='data/raw/'+file,url=url,sha256=hashlib.sha256(content).hexdigest(),bytes=len(content),retrieved_at=datetime.datetime.now(datetime.timezone.utc).isoformat()))
        list(deployments(stage))
        for entry in manifest:(ROOT/entry['file']).write_bytes((stage/pathlib.Path(entry['file']).name).read_bytes())
        (ROOT/'data/supplemental/surface-manifest.json').write_text(json.dumps(manifest,indent=2))
if __name__=='__main__':main()
