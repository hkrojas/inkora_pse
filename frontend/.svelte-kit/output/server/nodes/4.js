import * as universal from '../entries/pages/about/_page.js';

export const index = 4;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/about/_page.svelte.js')).default;
export { universal };
export const universal_id = "src/routes/about/+page.js";
export const imports = ["_app/immutable/nodes/4.CtAB1Bdb.js","_app/immutable/chunks/ki_1NypW.js","_app/immutable/chunks/CJpXVGlq.js","_app/immutable/chunks/Kwgczlxp.js","_app/immutable/chunks/B9YsLxdZ.js","_app/immutable/chunks/CsoWUHaV.js","_app/immutable/chunks/Bi0YyVqG.js","_app/immutable/chunks/BJmOjZ3w.js"];
export const stylesheets = [];
export const fonts = [];
