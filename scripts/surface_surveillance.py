"""Import every airport in the retained FAA nationwide surface-system deployment lists."""
import re,html
from supplemental import source
PAGES=[('ASDE-X','faa-asde-x.html','https://www.faa.gov/air_traffic/technology/asde-x','Status','2023-09-07',35),('ASSC','faa-assc.html','https://www.faa.gov/air_traffic/technology/adsb/atc/assc','Availability','2024-05-24',9)]
def deployments(raw):
    for model,file,url,heading,date,expected in PAGES:
        text=(raw/file).read_text()
        section=re.search(r'<h[23]>'+heading+r'</h[23]>.*?<ul>(.*?)</ul>',text,re.S).group(1)
        entries=[]
        for item in re.findall(r'<li>(.*?)</li>',section,re.S):
            clean=html.unescape(re.sub('<[^>]+>','',item)).strip()
            match=re.fullmatch(r'(.+?)\s*\(([A-Z0-9]{3})\)v?',clean)
            if not match:raise ValueError('Unrecognized FAA airport: '+clean)
            entries.append(match.groups())
        if len(entries)!=expected or len({i for n,i in entries})!=expected:raise ValueError('FAA deployment list changed')
        stamp=re.search(r'Last updated:\s*[^,]+,\s*([^<]+)',text)
        if not stamp:raise ValueError('FAA publication date not found')
        from datetime import datetime
        date=datetime.strptime(stamp.group(1).strip(),'%B %d, %Y').date().isoformat()
        yield model,url,date,entries

def augment_surface(features,raw):
    counts={}
    for model,url,date,entries in deployments(raw):
        counts[model]=len(entries)
        for name,ident in entries:
            tower=next((f for f in features if f['feature_type']=='towers' and ident in f['identifiers']),None)
            fid='FAA_SURFACE:'+model+':'+ident
            inputs='ASDE-3 surface movement radar; multilateration; ADS-B; airport surveillance radar / Mode S; STARS' if model=='ASSC' else 'Surface movement radar; multilateration; ADS-B; terminal surveillance radar / Mode S; flight-plan data'
            features.append(dict(feature_id=fid,source_key=ident,site_id=fid,equipment_id=fid,name=name+' · '+model+' surface surveillance',identifiers=[ident],aliases=['airport surface detection','surface movement radar','SMR'],feature_type='radar',subtype=model,facility_class='Airport surface surveillance system',equipment_model=model,model_date=date,location_date=None,location_accuracy='Not located',evidence_tier='government',geometry=None,coordinate_role='Airport deployment; individual sensor positions not published',state=tower['state'] if tower else '',city=tower['city'] if tower else name,owner_or_operator='Federal Aviation Administration',relationships=[{'type':'published surface-system airport association','identifier':ident}],attributes={'FAA_DEPLOYMENT_AIRPORT':name,'SYSTEM_ARCHITECTURE_INPUTS':inputs,'SENSOR_LOCATION_NOTE':'Architecture describes the system family; this page does not enumerate or locate each airport antenna.'},source={'dataset':'FAA surface surveillance deployment lists','table':'FAA_SURFACE','record':ident,'url':url,'cycle':None,'record_effective_date':date},sources=[source('FAA '+model+' · nationwide deployment list','Federal Aviation Administration',url,date,['system type','airport deployment','system architecture'],ident)],effective_date=date,status_note='FAA-documented multi-sensor airport system. Sensor coordinates and current individual antenna inventory are not supplied.',quality={'mapped':False,'original_coordinates':{},'review_notes':['No airport reference point or tower address substituted for radar sensor coordinates.']}))
    return counts
