import { useEffect, useRef } from 'react';
import './StickyPageHeader.css';

// Scroll distance (px) over which the header morphs from expanded -> compact.
const COLLAPSE_DISTANCE = 120;

export default function StickyPageHeader({ code = 'A1.3.1', title = 'Describe the role of operating systems' }) {
  const headerRef = useRef(null);
  const progressRef = useRef(-1);

  useEffect(() => {
    const el = headerRef.current;
    if (!el) return;

    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let frame = 0;

    const apply = () => {
      frame = 0;
      const raw = Math.min(window.scrollY / COLLAPSE_DISTANCE, 1);
      // Snap to the endpoints when motion is reduced: same two states, no in-between.
      const p = reduceMotion ? (raw > 0.5 ? 1 : 0) : raw;
      if (Math.abs(p - progressRef.current) < 0.001) return;
      progressRef.current = p;
      // Drive everything off one custom property so there is no re-render per frame.
      el.style.setProperty('--p', p.toFixed(4));
      el.classList.toggle('is-compact', p > 0.99);
    };

    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(apply);
    };

    apply();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', onScroll);
      if (frame) cancelAnimationFrame(frame);
    };
  }, []);

  return (
    <header ref={headerRef} className="sph">
      <div className="sph__inner">
        <span className="sph__code">{code}</span>
        <h1 className="sph__title">{title}</h1>
      </div>
    </header>
  );
}
