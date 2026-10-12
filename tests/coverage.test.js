import test from 'node:test';import assert from 'node:assert/strict';import {overlaysFor,coverageDetail,coverageReason} from '../src/coverage.js';import {escapeHtml} from '../src/catalog.js';
const index={label:'Modeled terrain line-of-sight · not FAA-published coverage',method:'4/3 Earth.',assumptions:['Antenna 20 m.'],slices_ft_agl:[1000,5000],sources:[{title:'ATC-425',publisher:'MIT LL',url:'https://x',date:'2015-05-26',fields:['range'],tier:'faa-sponsored research'}],
 mosaics:[{bounds:[[1,2],[3,4]],images:{1000:'mosaic-0-1000.png',5000:'mosaic-0-5000.png'}}],
 radars:{'JPL_RADAR:MILLVALLEY':{model:'ARSR-4',range_km:420,ground_m:785,antenna_m:805,bounds:[[5,6],[7,8]],images:{1000:'tam-1000.png',5000:'tam-5000.png'},covered_fraction:{1000:.354,5000:.579}}}};
test('coverage overlays: mosaics for an altitude, or only the selected modeled radar',()=>{
 assert.deepEqual(overlaysFor(index,'',null),[]);assert.deepEqual(overlaysFor(null,'1000',null),[]);
 assert.deepEqual(overlaysFor(index,'1000','OTHER').map(o=>o.url),['data/coverage/mosaic-0-1000.png']);
 assert.deepEqual(overlaysFor(index,'5000','JPL_RADAR:MILLVALLEY').map(o=>[o.kind,o.url]),[['radar','data/coverage/tam-5000.png']]);
});
test('inspector labels the model and explains unmodeled radars',()=>{
 const html=coverageDetail(index,{feature_type:'radar',feature_id:'JPL_RADAR:MILLVALLEY'},'5000',escapeHtml);
 assert.match(html,/not FAA-published coverage/);assert.match(html,/58% of the 420 km range disc/);assert.match(html,/data-coverage="5000" aria-pressed="true"/);
 assert.equal(coverageDetail(index,{feature_type:'towers'},'',escapeHtml),'');
 assert.match(coverageReason({geometry:{},location_accuracy:'Airport reference only'}),/airport reference point/);
 assert.match(coverageDetail(index,{feature_type:'radar',feature_id:'X',geometry:null},'',escapeHtml),/Not modeled: the radar has no published location/);
});
