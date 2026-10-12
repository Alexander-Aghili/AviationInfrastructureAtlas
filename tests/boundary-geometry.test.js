import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import {chooseBoundaries,boundaryOutlines} from '../src/boundary-geometry.js';
const data=JSON.parse(fs.readFileSync(new URL('../public/data/boundaries.geojson',import.meta.url)));
test('high/low are separate and New York Oceanic/San Juan retain FIRs',()=>{
 const high=chooseBoundaries(data.features),low=chooseBoundaries(data.features,{level:'LOW'});
 assert(high.some(f=>f.properties.center==='ZSE'));assert(high.some(f=>f.properties.center==='ZLC'));assert(high.some(f=>f.properties.center==='ZBW'));
 assert(high.some(f=>f.properties.center==='ZWY'&&f.properties.boundary_type==='FIR'));assert(high.some(f=>f.properties.center==='ZSU'&&f.properties.boundary_type==='FIR'));
 assert(high.filter(f=>f.properties.boundary_type==='ARTCC').every(f=>f.properties.altitude==='HIGH'));assert(low.filter(f=>f.properties.boundary_type==='ARTCC').every(f=>f.properties.altitude==='LOW'));
 assert(chooseBoundaries(data.features,{oceanic:'CTA',centerIds:['ZWY']}).every(f=>f.properties.center==='ZWY'&&f.properties.boundary_type==='CTA'));
});
test('all FAA outlines are finite and never jump across the date line',()=>{
 for(const f of data.features){const outline=boundaryOutlines(f);assert(outline.geometry.coordinates.length>0);for(const line of outline.geometry.coordinates){assert(line.every(p=>p.every(Number.isFinite)));for(let i=1;i<line.length;i++)assert(Math.abs(line[i][0]-line[i-1][0])<=180);}}
});
test('source date-line seam keeps its north-south boundary instead of producing NaN',()=>{
 const f={geometry:{type:'Polygon',coordinates:[[[180,10],[-180,20],[-170,20],[-170,10],[180,10]]]}};const result=boundaryOutlines(f);assert(result.geometry.coordinates.some(line=>line.some(p=>p[0]===180&&p[1]===20)));
});
