"use client";

import { FormEvent, useMemo, useState } from "react";

type ChatMessage = {
  role: "client" | "consultant";
  message: string;
};

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export default function HomePage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "consultant",
      message:
        "Hi there! I'm your Issa Compass visa assistant. Tell me a bit about your situation and what you want to do in Thailand. 😊",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const chatHistoryForBackend = useMemo(
    () =>
      messages.map((m) => ({
        role: m.role,
        message: m.message,
      })),
    [messages]
  );

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage: ChatMessage = {
      role: "client",
      message: input.trim(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${BACKEND_URL}/generate-reply`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          clientSequence: userMessage.message,
          chatHistory: chatHistoryForBackend,
        }),
      });

      const data = (await res.json().catch(() => ({}))) as {
        aiReply?: string;
        error?: string;
      };

      if (!res.ok) {
        const message =
          (data && (data as any).error) || `Backend error (${res.status})`;
        throw new Error(message);
      }

      const aiText =
        data.aiReply ??
        "Sorry, I couldn't generate a reply just now. Please try again.";

      setMessages((prev) => [
        ...prev,
        {
          role: "consultant",
          message: aiText,
        },
      ]);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Something went wrong talking to the backend.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="w-full max-w-3xl mx-auto p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl shadow-xl flex flex-col h-[80vh] overflow-hidden">
        <header className="px-4 py-3 border-b border-slate-800 flex items-center justify-between bg-slate-900/70">
          <div>
            <h1 className="text-lg font-semibold">Issa Compass Visa Chat</h1>
            <p className="text-xs text-slate-400">
              Self-learning assistant backed by your Flask microservice
            </p>
          </div>
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-900/40 px-3 py-1 text-xs text-emerald-300 border border-emerald-700/60">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            Connected
          </span>
        </header>

        <section className="flex-1 overflow-y-auto px-4 py-3 space-y-3 bg-gradient-to-b from-slate-950 to-slate-900">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${
                msg.role === "client" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm leading-relaxed whitespace-pre-wrap ${
                  msg.role === "client"
                    ? "bg-sky-600 text-white rounded-br-sm"
                    : "bg-slate-800 text-slate-50 rounded-bl-sm"
                }`}
              >
                {msg.message}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-slate-800 text-slate-300 rounded-2xl rounded-bl-sm px-3 py-2 text-sm flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-slate-400 animate-bounce" />
                Typing…
              </div>
            </div>
          )}
        </section>

        <footer className="border-t border-slate-800 bg-slate-900/80 px-4 py-3">
          {error && (
            <p className="mb-2 text-xs text-red-300 bg-red-900/40 border border-red-700/60 rounded-md px-2 py-1">
              {error}
            </p>
          )}
          <form onSubmit={handleSubmit} className="flex items-center gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about DTV, your documents, timing, etc..."
              className="flex-1 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-50 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="inline-flex items-center justify-center rounded-xl bg-sky-600 px-4 py-2 text-sm font-medium text-white shadow hover:bg-sky-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Sending..." : "Send"}
            </button>
          </form>
          <p className="mt-1 text-[10px] text-slate-500">
            Backend URL: <code>{BACKEND_URL}</code>
          </p>
        </footer>
      </div>
