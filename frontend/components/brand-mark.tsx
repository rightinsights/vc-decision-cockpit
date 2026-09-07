"use client";

import { useState } from "react";

/** Logo mark from /brand-mark.png (drop the file into frontend/public). Falls back to a monogram until it exists. */
export function BrandMark({ size = 36 }: { size?: number }) {
  const [missing, setMissing] = useState(false);
  if (missing) {
    return (
      <span
        className="flex items-center justify-center border border-paper/40 text-[11px] font-bold tracking-wider"
        style={{ width: size, height: size }}
      >
        RI
      </span>
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src="/brand-mark.png"
      alt=""
      width={size}
      height={size}
      className="object-contain"
      style={{ width: size, height: size }}
      onError={() => setMissing(true)}
    />
  );
}
