"""Normalize the retained 2026-10-01 FAA release; no airport-coordinate substitutions."""
import csv,json,re,hashlib,collections,pathlib,math
ROOT=pathlib.Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw'; OUT=ROOT/'public/data'; CYCLE='2026-10-01'
SOURCE='https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/2026-10-01/'
def coords(row):
    try:
        lat=float(row['LAT_DECIMAL']);lon=float(row['LONG_DECIMAL'])
        return [lon,lat] if math.isfinite(lat) and math.isfinite(lon) and abs(lat)<=90 and abs(lon)<=180 else None
    except (KeyError,ValueError):return None
def seconds(value):
    if not value.strip():return None
    return float(value.strip()[:-1])/3600*(-1 if value.strip()[-1] in 'SW' else 1)
def dms(value):
    m=re.fullmatch(r'(\d+)-(\d+)-(\d+(?:\.\d+)?)([NSEW])',value.strip())
    if not m:return None
    d,mn,s,h=m.groups();return (float(d)+float(mn)/60+float(s)/3600)*(-1 if h in 'SW' else 1)
def rows(group,table):
    with (RAW/f'01_Oct_2026_{group}_CSV'/f'{table}.csv').open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def main():
    features=[];counts={};seen=set()
    manifest=json.loads((RAW/'manifest.json').read_text())
    for entry in manifest:
        if entry.get('error'):raise ValueError('Failed source download: '+entry['url'])
        path=ROOT/entry['file']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('Source checksum mismatch: '+str(path))
    nav_remarks=collections.defaultdict(list);ils_remarks=collections.defaultdict(list)
    for r in rows('NAV','NAV_RMK'):nav_remarks[tuple(r[k] for k in ['NAV_ID','NAV_TYPE','STATE_CODE','CITY'])].append(r['REMARK'])
    for r in rows('ILS','ILS_RMK'):ils_remarks[tuple(r[k] for k in ['SITE_NO','RWY_END_ID','SYSTEM_TYPE_CODE'])].append(r['TAB_NAME']+': '+r['REMARK'])
    def add(table,key,name,ident,kind,subtype,row,geometry=None,centers=None,role='equipment location',site=None):
        fid=table+':'+key
        if fid in seen:raise ValueError('Duplicate source key '+fid)
        seen.add(fid)
        point=coords(row) if geometry is None else geometry
        if row.get('LOC_FREQ'):row['LOC_FREQ_UNIT']='MHz'
        if table=='ILS_MKR' and row.get('FREQ'):row['FREQ_UNIT']='kHz'
        if table.startswith('ILS') and row.get('SITE_ELEVATION'):row['ELEVATION_REFERENCE']='feet MSL'
        attr={k:v for k,v in row.items() if v and not k.startswith(('LAT_','LONG_','TACAN_DME_LAT','TACAN_DME_LONG'))}
        features.append(dict(feature_id=fid,source_key=key,site_id=site or fid,equipment_id=fid,name=name.title(),identifiers=list(dict.fromkeys([ident]+[row[k] for k in ['ICAO_ID'] if row.get(k)])),aliases=[row.get('CITY',''),row.get('NAME','')],feature_type=kind,subtype=subtype,geometry={'type':'Point','coordinates':point} if point else None,coordinate_role=role,state=row.get('STATE_CODE',''),city=row.get('CITY','').title(),owner_or_operator=row.get('OPERATOR') or row.get('OWNER'),relationships=[{'type':'published ARTCC association','identifier':c} for c in sorted(set(centers or [])) if c],attributes=attr,source={'dataset':'FAA NASR','table':table,'record':key,'url':SOURCE,'cycle':CYCLE,'record_effective_date':row.get('EFF_DATE',CYCLE)},effective_date=CYCLE,quality={'mapped':bool(point),'original_coordinates':{k:v for k,v in row.items() if k.startswith(('LAT_','LONG_','TACAN_DME_LAT','TACAN_DME_LONG'))},'review_notes':[] if point else ['No equipment coordinates supplied; retained as an unlocated record.']}))
        counts[table]=counts.get(table,0)+1
    for r in rows('NAV','NAV_BASE'):
        if r['COUNTRY_CODE']!='US':continue
        r['REMARK']=' / '.join(nav_remarks[tuple(r[k] for k in ['NAV_ID','NAV_TYPE','STATE_CODE','CITY'])])
        add('NAV_BASE',r['NAV_ID']+'|'+r['NAV_TYPE']+'|'+r['STATE_CODE']+'|'+r['CITY'],r['NAME'],r['NAV_ID'],'navigation',r['NAV_TYPE'],r,centers=[r['HIGH_ALT_ARTCC_ID'],r['LOW_ALT_ARTCC_ID']])
    for group,table,idfield,namefield,kind,typefield in [('COM','COM','COMM_LOC_ID','COMM_OUTLET_NAME','communications','COMM_TYPE'),('AWOS','AWOS','ASOS_AWOS_ID','CITY','weather','ASOS_AWOS_TYPE'),('RDR','RDR','FACILITY_ID','FACILITY_ID','radar','RADAR_TYPE'),('ATC','ATC_BASE','FACILITY_ID','FACILITY_NAME','control','FACILITY_TYPE')]:
        for r in rows(group,table):
            if r.get('COUNTRY_CODE')!='US':continue
            if table=='ATC_BASE' and r['FACILITY_TYPE']=='NON-ATCT':continue
            key='|'.join(r.get(k,'') for k in [idfield,typefield,'STATE_CODE','CITY','COMM_OUTLET_NAME','NAV_ID','FACILITY_ID','RADAR_NO'] if k in r)
            add(table,key,r[namefield] or r[idfield],r[idfield],kind,r[typefield],r,centers=[r.get('APCH_P_PROVIDER','')] if r.get('APCH_P_PROV_TYPE_CD')=='C' else [],role='weather station location' if kind=='weather' else 'equipment location')
    for table,sub in [('ILS_BASE','Localizer'),('ILS_GS','Glide slope'),('ILS_DME','DME'),('ILS_MKR','Marker beacon')]:
        for r in rows('ILS',table):
            if r['COUNTRY_CODE']!='US':continue
            r['REMARK']=' / '.join(ils_remarks[tuple(r[k] for k in ['SITE_NO','RWY_END_ID','SYSTEM_TYPE_CODE'])])
            key='|'.join(r.get(k,'') for k in ['SITE_NO','RWY_END_ID','SYSTEM_TYPE_CODE','ILS_COMP_TYPE_CODE'])
            add(table,key,f"{r['CITY']} · RWY {r['RWY_END_ID']} {sub}",r['ILS_LOC_ID'],'landing',sub,r,site='ILS:'+r['SITE_NO']+'|'+r['RWY_END_ID'])
    aff={};supp=collections.defaultdict(lambda:dict(remarks=[],frequencies=[],airports=[]))
    for line in (RAW/'AFF/AFF.txt').read_text().splitlines():
        if line[:4]=='AFF1':
            center=line[4:8].strip();loc=line[48:78].strip();typ=line[128:133].strip();key=(center,loc,typ)
            aff[key]=line
        elif line[:4] in ['AFF2','AFF3']:
            key=(line[4:8].strip(),line[8:38].strip(),line[38:43].strip())
            if line[:4]=='AFF2':supp[key]['remarks'].append(line[47:247].strip())
            else:
                supp[key]['frequencies'].append(line[43:51].strip()+' MHz · '+line[51:61].strip())
                if line[78:82].strip():supp[key]['airports'].append(line[78:82].strip())
    # Cross-center sites merge only with exact published name, type, and identical coordinates.
    grouped={}
    for key,line in aff.items():
        center,loc,typ=key;lat=seconds(line[189:200]);lon=seconds(line[214:225]);physical=(loc,typ,lat,lon,line[173:175])
        g=grouped.setdefault(physical,{'centers':[],'keys':[],'lines':[],'remarks':[],'frequencies':[],'airports':[]})
        g['centers'].append(center);g['keys'].append('|'.join(key));g['lines'].append(line)
        for k in ['remarks','frequencies','airports']:g[k]+=supp[key][k]
    for (loc,typ,lat,lon,state),g in grouped.items():
        line=g['lines'][0];row={'STATE_CODE':state,'CITY':loc,'EFF_DATE':line[133:143].strip(),'ARTCC_NAME':line[8:48].strip(),'ICAO_ID':line[225:229].strip() if typ=='ARTCC' else '','REMARK':' / '.join(g['remarks']),'FREQUENCIES':' / '.join(sorted(set(g['frequencies']))),'ASSOCIATED_AIRPORTS':', '.join(sorted(set(g['airports']))),'LAT_SOURCE':line[175:200].strip(),'LONG_SOURCE':line[200:225].strip(),'SOURCE_RECORDS':'; '.join(g['keys'])}
        kind={'ARTCC':'centers','RCAG':'communications','ARSR':'radar','SECRA':'radar','CERAP':'control'}[typ]
        add('AFF1','|'.join([loc,typ,state,str(lat),str(lon)]),loc,g['centers'][0] if typ=='ARTCC' else loc,kind,typ,row,geometry=[lon,lat] if lat is not None and lon is not None else None,centers=g['centers'],role='physical facility location' if typ=='ARTCC' else 'equipment site location')
    # Published vertices only; omitted segments carry arcs or national-border instructions.
    boundary=[];groups=collections.defaultdict(list);omitted=0
    for r in rows('ARB','ARB_SEG'):
        if r['LOCATION_ID'].startswith('Z'):groups[(r['LOCATION_ID'],r['ALTITUDE'],r['TYPE'])].append(r)
    for (center,alt,typ),rr in groups.items():
        rr.sort(key=lambda r:int(r['POINT_SEQ']));parts=[];run=[];start=0
        for i,r in enumerate(rr):
            a=coords(r);desc=r['BNDRY_PT_DESCRIP'].upper();closing='POINT OF BEGINNING' in desc
            b=coords(rr[start] if closing else rr[(i+1)%len(rr)])
            unsupported=any(w in desc for w in ['ARC','BOUNDARY','BORDER','THENCE VIA']) or not a or not b or abs(a[0]-b[0])>180
            if unsupported:
                if len(run)>1:parts.append(run)
                run=[];omitted+=1
            else:
                if not run:run=[a]
                run.append(b)
            if closing:
                if len(run)>1:parts.append(run)
                run=[];start=i+1
        if len(run)>1:parts.append(run)
        if parts:boundary.append({'type':'Feature','geometry':{'type':'MultiLineString','coordinates':parts},'properties':{'center':center,'name':rr[0]['LOCATION_NAME'].title(),'altitude':alt,'boundary_type':typ,'effective_date':rr[0]['EFF_DATE'],'note':'Published straight segments only. Curves, national borders and antimeridian segments omitted pending geometry validation.'}})
    from supplemental import augment
    supplemental_manifest=json.loads((ROOT/'data/supplemental/manifest.json').read_text())
    for entry in supplemental_manifest:
        if hashlib.sha256((ROOT/entry['file']).read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('Supplemental checksum mismatch: '+entry['file'])
    supplemental_audit=augment(features,RAW,ROOT)
    counts=dict(collections.Counter(f['source']['table'] for f in features))
    counts_by_type=collections.Counter(f['feature_type'] for f in features)
    audit={'cycle':CYCLE,'source':SOURCE,'records':len(features),'mapped':sum(bool(f['geometry']) for f in features),'unlocated':sum(not f['geometry'] for f in features),'normalized_equipment_records':len(features),'unique_installations':None,'site_groups':len(set(f['site_id'] for f in features)),'by_table':counts,'by_type':dict(counts_by_type),'boundary_variants':len(boundary),'omitted_boundary_segments':omitted,'unassociated':sum(not f['relationships'] for f in features),'supplemental':supplemental_audit,'completeness':'Not a complete inventory. NASA/JPL supplies long-range radar site coordinates; FAA and NTSB supply selected terminal antenna positions. Many terminal radars and control facilities remain unlocated. Equipment inventories are dated, not live status. FAA-address Census geocodes are approximate. ARTCC boundaries show partial straight segments.','deduplication':'AFF sites reconciled only by exact site name, type, state and source coordinates; shared center associations retained. Other cross-table duplicates have not been reconciled.'}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'supplemental-manifest.json').write_text(json.dumps(supplemental_manifest,indent=2))
    catalog=[{k:v for k,v in f.items() if k not in ['attributes','quality']} for f in features]
    (OUT/'catalog.json').write_text(json.dumps(catalog,separators=(',',':')))
    for kind in counts_by_type:
        (OUT/(kind+'.json')).write_text(json.dumps([f for f in features if f['feature_type']==kind],separators=(',',':')))
    for name,obj in [('facilities.json',features),('boundaries.geojson',{'type':'FeatureCollection','features':boundary}),('audit.json',audit),('manifest.json',json.loads((RAW/'manifest.json').read_text()))]:
        (OUT/name).write_text(json.dumps(obj,separators=(',',':')))
    print(json.dumps(audit,indent=2))
if __name__=='__main__':main()
