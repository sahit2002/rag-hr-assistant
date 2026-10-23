"use client";

import { useEffect, useState } from "react";

interface StatusData {
  total_chunks: number;
  indexed: number;
  sources: string[];
}

interface Props {
  apiUrl: string;
  refresh: number;
}

export default function StatusBadge({ apiUrl, refresh }: Props) {
  const [status, setStatus] = useState<StatusData | null>(null);

  useEffect(() => {
    const baseApi = apiUrl.replace(/\/+$/, "");
    fetch(`${baseApi}/status`)
      .then((r) => r.json())
      .then(setStatus)
      .catch(() => setStatus(null));
  }, [apiUrl, refresh]);

  if (!status) return null;

  const hasIndex = status.indexed > 0;

  return (
    <div
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium ${
        hasIndex
          ? "bg-green-50 text-green-700 border border-green-200"
          : "bg-yellow-50 text-yellow-700 border border-yellow-200"
      }`}
    >
      <span
        className={`h-2 w-2 rounded-full ${
          hasIndex ? "bg-green-500" : "bg-yellow-400"
        }`}
      />
      {hasIndex
        ? `Index ready — ${status.indexed} chunks from ${status.sources.length} file(s)`
        : "No documents indexed yet"}
    </div>
  );
}
