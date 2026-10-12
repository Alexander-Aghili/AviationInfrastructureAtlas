// Symmetric SVG view boxes keep symbols centered independently of font metrics.
const shapes={
 navigation:'<path d="M12 3 21 12 12 21 3 12Z" fill="currentColor" stroke="white" stroke-width="1.5"/>',
 radar:'<path d="M5 5 17 17M5 5C2 12 10 20 17 17M10 14 7 21M4 21H13M16 3C19 4 21 6 21 9M15 7C17 8 18 9 18 11"/>',
 centers:'<path d="M4 4H20V20H4Z"/><path d="M8 8H16V16H8Z" fill="currentColor" stroke="none"/>',
 towers:'<path d="M6 21H18M9 21V11H15V21M5 5H19L17 11H7ZM8 2H16V5"/>',
 control:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4.5"/><path d="M12 12 18.4 5.6"/><circle cx="15.5" cy="15.5" r="1.4" fill="currentColor" stroke="none"/>',
 communications:'<path d="M12 5V21M7 21H17M12 12 7 21M12 12 17 21M7 4C3 8 3 12 7 16M17 4C21 8 21 12 17 16M9 7C7 9 7 11 9 13M15 7C17 9 17 11 15 13"/>',
 landing:'<path d="M12 3 21 20H3Z"/><path d="M12 9V15M12 18V18.2"/>',
 weather:'<path d="M6 18H18C23 18 23 10 18 10 17 3 7 3 6 10 0 10 1 18 6 18Z"/>'
};
// FAA ATC facility types for towers that also provide approach/departure control.
const approachTowerTypes=['ATCT-TRACON','ATCT-RAPCON','ATCT-A/C','ATCT-RATCF'];
export const providesApproach=f=>f?.feature_type==='towers'&&approachTowerTypes.includes(f.subtype);
const approachBadge='<g class="approach-badge"><circle cx="19.5" cy="4.5" r="4.3" fill="#1f8a9e" stroke="white" stroke-width="1.2"/><path d="M19.5 4.5 22 2" stroke="white" stroke-width="1.2"/></g>';
export function symbolSvg(kind,f){return `<svg class="facility-symbol" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${shapes[kind]||shapes.towers}${providesApproach({feature_type:kind,subtype:f?.subtype})?approachBadge:''}</svg>`;}
export const selectionSvg='<svg viewBox="0 0 34 34" width="34" height="34" fill="none" stroke="#137d98" stroke-width="2" aria-hidden="true"><path d="M2 10V2H10M24 2H32V10M32 24V32H24M10 32H2V24"/></svg>';
