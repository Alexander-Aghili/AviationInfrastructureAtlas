"""Field-level evidence from government publications and FAA-sponsored research.
No image-swath exclusion geometries from the JPL KML are used as radar locations.
"""
import json,re,xml.etree.ElementTree as ET,collections,hashlib
JPL='https://uavsar.jpl.nasa.gov/kml/FAA_LongRangeRadars.kml'
ATC425='https://www.ll.mit.edu/sites/default/files/publication/doc/2018-05/Cho_2015_ATC-425.pdf'
ATC450='https://www.ll.mit.edu/sites/default/files/publication/doc/radar-coverage-analysis-terminal-precipitation-glass-program-cho-atc-450.pdf'
DIRECTORY='https://www.faa.gov/sites/faa.gov/files/service-center-list-12.19.23.pdf'
NFDD='https://aeronav.faa.gov/aero_data/NFDD/nfdd-2025-03-25-56.pdf'
RADOMES='https://www.radomes.org/museum/showsite.php?site=Mill+Valley+AFS%2C+CA'
DOT='https://www.transportation.gov/procurement-forecast-opportunity/procurement-forecast-opportunity-673706-1-facilities-security'

def source(title,publisher,url,date,fields,record=None,tier='government',note=None):
    return dict(title=title,publisher=publisher,url=url,date=date,fields=fields,record=record,tier=tier,note=note)

def canonical(name):
    name=name.split('(')[0].strip().upper().replace('MOUNT ','MT ').replace('FORT ','FT ').replace('SAINT ','ST ')
    return re.sub('[^A-Z0-9]','',name)

def radar_models(raw):
    text=(raw/'Cho_2015_ATC-425.txt').read_text();pages=text.split('\f');models={}
    # Appendices A-4/A-5 contain legacy site lists, NOT the proposed MPAR column.
    for model,table,next_table in [('CARSR','TABLE A-4','TABLE A-5'),('ARSR-4','TABLE A-5','TABLE A-6')]:
        start=text.rfind(table);end=text.find(next_table,start);section=text[start:end]
        for line in section.splitlines():
            m=re.match(r'^\s*([A-Z0-9]{2,5})\s+(.+?)\s{2,}([A-Z]{2})\s+(.*)$',line)
            if not m:continue
            ident,name,state,rest=m.groups()
            if 'MPAR' not in rest and 'None' not in rest:continue
            page=next((i+1 for i,p in enumerate(pages) if line in p),None)
            original=re.search(r'(?:ARSR-[123]|FPS-\d+[A-Z]?)',rest)
            models[canonical(name)]={'identifier':ident,'name':name,'state':state,'model':model,'original_model':original.group(0) if original else None,'page':page,'table':table.replace('TABLE ','Table ')}
    aliases={'SAN CLEMENTE':'SAN CLEMENTE','GUANTANAMO BAY':'GUANTANAMO','REMSEN':'UTICA','SAINT LOUIS':'ST LOUIS','FORT GREEN':'FT GREEN','MOUNT KAALA':'MT KAALA','MOUNT LAGUNA':'MT LAGUNA','MOUNT SANTA ROSA':'MT SANTA ROSA'}
    for alias,name in aliases.items():
        if canonical(name) in models:models[canonical(alias)]=models[canonical(name)]
    # Model inventory from the FAA-sponsored 4 March 2022 ATC-450 Table A-2.
    newer=(raw/'Cho_2021_ATC-450.txt').read_text();s=newer.rfind('Table A-2');end=newer.find('Table A-3',s);terminal={}
    for line in newer[s:end].splitlines():
        m=re.match(r'^\s*([A-Z0-9]{2,5})\s+(.+?)\s{2,}(ASR-(?:8|9|11)(?:\s+WSP)?)\s+(FAA|AF|Army|MC|Navy)\s*$',line)
        if m:
            ident,name,model,agency=m.groups();page=next((i+1 for i,p in enumerate(newer.split('\f')) if line in p),None)
            terminal[ident]={'name':name,'model':model.replace('  ',' '),'agency':agency,'page':page}
    if len(models)<100 or len(terminal)<180:raise ValueError(f'Unexpected report schema: {len(models)} long-range, {len(terminal)} terminal models')
    return models,terminal

