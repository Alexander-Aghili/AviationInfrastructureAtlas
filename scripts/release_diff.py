"""Compare two normalized facility builds and render a reviewable Markdown change report."""
import collections
# Fields that change with every release without the facility itself changing.
CYCLE_FIELDS={'EFF_DATE'}
def _view(f):
    point=(f.get('geometry') or {}).get('coordinates')
    return {'name':f['name'],'type':f['subtype'],'equipment model':f.get('equipment_model'),'identifiers':', '.join(f['identifiers']),'state':f['state'],
            'position':', '.join(f'{v:.6f}' for v in reversed(point)) if point else None,'position precision':f.get('location_accuracy'),
            'associations':', '.join(sorted({r['identifier'] for r in f['relationships']})),'owner / operator':f.get('owner_or_operator'),
            **{'attribute '+k:v for k,v in f.get('attributes',{}).items() if k not in CYCLE_FIELDS}}
def _identity(f):return (f['feature_type'],f['source']['table'],f['identifiers'][0],f['subtype'])
def _changes(a,b):
    a,b=_view(a),_view(b);return [(k,a.get(k),b.get(k)) for k in sorted(a.keys()|b.keys()) if a.get(k)!=b.get(k)]
def diff(old,new):
    """Per-layer added, removed and changed records keyed by feature_id.

    Source keys embed fields FAA can edit (ILS system type, runway number), so a lone removed
    record and a lone added record with the same table, identifier and type are reported as one
    re-keyed change. Ambiguous matches stay as separate additions and removals."""
    before={f['feature_id']:f for f in old};after={f['feature_id']:f for f in new}
    added=[after[k] for k in sorted(after.keys()-before.keys())];removed=[before[k] for k in sorted(before.keys()-after.keys())]
    gone=collections.defaultdict(list);came=collections.defaultdict(list)
    for f in removed:gone[_identity(f)].append(f)
    for f in added:came[_identity(f)].append(f)
    pairs=[(gone[k][0],came[k][0]) for k in gone.keys()&came.keys() if len(gone[k])==len(came[k])==1]
    paired={f['feature_id'] for pair in pairs for f in pair}
    layers=collections.defaultdict(lambda:{'added':[],'removed':[],'changed':[]})
    for f in added:
        if f['feature_id'] not in paired:layers[f['feature_type']]['added'].append(f)
    for f in removed:
        if f['feature_id'] not in paired:layers[f['feature_type']]['removed'].append(f)
    changes=[(before[k],after[k],_changes(before[k],after[k])) for k in before.keys()&after.keys()]
    changes+=[(a,b,[('source key',a['feature_id'],b['feature_id'])]+_changes(a,b)) for a,b in pairs]
    for a,b,fields in sorted(changes,key=lambda c:c[1]['feature_id']):
        if fields:layers[b['feature_type']]['changed'].append((b,fields))
    return dict(layers)
def _label(f):return f"`{f['identifiers'][0]}` {f['name']} ({f['subtype']})"
def markdown(report,old_cycle,new_cycle,old_audit,new_audit):
    lines=[f'# NASR release {new_cycle}','',f'Compared with the retained {old_cycle} build. Review before committing; counts are source records, not verified installations.','',
           f"Records: {old_audit['records']:,} → {new_audit['records']:,} · mapped {old_audit['mapped']:,} → {new_audit['mapped']:,} · unlocated {old_audit['unlocated']:,} → {new_audit['unlocated']:,}",'']
    if old_audit.get('boundary_source')!=new_audit.get('boundary_source'):
        o,n=old_audit['boundary_source'],new_audit['boundary_source']
        lines+=[f"Boundaries: {o['effective_date']}–{o['valid_until']} ({o['source_polygon_records']} polygons) → {n['effective_date']}–{n['valid_until']} ({n['source_polygon_records']} polygons)",'']
    if not report:return '\n'.join(lines+['No facility records changed.',''])
    lines+=['| Layer | Added | Removed | Changed |','|---|---:|---:|---:|']
    lines+=[f"| {k} | {len(v['added'])} | {len(v['removed'])} | {len(v['changed'])} |" for k,v in sorted(report.items())]
    for kind,v in sorted(report.items()):
        lines+=['',f'## {kind}']
        if v['added']:lines+=['','### Added','']+[f'- {_label(f)}' for f in v['added']]
        if v['removed']:lines+=['','### Removed','']+[f'- {_label(f)}' for f in v['removed']]
        if v['changed']:
            lines+=['','### Changed','']
            for f,fields in v['changed']:lines+=[f'- {_label(f)}']+[f'  - {k}: {a if a not in (None,"") else "—"} → {b if b not in (None,"") else "—"}' for k,a,b in fields]
    return '\n'.join(lines)+'\n'
def summary(report):
    return ', '.join(f"{k} +{len(v['added'])} −{len(v['removed'])} ~{len(v['changed'])}" for k,v in sorted(report.items())) or 'no facility changes'
