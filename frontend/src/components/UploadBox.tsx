"use client";

import { useState, useRef } from "react";

interface Props {
  apiUrl: string;
  onSuccess: () => void;
}

export default function UploadBox({ apiUrl, onSuccess }: Props) {
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [isError, setIsError] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setIsError(true);
      setMessage("Only PDF files are accepted.");
      return;
    }
    setUploading(true);
    setMessage(null);
    const form = new FormData();
    form.append("file", file);
    const baseApi = apiUrl.replace(/\/+$/, "");
    try {
      const res = await fetch(`${baseApi}/ingest`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? "Upload failed");
      }
      const data = await res.json();
      setIsError(false);
      setMessage(
        `✓ Indexed "${data.filename}" — ${data.chunks_added} new chunks (${data.total_indexed} total).`
      );
      onSuccess();
    } catch (e: unknown) {
      setIsError(true);
      setMessage(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div className="space-y-2">
      <div
        onDrop={onDrop}
        onDragOver={(e) => e.preventDefault()}
        onClick={() => inputRef.current?.click()}
        className="border-2 border-dashed border-gray-300 rounded-lg px-6 py-8 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors"
      >
        <p className="text-sm text-gray-500">
          {uploading
            ? "Uploading & indexing…"
            : "Drag & drop a PDF here, or click to select"}
        </p>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={onInputChange}
        />
      </div>
      {message && (
        <p
          className={`text-sm px-1 ${
            isError ? "text-red-600" : "text-green-700"
          }`}
        >
          {message}
        </p>
      )}
    </div>
  );
}
