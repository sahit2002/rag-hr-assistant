"use client";

import { useState } from "react";

interface Props {
  onSubmit: (question: string) => void;
  loading: boolean;
}

export default function QuestionBox({ onSubmit, loading }: Props) {
  const [question, setQuestion] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (question.trim()) onSubmit(question.trim());
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        type="text"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="e.g. How many sick days am I entitled to per year?"
        disabled={loading}
        className="flex-1 rounded-md border border-gray-300 px-4 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-50"
      />
      <button
        type="submit"
        disabled={loading || !question.trim()}
        className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? "Thinking…" : "Ask"}
      </button>
    </form>
  );
}
