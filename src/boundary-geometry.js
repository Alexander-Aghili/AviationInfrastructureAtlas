export function chooseBoundaries(features,{level='HIGH',oceanic='FIR',centerIds=null}={}){
 return features.filter(f=>{
 const p=f.properties;if(centerIds&&!centerIds.includes(p.center))return false;
 if(p.boundary_type==='ARTCC')return p.altitude===level;
 if(['ARTCC','CERAP'].includes(p.local_type))return true;
 return p.boundary_type===oceanic;
 });
}
// Cut outlines at the date line instead of drawing a diagonal across the world.
export function boundaryOutlines(feature){
 const g=feature.geometry,polygons=g.type==='Polygon'?[g.coordinates]:g.coordinates,parts=[];
 for(const polygon of polygons)for(const ring of polygon){let run=[ring[0]];
 for(let i=1;i<ring.length;i++){const a=ring[i-1],b=ring[i];if(Math.abs(b[0]-a[0])<=180){run.push(b);continue;}
 const unwrapped=b[0]+(b[0]>a[0]?-360:360),edge=unwrapped>a[0]?180:-180;
 const ratio=unwrapped===a[0]?1:(edge-a[0])/(unwrapped-a[0]),lat=a[1]+ratio*(b[1]-a[1]);run.push([edge,lat]);if(run.length>1)parts.push(run);run=[[-edge,lat],b];
 }if(run.length>1)parts.push(run);}
 return {...feature,geometry:{type:'MultiLineString',coordinates:parts}};
}
