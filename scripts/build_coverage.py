"""Model terrain line-of-sight coverage for radars with published site coordinates.

Only radars whose position is a published site/antenna coordinate and whose family has a
documented detection range are modeled. Output is labeled modeled coverage, never FAA coverage.
Terrain tiles are cached in data/terrain and checksummed in data/coverage/terrain-manifest.json.
"""
import concurrent.futures,datetime,hashlib,io,json,math,pathlib,re,time,urllib.request
import numpy as np
from PIL import Image
from coverage_model import FT,bearing_distance,destination,visibility
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'public/data/coverage';TERRAIN=ROOT/'data/terrain';MANIFEST=ROOT/'data/coverage/terrain-manifest.json'
TILE_URL='https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'
ATC425='https://www.ll.mit.edu/sites/default/files/publication/doc/2018-05/Cho_2015_ATC-425.pdf'
SLICES_FT=[1000,2500,5000,10000]
ANTENNA_AGL_M=20.0  # Tower heights are not published; one consistent assumption for every site.
AZIMUTH_STEP=0.5
PRECISE={'Published radar-site coordinates','Published antenna coordinates'}
def detection_range_km(f):
    """ATC-425 Table 2-1 maximum aircraft detection range for the documented radar family."""
    model=f.get('equipment_model') or f['subtype']
    legacy=f['attributes'].get('ORIGINAL_LEGACY_MODEL') or ''
    if model=='ARSR-4':return 420
    if model=='CARSR':return 430 if legacy.startswith('FPS') else 380 if legacy.startswith('ARSR') else None
    if model in ('ASR-8','ASR-9','ASR-11'):return 100
    return None
