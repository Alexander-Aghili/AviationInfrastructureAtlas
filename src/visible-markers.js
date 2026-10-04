export const MAX_VISIBLE_MARKERS=150;
// Distribute the budget across screen cells instead of favoring one dense city.
export function chooseVisibleMarkers(records,project,size,selectedId=null,limit=MAX_VISIBLE_MARKERS){
 const cells=new Map(),cols=Math.max(1,Math.round(Math.sqrt(limit*size.x/Math.max(1,size.y)))),rows=Math.max(1,Math.ceil(limit/cols));let count=0,selected;
 for(const f of records){if(!f.geometry)continue;const p=project(f.geometry.coordinates);if(p.x<0||p.y<0||p.x>size.x||p.y>size.y)continue;count++;const item={record:f,distance:(p.x-size.x/2)**2+(p.y-size.y/2)**2};if(f.feature_id===selectedId){selected=f;continue;}const key=Math.min(cols-1,Math.floor(p.x/size.x*cols))+cols*Math.min(rows-1,Math.floor(p.y/size.y*rows));if(!cells.has(key))cells.set(key,[]);cells.get(key).push(item);}
 const buckets=[...cells.entries()].sort((a,b)=>a[0]-b[0]).map(([,items])=>items.sort((a,b)=>a.distance-b.distance||a.record.feature_id.localeCompare(b.record.feature_id)));
 const visible=selected?[selected]:[];for(let round=0;visible.length<limit;round++){let added=false;for(const bucket of buckets){if(bucket[round]){visible.push(bucket[round].record);added=true;if(visible.length===limit)break;}}if(!added)break;}
 return {visible,count};
}
