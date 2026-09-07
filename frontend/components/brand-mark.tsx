"use client";

import { useState } from "react";

/**
 * Logo mark from /brand-mark.png (drop the file into frontend/public). Shows a monogram until the
 * image has actually loaded, so a missing or slow file never flashes a broken-image icon.
 */
export function BrandMark({ size = 36 }: { size?: number }) {
  const [state, setState] = useState<"loading" | "ready" | "missing">("loading");
  return (
    <span className="relative inline-flex shrink-0 items-center justify-center" style={{ width: size, height: size }}>
      {state !== "ready" && (
        <span
          className="flex items-center justify-center rounded-sm border border-paper/40 text-[11px] font-bold tracking-wider"
          style={{ width: size, height: size }}
        >
          RI
        </span>
      )}
      {state !== "missing" && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src="/brand-mark.png"
          alt=""
          width={size}
          height={size}
          className="absolute inset-0 object-contain"
          style={{ width: size, height: size, opacity: state === "ready" ? 1 : 0 }}
          onLoad={() => setState("ready")}
          onError={() => setState("missing")}
        />
      )}
    </span>
  );
}
