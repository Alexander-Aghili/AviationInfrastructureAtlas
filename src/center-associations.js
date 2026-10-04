export function associatedSystems(records,center){
 if(!center)return [];
 const identifiers=new Set(center.identifiers);
 return records.filter(f=>f.feature_id!==center.feature_id&&f.relationships.some(r=>r.type==='published ARTCC association'&&identifiers.has(r.identifier)));
}
