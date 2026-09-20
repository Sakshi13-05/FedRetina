/**
 * Scroll reveal wrapper.
 * INPUT: children plus an optional delay in ms.
 * OUTPUT: content that fades and slides up the first time it enters the screen.
 */
import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
export function Reveal({ children, delay = 0, className, as: Tag = "div" }) {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.15 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  return (
    <Tag
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ref={ref}
      data-visible={visible}
      style={{ transitionDelay: `${delay}ms` }}
      className={cn("fr-reveal", className)}
    >
      {children}
    </Tag>
  );
}
