import { k as head } from "../../../chunks/index2.js";
import "../../../chunks/url.js";
import "@sveltejs/kit/internal/server";
import "../../../chunks/root.js";
function _page($$renderer) {
  head("cwls5q", $$renderer, ($$renderer2) => {
    $$renderer2.title(($$renderer3) => {
      $$renderer3.push(`<title>About</title>`);
    });
    $$renderer2.push(`<meta name="description" content="About this app"/>`);
  });
  $$renderer.push(`<div class="text-column"><h1>About this app</h1> <p>This is a <a href="https://svelte.dev/docs/kit">SvelteKit</a> app. You can make your own by typing
		the following into your command line and following the prompts:</p> <pre>npx sv create</pre> <p>The page you're looking at is purely static HTML, with no client-side interactivity needed.
		Because of that, we don't need to load any JavaScript. Try viewing the page's source, or opening
		the devtools network panel and reloading.</p></div>`);
}
export {
  _page as default
};
