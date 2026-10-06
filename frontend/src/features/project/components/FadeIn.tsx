"use client";

import { ReactNode, useEffect, useState } from "react";
import clsx from "clsx";

export default function FadeIn({ children, delayMs = 0 }: { children: ReactNode; delayMs?: number }) {
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setShown(true), 50 + delayMs);
    return () => clearTimeout(t);
  }, [delayMs]);

  return (
    <div className={clsx("transition-opacity duration-700", shown ? "opacity-100" : "opacity-0")}>
      {children}
    </div>
  );
}
