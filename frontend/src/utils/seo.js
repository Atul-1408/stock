import { useEffect } from "react";

const BRAND = "Sovereign Intelligence";

function setMeta(selector, attr, value, create) {
  let el = document.head.querySelector(selector);
  if (!el && create) {
    el = document.createElement(create.tag);
    Object.entries(create.attrs).forEach(([k, v]) => el.setAttribute(k, v));
    document.head.appendChild(el);
  }
  if (el) el.setAttribute(attr, value);
}

/**
 * Per-page SEO: title, description, robots, canonical, Open Graph.
 * Private pages pass `noindex` so search engines never list the terminal.
 */
export function useSeo({ title, description, noindex = false, path } = {}) {
  useEffect(() => {
    const fullTitle = title ? `${title} | ${BRAND}` : document.title;
    document.title = fullTitle;

    if (description) {
      setMeta('meta[name="description"]', "content", description);
      setMeta('meta[property="og:description"]', "content", description);
      setMeta('meta[name="twitter:description"]', "content", description);
    }
    setMeta('meta[property="og:title"]', "content", fullTitle);
    setMeta('meta[name="twitter:title"]', "content", fullTitle);

    setMeta(
      'meta[name="robots"]',
      "content",
      noindex ? "noindex, nofollow" : "index, follow, max-image-preview:large",
      { tag: "meta", attrs: { name: "robots" } }
    );

    const url = window.location.origin + (path ?? window.location.pathname);
    setMeta('link[rel="canonical"]', "href", url, { tag: "link", attrs: { rel: "canonical" } });
    setMeta('meta[property="og:url"]', "content", url);
  }, [title, description, noindex, path]);
}

export default function Seo(props) {
  useSeo(props);
  return null;
}
