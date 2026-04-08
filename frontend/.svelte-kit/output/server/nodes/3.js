import * as universal from '../entries/pages/_page.js';

export const index = 3;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/_page.svelte.js')).default;
export { universal };
export const universal_id = "src/routes/+page.js";
export const imports = ["_app/immutable/nodes/3.bBFiqB2q.js","_app/immutable/chunks/CJpXVGlq.js","_app/immutable/chunks/ki_1NypW.js","_app/immutable/chunks/Kwgczlxp.js","_app/immutable/chunks/Bi0YyVqG.js","_app/immutable/chunks/CGl4CnfS.js"];
export const stylesheets = [];
export const fonts = [];
