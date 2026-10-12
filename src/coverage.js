// Modeled terrain line-of-sight coverage: overlay selection and inspector text.
const PRECISE=['Published radar-site coordinates','Published antenna coordinates'];
export const coverageLabel=ft=>Number(ft).toLocaleString('en-US')+' ft AGL';
// A selected modeled radar shows only its own coverage; otherwise the national mosaics.
export function overlaysFor(index,ft,selectedId){
 if(!index||!ft)return [];
 const radar=index.radars[selectedId];
 if(radar)return [{kind:'radar',url:'data/coverage/'+radar.images[ft],bounds:radar.bounds}];
 return index.mosaics.map(m=>({kind:'mosaic',url:'data/coverage/'+m.images[ft],bounds:m.bounds}));
}
export function coverageReason(f){
 if(!f.geometry)return 'the radar has no published location';
 if(!PRECISE.includes(f.location_accuracy))return 'its map position is an airport reference point, not a published antenna or site coordinate';
 return 'its radar family has no documented detection range in the cited inventory';
}
export function coverageDetail(index,f,ft,e){
 if(f.feature_type!=='radar'||!index)return '';
 const r=index.radars[f.feature_id];
 if(!r)return `<h3>Modeled coverage</h3><p class="detail-note">Not modeled: ${e(coverageReason(f))}.</p>`;
 const buttons=index.slices_ft_agl.map(s=>`<button data-coverage="${s}" aria-pressed="${String(s)===String(ft)}">${e(coverageLabel(s))}</button>`).join('');
 const rows=index.slices_ft_agl.map(s=>`<dt>${e(coverageLabel(s))}</dt><dd>${Math.round(r.covered_fraction[s]*100)}% of the ${e(r.range_km)} km range disc in line of sight</dd>`).join('');
 const sources=index.sources.map(s=>`<div class="source-card"><span class="source-tier">${e(s.tier)}</span><a href="${e(s.url)}" target="_blank" rel="noopener">${e(s.title)} ↗</a><small>${e(s.publisher)}${s.date?'<br>Published '+e(s.date):''}<br>Used for: ${e(s.fields.join(', '))}</small></div>`).join('');
 return `<h3>Modeled coverage</h3><div class="evidence-note approx">${e(index.label)}. ${e(index.method)}</div><div class="associated coverage-slices">${buttons}</div><dl><dt>Range used</dt><dd>${e(r.range_km)} km · ${e(r.model)}</dd><dt>Antenna height</dt><dd>${e(r.antenna_m)} m MSL (terrain ${e(r.ground_m)} m + assumed tower)</dd>${rows}</dl><details><summary>Model assumptions & sources</summary><ul class="assumptions">${index.assumptions.map(a=>`<li>${e(a)}</li>`).join('')}</ul>${sources}</details>`;
}
