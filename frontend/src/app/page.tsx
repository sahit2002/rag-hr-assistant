"use client";

import { useState, useRef } from "react";
import UploadBox from "@/components/UploadBox";
import QuestionBox from "@/components/QuestionBox";
import AnswerDisplay from "@/components/AnswerDisplay";
import SourcesPanel from "@/components/SourcesPanel";
import StatusBadge from "@/components/StatusBadge";

export interface SourceChunk {
  source: string;
  page: string | number;
  chunk_index: number;
  doc_id: string;
  score: number;
  text: string;
}

export interface QueryResult {
  answer: string;
  sources: SourceChunk[];
  query_type: string;
  sub_queries: string[];
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function HomePage() {
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshStatus, setRefreshStatus] = useState(0);

  const handleUploadSuccess = () => setRefreshStatus((n) => n + 1);

  const handleQuestion = async (question: string) => {
    setLoading(true);
    setError(null);
    setQueryResult(null);
    try {
      const res = await fetch(`${API_URL}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? "Query failed");
      }
      const data: QueryResult = await res.json();
      setQueryResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="max-w-3xl mx-auto px-4 py-10 space-y-8">
      {/* Header */}
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          HR Policy Assistant
        </h1>
        <p className="text-sm text-gray-500">
          Upload your HR policy PDF, then ask any policy-related question.
        </p>
      </header>

      {/* Index status */}
      <StatusBadge apiUrl={API_URL} refresh={refreshStatus} />

      {/* Upload */}
      <section>
        <h2 className="text-sm font-medium text-gray-700 mb-2">
          1. Upload a policy document
        </h2>
        <UploadBox apiUrl={API_URL} onSuccess={handleUploadSuccess} />
      </section>

      {/* Question */}
      <section>
        <h2 className="text-sm font-medium text-gray-700 mb-2">
          2. Ask a question
        </h2>
        <QuestionBox onSubmit={handleQuestion} loading={loading} />
      </section>

      {/* Error */}
      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Answer */}
      {queryResult && (
        <>
          <AnswerDisplay result={queryResult} />
          <SourcesPanel sources={queryResult.sources} />
        </>
      )}
    </main>
  );
}