class Terrain:
    """Terrarium elevation tiles (meters), cached on disk with checksums."""
    def __init__(self):
        self.manifest={e['url']:e for e in json.loads(MANIFEST.read_text())} if MANIFEST.exists() else {}
        self.tiles={}
    def _fetch(self,key):
        z,x,y=key;path=TERRAIN/f'{z}/{x}/{y}.png';url=TILE_URL.format(z=z,x=x,y=y)
        if not path.exists():
            for attempt in range(4):
                try:
                    request=urllib.request.Request(url,headers={'User-Agent':'AirwaysAtlas/1.0 coverage-model'})
                    with urllib.request.urlopen(request,timeout=60) as response:content=response.read()
                    break
                except OSError:
                    if attempt==3:raise
                    time.sleep(2**attempt)
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
        content=path.read_bytes();digest=hashlib.sha256(content).hexdigest()
        known=self.manifest.get(url)
        if known and known['sha256']!=digest:raise ValueError('Terrain checksum mismatch: '+str(path))
        if not known:self.manifest[url]={'url':url,'file':str(path.relative_to(ROOT)),'sha256':digest,'bytes':len(content),'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
        rgb=np.asarray(Image.open(io.BytesIO(content)).convert('RGB')).astype(np.float32)
        return rgb[...,0]*256+rgb[...,1]+rgb[...,2]/256-32768
    def sample(self,lats,lons,z):
        """Nearest-pixel elevation; open water is the sea surface, not bathymetry."""
        n=256*2**z;lats=np.clip(lats,-85.05,85.05)
        px=((np.asarray(lons)+180)/360*n).astype(np.int64)%n
        py=((1-np.log(np.tan(np.radians(lats))+1/np.cos(np.radians(lats)))/math.pi)/2*n).astype(np.int64).clip(0,n-1)
        tx,ty=px//256,py//256;keys=sorted({(z,int(a),int(b)) for a,b in set(zip(tx.ravel().tolist(),ty.ravel().tolist()))})
        missing=[k for k in keys if k not in self.tiles]
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            for k,tile in zip(missing,pool.map(self._fetch,missing)):self.tiles[k]=tile
        out=np.empty(px.shape,np.float32)
        for k in keys:
            mask=(tx==k[1])&(ty==k[2]);out[mask]=self.tiles[k][py[mask]%256,px[mask]%256]
        return np.maximum(out,0)
    def save(self):
        MANIFEST.parent.mkdir(parents=True,exist_ok=True)
        MANIFEST.write_text(json.dumps(sorted(self.manifest.values(),key=lambda e:e['url']),indent=1))
def merc(lat):return np.log(np.tan(np.pi/4+np.radians(lat)/2))
def unmerc(y):return np.degrees(2*np.arctan(np.exp(y))-np.pi/2)
def raster_grid(bounds,pixel_m):
    """Pixel-center lat/lon for a Web Mercator image that Leaflet stretches over bounds."""
    (s,w),(n,e)=bounds;mid=math.radians((s+n)/2)
    width=max(2,round((e-w)*111320*math.cos(mid)/pixel_m));height=max(2,round((merc(n)-merc(s))/math.radians(e-w)*width))
    lons=w+(np.arange(width)+.5)/width*(e-w);lats=unmerc(merc(n)-(np.arange(height)+.5)/height*(merc(n)-merc(s)))
    return np.meshgrid(lats,lons,indexing='ij')
def bounds_for(lat,lon,range_m):
    la,lo=destination(lat,lon,np.array([0,90,180,270]),np.full(4,range_m))
    return [[float(la[2]),float(lo[3])],[float(la[0]),float(lo[1])]]
def covered(radar,lats,lons):
    """Boolean [slice, ...] over grid points from a radar's polar visibility."""
    az,d=bearing_distance(radar['lat'],radar['lon'],lats,lons)
    ai=np.rint(az/AZIMUTH_STEP).astype(int)%radar['visible'].shape[1]
    ri=np.rint(d/radar['step_m']).astype(int)-1
    inside=(ri>=0)&(d<=radar['range_m'])
    return np.stack([np.where(inside,v[ai,ri.clip(0,v.shape[1]-1)],False) for v in radar['visible']])
def png(path,mask_or_count,rgb,alphas):
    image=np.zeros(mask_or_count.shape+(4,),np.uint8);image[...,:3]=rgb
    level=np.minimum(mask_or_count.astype(int),len(alphas));image[...,3]=np.array([0]+alphas,np.uint8)[level]
    Image.fromarray(image,'RGBA').save(path,optimize=True)
def slug(fid):return re.sub(r'[^A-Za-z0-9]+','-',fid).strip('-').lower()
def main():
    radars=[f for f in json.loads((ROOT/'public/data/radar.json').read_text()) if f['geometry'] and f.get('location_accuracy') in PRECISE and detection_range_km(f)]
    terrain=Terrain();OUT.mkdir(parents=True,exist_ok=True)
    for old in OUT.glob('*.png'):old.unlink()
    modeled=[]
    for i,f in enumerate(radars,1):
        lon,lat=f['geometry']['coordinates'];range_m=detection_range_km(f)*1000
        terminal=range_m<=150_000;step=100.0 if terminal else 500.0;zoom=10 if terminal else 8
        ground=float(terrain.sample(np.array([lat]),np.array([lon]),12)[0]);antenna=ground+ANTENNA_AGL_M
        azimuths=np.arange(0,360,AZIMUTH_STEP);ranges=np.arange(step,range_m+step,step)
        la,lo=destination(lat,lon,azimuths[:,None],ranges[None,:])
        ground_profile=terrain.sample(la,lo,zoom)
        visible=visibility(ranges,ground_profile,antenna,[h*FT for h in SLICES_FT])
        radar={'lat':lat,'lon':lon,'range_m':range_m,'step_m':step,'visible':visible}
        bounds=bounds_for(lat,lon,range_m);glat,glon=raster_grid(bounds,250 if terminal else 1000)
        images={}
        for ft,mask in zip(SLICES_FT,covered(radar,glat,glon)):
            name=f'{slug(f["feature_id"])}-{ft}.png';png(OUT/name,mask,(222,120,40),[150]);images[ft]=name
        modeled.append({**radar,'feature':f,'ground':ground,'antenna':antenna,'bounds':bounds,'images':images,
                        'area':{ft:float(v.sum()) for ft,v in zip(SLICES_FT,visible)}})
        print(f'· {i}/{len(radars)} {f["name"]} ({f.get("equipment_model") or f["subtype"]}, {range_m/1000:.0f} km)',flush=True)
    terrain.save()
    # Mosaics: radars whose ranges overlap share one image; each pixel counts covering radars.
    groups=[]
    for r in modeled:
        joined=[g for g in groups if any(bearing_distance(r['lat'],r['lon'],np.array([o['lat']]),np.array([o['lon']]))[1][0]<r['range_m']+o['range_m'] for o in g)]
        merged=[r]+[o for g in joined for o in g];groups=[g for g in groups if g not in joined]+[merged]
    mosaics=[]
    for n,group in enumerate(sorted(groups,key=len,reverse=True)):
        boxes=[r['bounds'] for r in group];bounds=[[min(b[0][0] for b in boxes),min(b[0][1] for b in boxes)],[max(b[1][0] for b in boxes),max(b[1][1] for b in boxes)]]
        glat,glon=raster_grid(bounds,2000);count=np.zeros((len(SLICES_FT),)+glat.shape,np.uint8)
        for r in group:
            (s,w),(nn,e)=r['bounds'];rows=(glat[:,0]>=s)&(glat[:,0]<=nn);cols=(glon[0]>=w)&(glon[0]<=e)
            window=np.ix_(rows,cols);count[(slice(None),)+window]+=covered(r,glat[window],glon[window])
        files={}
        for ft,c in zip(SLICES_FT,count):
            name=f'mosaic-{n}-{ft}.png';png(OUT/name,c,(31,138,158),[95,145,185]);files[ft]=name
        mosaics.append({'bounds':bounds,'images':files,'radars':len(group)})
    index={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'slices_ft_agl':SLICES_FT,
        'label':'Modeled terrain line-of-sight · not FAA-published coverage',
        'method':'Terrain line-of-sight with a 4/3-Earth-radius refraction model, following the FAA-sponsored ATC-425 method. Ranges are the ATC-425 Table 2-1 maximum aircraft detection range for the documented radar family. A target is covered when it is in line of sight at the stated height above the terrain beneath it.',
        'assumptions':[f'Antenna {ANTENNA_AGL_M:.0f} m above the terrain at the published site; actual tower heights are not published.','Terrain only: no buildings, vegetation, beam pattern, ground clutter, cone of silence, sensitivity or operational status.',f'Terrain sampled every 0.5 km on {AZIMUTH_STEP}° radials (0.1 km for terminal radars).','Radars located only by airport reference points, or with no documented model, are not modeled.'],
        'sources':[{'title':'ATC-425 · Table 2-1 and §2 method','publisher':'MIT Lincoln Laboratory · FAA-sponsored research','url':ATC425+'#page=13','date':'2015-05-26','fields':['detection range','4/3-Earth refraction','terrain line-of-sight method'],'tier':'faa-sponsored research'},
                   {'title':'Terrain Tiles (Terrarium)','publisher':'Mapzen / Tilezen on AWS Open Data · USGS 3DEP, SRTM, GMTED2010, ETOPO1','url':'https://registry.opendata.aws/terrain-tiles/','date':None,'fields':['terrain elevation'],'tier':'open data'}],
        'radars':{r['feature']['feature_id']:{'name':r['feature']['name'],'model':r['feature'].get('equipment_model') or r['feature']['subtype'],'range_km':r['range_m']/1000,'ground_m':round(r['ground']),'antenna_m':round(r['antenna']),'bounds':r['bounds'],'images':r['images'],
            'covered_fraction':{ft:round(a/r['visible'][0].size,3) for ft,a in r['area'].items()}} for r in modeled},
        'mosaics':mosaics}
    (OUT/'index.json').write_text(json.dumps(index,separators=(',',':')))
    print(f'Modeled {len(modeled)} radars; {len(mosaics)} mosaics; {len(terrain.manifest)} terrain tiles retained.')
if __name__=='__main__':main()
