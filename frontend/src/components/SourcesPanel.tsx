"use client";

import { useState } from "react";
import type { SourceChunk } from "@/app/page";

interface Props {
  sources: SourceChunk[];
}

export default function SourcesPanel({ sources }: Props) {
  const [open, setOpen] = useState(false);

  if (!sources.length) return null;

  return (
    <section>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-800 transition-colors"
      >
        <span>{open ? "▲" : "▼"}</span>
        <span>
          Sources ({sources.length} chunk{sources.length !== 1 ? "s" : ""})
        </span>
      </button>

      {open && (
        <div className="mt-3 space-y-3">
          {sources.map((src, i) => (
            <div
              key={src.doc_id}
              className="rounded-lg border border-gray-200 bg-white px-4 py-3 text-xs shadow-sm"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold text-gray-700">
                  [{i + 1}] {src.source} — page {src.page}
                </span>
                <span className="text-gray-400">
                  score: {src.score.toFixed(3)}
                </span>
              </div>
              <p className="text-gray-500 leading-relaxed line-clamp-4">
                {src.text}
              </p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
