"use client";

import type { QueryResult } from "@/app/page";

interface Props {
  result: QueryResult;
}

const typeLabel: Record<string, string> = {
  single_fact: "Single fact",
  multi_part: "Multi-part",
  summarization: "Summarization",
};

export default function AnswerDisplay({ result }: Props) {
  return (
    <section className="space-y-3">
      <div className="flex items-center gap-3">
        <h2 className="text-sm font-medium text-gray-700">Answer</h2>
        <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
          {typeLabel[result.query_type] ?? result.query_type}
        </span>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white px-5 py-4 text-sm leading-relaxed whitespace-pre-wrap shadow-sm">
        {result.answer}
      </div>

      {result.sub_queries.length > 1 && (
        <details className="text-xs text-gray-400">
          <summary className="cursor-pointer select-none">
            Sub-queries ({result.sub_queries.length})
          </summary>
          <ol className="mt-1 ml-4 list-decimal space-y-0.5">
            {result.sub_queries.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ol>
        </details>
      )}
    </section>
  );
}
