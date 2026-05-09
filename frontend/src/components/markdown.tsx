"use client";

import { Fragment, type ReactNode } from "react";

type Block =
  | { kind: "heading"; level: 1 | 2 | 3 | 4; text: string }
  | { kind: "ul"; items: string[] }
  | { kind: "ol"; items: string[] }
  | { kind: "code"; text: string }
  | { kind: "p"; text: string }
  | { kind: "hr" };

const HEADING_RE = /^(#{1,4})\s+(.*)$/;
const ULI_RE = /^\s*[-*]\s+(.*)$/;
const OLI_RE = /^\s*\d+\.\s+(.*)$/;

function parse(md: string): Block[] {
  const out: Block[] = [];
  const lines = md.replace(/\r\n/g, "\n").split("\n");
  let i = 0;

  while (i < lines.length) {
    const raw = lines[i];
    const line = raw.trimEnd();

    if (line.trim() === "") {
      i += 1;
      continue;
    }

    if (line.trim() === "---" || line.trim() === "***") {
      out.push({ kind: "hr" });
      i += 1;
      continue;
    }

    if (line.startsWith("```")) {
      const buf: string[] = [];
      i += 1;
      while (i < lines.length && !lines[i].startsWith("```")) {
        buf.push(lines[i]);
        i += 1;
      }
      if (i < lines.length) i += 1;
      out.push({ kind: "code", text: buf.join("\n") });
      continue;
    }

    const h = line.match(HEADING_RE);
    if (h) {
      const level = Math.min(4, h[1].length) as 1 | 2 | 3 | 4;
      out.push({ kind: "heading", level, text: h[2].trim() });
      i += 1;
      continue;
    }

    const uli = line.match(ULI_RE);
    if (uli) {
      const items: string[] = [uli[1]];
      i += 1;
      while (i < lines.length) {
        const m = lines[i].match(ULI_RE);
        if (!m) break;
        items.push(m[1]);
        i += 1;
      }
      out.push({ kind: "ul", items });
      continue;
    }

    const oli = line.match(OLI_RE);
    if (oli) {
      const items: string[] = [oli[1]];
      i += 1;
      while (i < lines.length) {
        const m = lines[i].match(OLI_RE);
        if (!m) break;
        items.push(m[1]);
        i += 1;
      }
      out.push({ kind: "ol", items });
      continue;
    }

    const buf: string[] = [line];
    i += 1;
    while (i < lines.length) {
      const next = lines[i];
      if (
        next.trim() === "" ||
        HEADING_RE.test(next) ||
        ULI_RE.test(next) ||
        OLI_RE.test(next) ||
        next.startsWith("```")
      ) {
        break;
      }
      buf.push(next);
      i += 1;
    }
    out.push({ kind: "p", text: buf.join(" ") });
  }

  return out;
}

function renderInline(text: string): ReactNode[] {
  const tokens: ReactNode[] = [];
  let rest = text;
  let key = 0;
  const pattern = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/;

  while (rest.length > 0) {
    const m = rest.match(pattern);
    if (!m || m.index === undefined) {
      tokens.push(<Fragment key={key++}>{rest}</Fragment>);
      break;
    }
    if (m.index > 0) {
      tokens.push(<Fragment key={key++}>{rest.slice(0, m.index)}</Fragment>);
    }
    const tok = m[0];
    if (tok.startsWith("**")) {
      tokens.push(
        <strong key={key++} className="font-semibold text-slate-900">
          {tok.slice(2, -2)}
        </strong>,
      );
    } else if (tok.startsWith("`")) {
      tokens.push(
        <code
          key={key++}
          className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[0.85em] text-slate-800"
        >
          {tok.slice(1, -1)}
        </code>,
      );
    } else {
      tokens.push(
        <em key={key++} className="italic">
          {tok.slice(1, -1)}
        </em>,
      );
    }
    rest = rest.slice(m.index + tok.length);
  }
  return tokens;
}

export function Markdown({
  text,
  className,
}: {
  text: string;
  className?: string;
}) {
  const blocks = parse(text || "");
  return (
    <div
      className={
        className ??
        "space-y-2 text-sm leading-relaxed text-slate-800 [&_strong]:font-semibold"
      }
    >
      {blocks.map((b, i) => {
        if (b.kind === "heading") {
          if (b.level === 1)
            return (
              <h2
                key={i}
                className="mt-3 text-base font-semibold tracking-tight text-slate-900"
              >
                {renderInline(b.text)}
              </h2>
            );
          if (b.level === 2)
            return (
              <h3
                key={i}
                className="mt-3 text-sm font-semibold tracking-tight text-slate-900"
              >
                {renderInline(b.text)}
              </h3>
            );
          if (b.level === 3)
            return (
              <h4
                key={i}
                className="mt-2 text-[13px] font-semibold uppercase tracking-wide text-slate-700"
              >
                {renderInline(b.text)}
              </h4>
            );
          return (
            <h5
              key={i}
              className="mt-2 text-xs font-semibold uppercase tracking-wide text-slate-600"
            >
              {renderInline(b.text)}
            </h5>
          );
        }
        if (b.kind === "ul") {
          return (
            <ul key={i} className="list-disc space-y-1 pl-5">
              {b.items.map((it, j) => (
                <li key={j}>{renderInline(it)}</li>
              ))}
            </ul>
          );
        }
        if (b.kind === "ol") {
          return (
            <ol key={i} className="list-decimal space-y-1 pl-5">
              {b.items.map((it, j) => (
                <li key={j}>{renderInline(it)}</li>
              ))}
            </ol>
          );
        }
        if (b.kind === "code") {
          return (
            <pre
              key={i}
              className="overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3 font-mono text-xs text-slate-800"
            >
              {b.text}
            </pre>
          );
        }
        if (b.kind === "hr") {
          return <hr key={i} className="my-2 border-slate-200" />;
        }
        return (
          <p key={i} className="leading-relaxed">
            {renderInline(b.text)}
          </p>
        );
      })}
    </div>
  );
}