def augment(features,raw,root):
    models,terminal=radar_models(raw)
    for f in features:
        f['sources']=[source('FAA NASR · '+f['source']['table'],'Federal Aviation Administration',f['source']['url'],f['source']['record_effective_date'],['identity','facility type','published attributes']+(['location'] if f['geometry'] else []),f['source_key'])]
        f['facility_class']=f['subtype'];f['equipment_model']=None;f['model_date']=None;f['location_date']=f['effective_date'] if f['geometry'] else None;f['location_accuracy']='Published coordinates' if f['geometry'] else 'Not located';f['evidence_tier']='government';f['status_note']='Publication record; live status not provided.'
        if f['feature_type']=='radar' and f['subtype']=='ASR':
            ident=f['identifiers'][0];m=terminal.get(ident)
            if m:
                f['name']=m['name'].title()+' radar';f['equipment_model']=m['model'];f['subtype']=m['model'];f['model_date']='2022-03-04'
                f['sources'].append(source('ATC-450 · Table A-2, p. '+str(m['page']),'MIT Lincoln Laboratory · FAA-sponsored research',ATC450+'#page='+str(m['page']),'2022-03-04',['equipment model'],ident,tier='faa-sponsored research',note='Last documented model; this report does not certify the current installation.'))
                f['attributes']['DOCUMENTED_MODEL']=m['model'];f['attributes']['MODEL_SOURCE_DATE']='2022-03-04'
    # Government-hosted long-range radar inventory. Coordinates come ONLY from descriptions.
    ns={'k':'http://www.opengis.net/kml/2.2'}
    for p in ET.parse(raw/'FAA_LongRangeRadars.kml').findall('.//k:Placemark',ns):
        desc=p.find('k:description',ns).text;name=desc.strip().split('<br>')[0].strip();lat=re.search(r'Latitude:\s*([-\d.]+)',desc);lon=re.search(r'Longitude:\s*([-\d.]+)',desc)
        if not lat or not lon:raise ValueError('JPL coordinate description changed: '+name)
        point=[float(lon.group(1)),float(lat.group(1))];meta=models.get(canonical(name));model=meta['model'] if meta else None
        if meta and meta['state']=='CU':continue  # outside the US/territory scope
        ident=meta['identifier'] if meta else 'JPL-'+canonical(name);state=meta['state'] if meta else ''
        fid='JPL_RADAR:'+canonical(name);sources=[source('FAA long-range radar site inventory','NASA / Jet Propulsion Laboratory',JPL,None,['site name','location'],name,note='Inventory has no publication date. Coordinates are read from the site description, not the decorative exclusion-zone polygon.')]
        if meta:sources.append(source('ATC-425 · '+meta['table']+', p. '+str(meta['page']),'MIT Lincoln Laboratory · FAA-sponsored research',ATC425+'#page='+str(meta['page']),'2015-05-26',['equipment family','identifier','state'],ident,tier='faa-sponsored research',note='2015 inventory; current equipment status is not established.' if model=='ARSR-4' else '2015 CARSR-program inventory. Original legacy model is preserved; present conversion status is not established.'))
        aliases=[];display=name.title()+' radar';attributes={'SITE_NAME':name,'DOCUMENTED_EQUIPMENT':model or 'ARSR family · model not supplied','MODEL_SOURCE_DATE':'2015-05-26' if meta else 'Unknown','CURRENT_EQUIPMENT_STATUS':'Not verified'}
        if meta and meta['original_model']:attributes['ORIGINAL_LEGACY_MODEL']=meta['original_model']
        if name=='MILL VALLEY':
            display='Mount Tamalpais radar';aliases=['Mt Tam','Mt. Tam','Mount Tam','Mt TAM Radar facility','Mill Valley','West Peak','Mill Valley AFS','J-33','P-38','Z-38']
            sources += [source('QMV ARSR refurbishment · FY2025 procurement forecast','US Department of Transportation / FAA',DOT,'2024-09-03',['facility identity','FAA radar site'], 'QMV'),source('Mill Valley AFS site history','National Air Defense Radar Museum · Radomes.org',RADOMES,None,['historical aliases','ARSR-4 corroboration'],'J-33',tier='community',note='Corroborating history; the mapped coordinates are from NASA/JPL and the model is documented in FAA-sponsored research.')]
            attributes['SITE_ALIASES']='Mt Tam / Mill Valley AFS / J-33';attributes['OPERATOR']='Federal Aviation Administration';attributes['GOVERNMENT_CORROBORATION_DATE']='2024-09-03'
        features.append(dict(feature_id=fid,source_key=name,site_id=fid,equipment_id=fid,name=display,identifiers=[ident],aliases=aliases,feature_type='radar',subtype=model or 'ARSR (model unspecified)',facility_class='Long-range surveillance radar',equipment_model=model,model_date='2015-05-26' if meta else None,location_date=None,location_accuracy='Published radar-site coordinates',evidence_tier='government',geometry={'type':'Point','coordinates':point},coordinate_role='published radar site location',state=state,city=name.title(),owner_or_operator='Federal Aviation Administration' if name=='MILL VALLEY' else None,relationships=[],attributes=attributes,source={'dataset':'NASA/JPL FAA radar inventory','table':'JPL_RADAR','record':name,'url':JPL,'cycle':None,'record_effective_date':None},sources=sources,effective_date=None,status_note='Documented site; present equipment and operational status are not verified.',quality={'mapped':True,'original_coordinates':{'LATITUDE':lat.group(1),'LONGITUDE':lon.group(1)},'review_notes':['Undated government site inventory. Model documentation is separately dated. No coverage or exclusion geometry is rendered.']}))
    # Two antenna positions explicitly referenced in an official FAA procedure publication.
    terminal_locations={'OAK':('37-42-22.10N','122-13-31.19W'),'NUQ':('37-25-28.28N','122-00-53.36W')}
    def dms(v):
        d,m,s,h=re.fullmatch(r'(\d+)-(\d+)-(\d+\.\d+)([NSWE])',v).groups();return (float(d)+float(m)/60+float(s)/3600)*(-1 if h in 'SW' else 1)
    for ident,(lat,lon) in terminal_locations.items():
        f=next((f for f in features if f['source']['table']=='RDR' and f['identifiers'][0]==ident and f['facility_class']=='ASR'),None)
        if not f:continue
        f['geometry']={'type':'Point','coordinates':[dms(lon),dms(lat)]};f['coordinate_role']='FAA-published radar antenna location';f['location_date']='2025-03-25';f['location_accuracy']='Published antenna coordinates';f['quality']['mapped']=True;f['quality']['original_coordinates']={'LATITUDE':lat,'LONGITUDE':lon};f['quality']['review_notes']=['Coordinates referenced in a removed procedure remark; retained as dated location evidence, not a present-status certification.']
        f['sources'].append(source('NFDD No. 056 · San Jose DVA change','Federal Aviation Administration',NFDD,'2025-03-25',['radar antenna location','ASR-9 model'],ident,note='The publication quotes the previous radar predicate coordinates in the removal note.'))
        f['equipment_model']='ASR-9';f['subtype']='ASR-9';f['model_date']='2025-03-25'
    rno=next(f for f in features if f['source']['table']=='RDR' and f['identifiers'][0]=='RNO' and f['facility_class']=='ASR')
    rno['geometry']={'type':'Point','coordinates':[-(119+46/60+46.45/3600),39+30/60+4.55/3600]};rno['location_date']='2017-11-02';rno['location_accuracy']='Published antenna coordinates';rno['coordinate_role']='NTSB-published radar sensor location';rno['quality']['mapped']=True;rno['quality']['original_coordinates']={'LATITUDE':'39°30′4.55″N','LONGITUDE':'119°46′46.45″W'};rno['quality']['review_notes']=['2017 NTSB antenna position; present installation position is not independently certified.']
    rno['sources'].append(source('ATC factual report · WPR16FA172','National Transportation Safety Board','https://data.ntsb.gov/Docket/Document/docBLOB?FileExtension=.PDF&FileName=Air+Traffic+Control+Group+Chairman%27s+Factual+Report-Master.PDF&ID=40464366','2017-11-02',['radar antenna location','ASR-11 corroboration'],'RNO'))
    # Retain published addresses as evidence. A TRACON building is the facility itself, so its
    # address estimate is mapped with a label; tower addresses never stand in for tower cabs.
    locations=json.loads((root/'data/supplemental/control_locations.json').read_text())+json.loads((root/'data/supplemental/tower_locations.json').read_text())
    for item in locations:
        f=next((f for f in features if f['source']['table']=='ATC_BASE' and f['identifiers'][0]==item['identifier']),None)
        if not f:continue
        f['attributes']['FACILITY_ADDRESS']=item['address']
        f['sources'].append(source('FAA service-center directory','Federal Aviation Administration',DIRECTORY,'2023-12-19',['facility address'],item['identifier']))
        if f['subtype']=='TRACON' and item.get('coordinates') and not f['geometry']:
            f['geometry']={'type':'Point','coordinates':item['coordinates']};f['equipment_geometry']=None
            f['coordinate_role']='Census street-range estimate of the FAA-published facility address';f['location_accuracy']='Address estimate';f['location_date']='2023-12-19';f['quality']['mapped']=True
            f['quality']['review_notes']=['Census street-range interpolation of the FAA directory address; not a surveyed building position.']
            f['sources'].append(source('US Census Geocoder · address match','US Census Bureau',item['url'],item['retrieved_at'][:10],['estimated map position'],item['identifier']))
    # FAA Letters to Airmen / PIV-list addresses for other TRACONs, positioned by Census or EPA FRS.
    for item in json.loads((root/'data/supplemental/tracon_locations.json').read_text()):
        f=next((f for f in features if f['source']['table']=='ATC_BASE' and f['subtype']=='TRACON' and f['identifiers'][0]==item['identifier']),None)
        if not f:continue
        f['attributes'].setdefault('FACILITY_ADDRESS',item['address'])
        if item['review_note']:f['quality']['review_notes'].append(item['review_note'])
        offices={'FAA (Federal NOTAM System, Letters to Airmen)':'Federal Aviation Administration · Letter to Airmen','FAA / ASH':'Federal Aviation Administration · Security & Hazardous Materials Safety'}
        for s in item['sources']:
            if s['publisher'] in offices:f['sources'].append(source(s['title'],offices[s['publisher']],s['url'],s['date'],['facility address'],item['identifier'],note='Published address: '+s['quote'] if s.get('quote') else None))
        evidence=item['position_evidence']
        if evidence and not f['geometry']:
            f['geometry']={'type':'Point','coordinates':item['coordinates']};f['equipment_geometry']=None
            f['coordinate_role']=evidence['role'];f['location_accuracy']='Address estimate';f['location_date']=evidence['date'];f['quality']['mapped']=True
            f['quality']['review_notes'].append('Approximate facility position from an official address; not a surveyed building position.')
            f['sources'].append(source(evidence['title'],evidence['publisher'],evidence['url'],evidence['date'],['estimated map position'],item['identifier']))
        if item['identifier']=='NCT':f['aliases']+=['NorCal','Norcal Approach','Norcal Departure','Northern California TRACON Facility','Mather']
    # Explicit sensor associations from ATC-450 Table A-1. No proximity-based inference.
    nct_ids=['BAB','OAK','MCE','MRY','RNO','SCK','SUU']
    for f in features:
        if f['feature_type']=='radar' and f['source']['table']=='RDR' and f['identifiers'][0] in nct_ids and f['facility_class']=='ASR':
            f['relationships'].append({'type':'published TRACON sensor association','identifier':'NCT','source_date':'2022-03-04'})
            f['sources'].append(source('ATC-450 · Table A-1, NCT row','MIT Lincoln Laboratory · FAA-sponsored research',ATC450+'#page=55','2022-03-04',['TRACON association'],f['identifiers'][0],tier='faa-sponsored research'))
    nct=next(f for f in features if f['source']['table']=='ATC_BASE' and 'NCT' in f['identifiers'])
    nct['attributes']['FACILITY_FUNCTION']='Terminal Radar Approach Control (TRACON)';nct['attributes']['DOCUMENTED_SENSOR_IDS']=', '.join(nct_ids)
    return {'long_range_sites':sum(f['source']['table']=='JPL_RADAR' for f in features),'terminal_model_records':sum(f['source']['table']=='RDR' and f['equipment_model'] is not None for f in features),'control_address_estimates':sum(f['location_accuracy']=='Address estimate' for f in features),'equipment_inventory_dates':['2015-05-26','2022-03-04'],'note':'NASR cycle and supplemental evidence dates are distinct. Radar models are last documented types, not a claim of current equipment. NASA/JPL radar inventory is undated. TRACON buildings with an FAA-published address are mapped at labeled Census address estimates; tower address geocodes are retained as research only and are not rendered.'}
