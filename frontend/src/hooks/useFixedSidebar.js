import { useEffect, useState } from 'react';

function findScrollContainer(el) {
  let p = el?.parentElement;
  while (p) {
    const s = window.getComputedStyle(p);
    if (/(auto|scroll)/.test(s.overflowY)) return p;
    p = p.parentElement;
  }
  return null;
}

/**
 * Hook que fija un sidebar usando position: fixed cuando scrollea fuera del
 * viewport. Diseñado para layouts con scroll encapsulado (ej. <main> con
 * overflow-y-auto) donde CSS position: sticky es incompatible.
 *
 * @param {React.RefObject} asideRef – ref al <aside> contenedor
 * @param {number} threshold – px desde el top del viewport donde fijar (default 90)
 * @returns {{ fixed: boolean, style: { top?: number, left?: number, width?: number, height?: number } }}
 */
export default function useFixedSidebar(asideRef, threshold = 90) {
  const [state, setState] = useState({ fixed: false, style: {} });

  useEffect(() => {
    const aside = asideRef?.current;
    if (!aside) return;

    const main = findScrollContainer(aside);
    if (!main) return;

    let metrics = {};
    let raf = null;

    const measure = () => {
      const rect = aside.getBoundingClientRect();
      const mainRect = main.getBoundingClientRect();
      // Calcular offset del aside relativo al main (scroll container)
      let offsetTop = 0;
      let el = aside;
      while (el && el !== main) {
        offsetTop += el.offsetTop;
        el = el.offsetParent;
      }
      metrics = {
        left: rect.left,
        width: rect.width,
        height: rect.height,
        offsetTop,
        mainTop: mainRect.top,
      };
    };

    const onScroll = () => {
      if (raf) return;
      raf = requestAnimationFrame(() => {
        raf = null;
        const scrollTop = main.scrollTop;
        const trigger = metrics.offsetTop - threshold;
        const shouldFix = scrollTop > trigger;
        setState((prev) => {
          if (prev.fixed === shouldFix) return prev;
          return {
            fixed: shouldFix,
            style: shouldFix
              ? {
                  top: threshold + metrics.mainTop,
                  left: metrics.left,
                  width: metrics.width,
                  height: metrics.height,
                }
              : {},
          };
        });
      });
    };

    const onResize = () => {
      measure();
      onScroll();
    };

    measure();
    main.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onResize);
    onScroll();

    return () => {
      main.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onResize);
      if (raf) cancelAnimationFrame(raf);
    };
  }, [asideRef, threshold]);

  return state;
}
