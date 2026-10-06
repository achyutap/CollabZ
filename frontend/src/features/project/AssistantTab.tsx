"use client";

import { KeyboardEvent, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import clsx from "clsx";
import { Bot, Send } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import { toast } from "@/lib/toast";
import type { ChatMessageOut } from "@/lib/types";
import { Spinner } from "@/components/common";
import { skillLabel } from "@/components/common/skills";
import type { TabProps } from "./components/tabTypes";
import CodeBlock from "./components/CodeBlock";
import { useErrorToast } from "./components/hooks";
import { errMsg } from "./components/format";

const MAX_LEN = 2000;

export default function AssistantTab({ projectId, project }: TabProps) {
  const path = `/projects/${projectId}/chat`;
  const { data, error, loading } = useFetch<ChatMessageOut[]>(path);
  useErrorToast(error);

  const [messages, setMessages] = useState<ChatMessageOut[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [limitNotice, setLimitNotice] = useState<string | null>(null);
  const [failedText, setFailedText] = useState<string | null>(null);
  const seeded = useRef(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (data && !seeded.current) {
      seeded.current = true;
      setMessages(data);
    }
  }, [data]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, sending, failedText]);

  const limited = limitNotice !== null;
  const firstSkill = project.problem.required_skills[0];
  const chips = [
    "Explain the project requirements",
    "Review my commit message",
    firstSkill ? `Suggest an approach for ${skillLabel(firstSkill)}` : "Suggest an approach for this project",
    "What should I do next?",
  ];
  const last = messages[messages.length - 1];
  const showChips =
    !loading && !sending && !limited && failedText === null && (!last || last.role === "assistant");

  async function send(raw: string) {
    const text = raw.trim();
    if (!text || sending || limited) return;
    const optimistic: ChatMessageOut = {
      id: `tmp-${Date.now()}`,
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    };
    setMessages((m) => [...m, optimistic]);
    setInput("");
    setFailedText(null);
    setSending(true);
    try {
      const res = await api.post<{ reply: string }>(path, { message: text });
      setMessages((m) => [
        ...m,
        { id: `a-${Date.now()}`, role: "assistant", content: res.reply, created_at: new Date().toISOString() },
      ]);
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setLimitNotice(err.detail || "You've reached the message limit. Please try again later.");
      } else if (err instanceof ApiError && err.status === 503) {
        setMessages((m) => m.filter((x) => x.id !== optimistic.id));
        setFailedText(text);
      } else {
        setMessages((m) => m.filter((x) => x.id !== optimistic.id));
        setInput(text);
        toast.error(errMsg(err));
      }
    } finally {
      setSending(false);
    }
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send(input);
    }
  }

  return (
    <div className="card flex h-[calc(100vh-20rem)] min-h-[460px] flex-col overflow-hidden p-0">
      <div className="flex items-center gap-2 border-b border-gray-100 px-4 py-3 text-sm text-gray-600">
        <Bot className="h-4 w-4 shrink-0 text-indigo-600" aria-hidden="true" />
        AI assistant for this project. It guides you but won&apos;t write your submissions.
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto p-4" aria-live="polite">
        {loading && !data ? (
          <div className="flex justify-center py-6">
            <Spinner />
          </div>
        ) : messages.length === 0 ? (
          <p className="py-6 text-center text-sm text-gray-500">
            Ask anything about this project to get started.
          </p>
        ) : (
          messages.map((m) => (
            <div key={m.id} className={clsx("flex", m.role === "user" ? "justify-end" : "justify-start")}>
              {m.role === "user" ? (
                <div className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-2.5 text-sm text-white">
                  {m.content}
                </div>
              ) : (
                <div className="max-w-[90%] break-words rounded-2xl rounded-bl-sm border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm text-gray-800">
                  <div className="[&_a]:text-indigo-600 [&_a]:underline [&_ol]:list-decimal [&_ol]:pl-5 [&_p+p]:mt-2 [&_ul]:list-disc [&_ul]:pl-5 [&_:not(pre)>code]:rounded [&_:not(pre)>code]:bg-gray-200 [&_:not(pre)>code]:px-1 [&_:not(pre)>code]:py-0.5 [&_:not(pre)>code]:text-xs">
                    <ReactMarkdown components={{ pre: ({ children }) => <CodeBlock>{children}</CodeBlock> }}>
                      {m.content}
                    </ReactMarkdown>
                  </div>
                </div>
              )}
            </div>
          ))
        )}

        {sending && (
          <div className="flex justify-start" role="status" aria-label="Assistant is typing">
            <div className="flex items-center gap-1 rounded-2xl rounded-bl-sm border border-gray-200 bg-gray-50 px-4 py-3">
              {[0, 150, 300].map((d) => (
                <span
                  key={d}
                  className="h-2 w-2 animate-bounce rounded-full bg-gray-400"
                  style={{ animationDelay: `${d}ms` }}
                />
              ))}
            </div>
          </div>
        )}

        {failedText !== null && (
          <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            The AI assistant is unavailable right now.
            <button
              type="button"
              onClick={() => void send(failedText)}
              className="ml-2 font-medium underline hover:no-underline"
            >
              Retry
            </button>
          </div>
        )}

        {limited && (
          <div role="alert" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
            {limitNotice}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div className="border-t border-gray-100 p-3">
        {showChips && (
          <div className="mb-3 flex flex-wrap gap-2">
            {chips.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => void send(c)}
                className="rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-100"
              >
                {c}
              </button>
            ))}
          </div>
        )}
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <label htmlFor="assistant-input" className="sr-only">
              Message the assistant
            </label>
            <textarea
              id="assistant-input"
              value={input}
              onChange={(e) => setInput(e.target.value.slice(0, MAX_LEN))}
              onKeyDown={onKeyDown}
              rows={2}
              maxLength={MAX_LEN}
              disabled={limited}
              placeholder={limited ? "Message limit reached" : "Type a message. Enter to send, Shift+Enter for a new line"}
              className="input resize-none"
            />
            <p className="mt-1 text-right text-xs tabular-nums text-gray-400">
              {input.length}/{MAX_LEN}
            </p>
          </div>
          <button
            type="button"
            onClick={() => void send(input)}
            disabled={!input.trim() || sending || limited}
            aria-label="Send message"
            className="btn btn-primary mb-6 !px-2.5"
          >
            <Send className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
  );
}
