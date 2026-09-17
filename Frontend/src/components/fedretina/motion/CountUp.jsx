/**
 * Number that counts up to its value once, on mount.
 * INPUT: target value, optional suffix and duration.
 * OUTPUT: an animated number that respects reduced-motion preferences.
 */
import { useEffect, useState } from "react";
export function CountUp({ value, suffix = "", duration = 1100, }) {
    const [shown, setShown] = useState(0);
    useEffect(() => {
        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            setShown(value);
            return;
        }
        let frame = 0;
        const start = performance.now();
        const tick = (now) => {
            const progress = Math.min((now - start) / duration, 1);
            // ease-out so the number settles gently
            setShown(Math.round(value * (1 - Math.pow(1 - progress, 3))));
            if (progress < 1)
                frame = requestAnimationFrame(tick);
        };
        frame = requestAnimationFrame(tick);
        return () => cancelAnimationFrame(frame);
    }, [value, duration]);
    return (<>
      {shown}
      {suffix}
    </>);
}
