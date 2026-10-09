import React from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { cn } from "@/lib/utils"

interface MarkdownContentProps {
  content: string
  className?: string
}

export function MarkdownContent({ content, className }: MarkdownContentProps) {
  if (!content) return null

  return (
    <div className={cn("markdown-body text-foreground max-w-none space-y-3", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children, ...props }) => (
            <h1
              className="mt-6 mb-3 text-2xl font-bold tracking-tight text-foreground sm:text-3xl first:mt-0"
              {...props}
            >
              {children}
            </h1>
          ),
          h2: ({ children, ...props }) => (
            <h2
              className="mt-5 mb-2.5 text-xl font-bold tracking-tight text-foreground sm:text-2xl first:mt-0 border-b border-border/40 pb-1.5"
              {...props}
            >
              {children}
            </h2>
          ),
          h3: ({ children, ...props }) => (
            <h3
              className="mt-4 mb-2 text-lg font-semibold tracking-tight text-foreground sm:text-xl first:mt-0"
              {...props}
            >
              {children}
            </h3>
          ),
          h4: ({ children, ...props }) => (
            <h4
              className="mt-3 mb-1.5 text-base font-semibold text-foreground first:mt-0"
              {...props}
            >
              {children}
            </h4>
          ),
          p: ({ children, ...props }) => (
            <p className="mb-3 leading-7 text-foreground/90 last:mb-0" {...props}>
              {children}
            </p>
          ),
          strong: ({ children, ...props }) => (
            <strong className="font-semibold text-foreground" {...props}>
              {children}
            </strong>
          ),
          em: ({ children, ...props }) => (
            <em className="italic text-foreground/90" {...props}>
              {children}
            </em>
          ),
          ul: ({ children, ...props }) => (
            <ul className="my-2.5 ml-5 list-disc space-y-1.5 text-foreground/90" {...props}>
              {children}
            </ul>
          ),
          ol: ({ children, ...props }) => (
            <ol className="my-2.5 ml-5 list-decimal space-y-1.5 text-foreground/90" {...props}>
              {children}
            </ol>
          ),
          li: ({ children, ...props }) => (
            <li className="leading-7" {...props}>
              {children}
            </li>
          ),
          blockquote: ({ children, ...props }) => (
            <blockquote
              className="my-3.5 border-l-4 border-primary/70 bg-muted/30 py-1.5 pl-4 pr-3 italic text-muted-foreground rounded-r"
              {...props}
            >
              {children}
            </blockquote>
          ),
          a: ({ href, children, ...props }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-primary underline underline-offset-4 hover:text-primary/80 transition-colors"
              {...props}
            >
              {children}
            </a>
          ),
          table: ({ children, ...props }) => (
            <div className="my-4 w-full overflow-x-auto rounded-xl border border-border/80 shadow-xs">
              <table className="w-full border-collapse text-left text-sm" {...props}>
                {children}
              </table>
            </div>
          ),
          thead: ({ children, ...props }) => (
            <thead className="border-b border-border bg-muted/60 text-xs uppercase font-semibold text-foreground" {...props}>
              {children}
            </thead>
          ),
          tbody: ({ children, ...props }) => (
            <tbody className="divide-y divide-border/50 bg-card" {...props}>
              {children}
            </tbody>
          ),
          tr: ({ children, ...props }) => (
            <tr className="transition-colors hover:bg-muted/30" {...props}>
              {children}
            </tr>
          ),
          th: ({ children, ...props }) => (
            <th className="px-4 py-2.5 font-semibold text-foreground" {...props}>
              {children}
            </th>
          ),
          td: ({ children, ...props }) => (
            <td className="px-4 py-2.5 text-foreground/90" {...props}>
              {children}
            </td>
          ),
          hr: ({ ...props }) => (
            <hr className="my-5 border-border/70" {...props} />
          ),
          code: ({ node, className, children, ...props }: any) => {
            const match = /language-(\w+)/.exec(className || "")
            const isCodeBlock = Boolean(match) || (typeof children === "string" && children.includes("\n"))

            if (!isCodeBlock) {
              return (
                <code
                  className="rounded-md border border-border/60 bg-muted/80 px-1.5 py-0.5 font-mono text-[0.875em] font-medium text-foreground"
                  {...props}
                >
                  {children}
                </code>
              )
            }

            return (
              <div className="relative my-3.5 overflow-hidden rounded-xl border border-border/80 bg-zinc-950 font-mono text-xs shadow-sm">
                {match && (
                  <div className="flex items-center justify-between border-b border-border/30 bg-zinc-900/90 px-3.5 py-1.5 text-[11px] font-medium text-zinc-400 tracking-wide uppercase">
                    <span>{match[1]}</span>
                  </div>
                )}
                <pre className="overflow-x-auto p-4 text-zinc-100 leading-relaxed">
                  <code className={className} {...props}>
                    {children}
                  </code>
                </pre>
              </div>
            )
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
export default MarkdownContent
