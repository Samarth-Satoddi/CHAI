"use client"

import { useEffect, useMemo, useRef, useState, type RefObject } from "react"
import { MessageCircle, Search, X, Clock, FolderGit2, Trash2, LoaderCircle, AlertCircle, ChevronDown, ChevronRight } from "lucide-react"
import type { AssistantMode, WorkspaceLayout } from "@/components/chat-types"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"

const API_BASE = (import.meta as any).env?.VITE_API_BASE || "http://localhost:8000"

export interface SampleConversation {
  id: string
  title: string
  mode: AssistantMode
  layout: WorkspaceLayout
  prompt: string
  answer?: string
}

export interface SavedConversationSummary {
  id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
  preview?: string
}

export const SAMPLE_CONVERSATIONS: SampleConversation[] = [
  {
    id: "onboarding",
    title: "A better onboarding flow",
    mode: "ask",
    layout: "chat",
    prompt: "What makes a good first-run experience for a new user?",
    answer:
      "A good first-run experience helps someone reach a meaningful win quickly. Show one clear next step, explain why it matters, and avoid asking for information before it is useful. Keep the path easy to skip or revisit, then use early behavior to make the next visit feel more relevant.",
  },
  {
    id: "comparison",
    title: "Campaign performance snapshot",
    mode: "research",
    layout: "workspace",
    prompt: "Review this campaign performance snapshot with a trend chart, channel breakdown, and next steps.",
  },
  {
    id: "launch",
    title: "Growth action brief",
    mode: "agent",
    layout: "workspace",
    prompt: "Create a growth action plan from this campaign performance snapshot, with milestones and measures of success.",
  },
]

function formatRelativeTime(isoString: string): string {
  if (!isoString) return ""
  try {
    const date = new Date(isoString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    if (diffMs < 0) return "Just now"
    const diffSec = Math.floor(diffMs / 1000)
    const diffMin = Math.floor(diffSec / 60)
    const diffHours = Math.floor(diffMin / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffSec < 45) return "Just now"
    if (diffMin < 60) return `${diffMin}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays === 1) return "Yesterday"
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric" })
  } catch {
    return ""
  }
}

interface ChatHistoryPopoverProps {
  open: boolean
  currentTitle: string
  activeHistoryId: string | null
  userId?: string | null
  sessionId?: string | null
  triggerRef: RefObject<HTMLButtonElement | null>
  onSelectSavedConversation?: (convo: { id: string; title: string; messages: any[] }) => void
  onOpenSample: (sample: SampleConversation) => void
  onReturnToCurrent: () => void
  onClose: () => void
  onDeleteActiveConversation?: () => void
}

export function ChatHistoryPopover({
  open,
  currentTitle,
  activeHistoryId,
  userId,
  sessionId,
  triggerRef,
  onSelectSavedConversation,
  onOpenSample,
  onReturnToCurrent,
  onClose,
  onDeleteActiveConversation,
}: ChatHistoryPopoverProps) {
  const [searchTerm, setSearchTerm] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")
  const [savedConversations, setSavedConversations] = useState<SavedConversationSummary[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isOpeningId, setIsOpeningId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [samplesExpanded, setSamplesExpanded] = useState(false)
  const popoverRef = useRef<HTMLDivElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)

  // Debounce search input (250ms)
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchTerm.trim())
    }, 250)
    return () => clearTimeout(handler)
  }, [searchTerm])

  // Fetch backend history data
  useEffect(() => {
    if (!open) return

    let cancelled = false
    setIsLoading(true)
    setError(null)

    const effectiveSessionId = sessionId || (typeof window !== "undefined" ? localStorage.getItem("chai_session_id") || "" : "")
    const headers: Record<string, string> = {}
    if (userId && !userId.startsWith("guest") && userId !== "guest_session") headers["X-User-ID"] = userId
    if (effectiveSessionId) headers["X-Session-ID"] = effectiveSessionId

    const searchParam = debouncedSearch ? `?search=${encodeURIComponent(debouncedSearch)}` : ""
    fetch(`${API_BASE}/api/history${searchParam}`, { headers })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data: SavedConversationSummary[]) => {
        if (!cancelled && Array.isArray(data)) {
          setSavedConversations(data)
          setIsLoading(false)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError("Could not load conversations.")
          setIsLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [open, debouncedSearch, userId, sessionId])

  // Focus management & outside click handling
  useEffect(() => {
    if (!open) return

    const focusFrame = window.requestAnimationFrame(() => searchRef.current?.focus())
    const handlePointerDown = (event: PointerEvent) => {
      if (!(event.target instanceof Node)) return
      if (popoverRef.current?.contains(event.target)) return
      if (triggerRef.current?.contains(event.target)) return
      onClose()
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return
      onClose()
      window.requestAnimationFrame(() => triggerRef.current?.focus())
    }

    document.addEventListener("pointerdown", handlePointerDown)
    document.addEventListener("keydown", handleKeyDown)
    return () => {
      window.cancelAnimationFrame(focusFrame)
      document.removeEventListener("pointerdown", handlePointerDown)
      document.removeEventListener("keydown", handleKeyDown)
    }
  }, [onClose, open, triggerRef])

  async function handleSelectSaved(id: string) {
    if (id === "current" || (activeHistoryId && id === activeHistoryId)) {
      onReturnToCurrent()
      onClose()
      return
    }

    setIsOpeningId(id)
    const effectiveSessionId = sessionId || (typeof window !== "undefined" ? localStorage.getItem("chai_session_id") || "" : "")
    const headers: Record<string, string> = {}
    if (userId && !userId.startsWith("guest") && userId !== "guest_session") headers["X-User-ID"] = userId
    if (effectiveSessionId) headers["X-Session-ID"] = effectiveSessionId

    try {
      const res = await fetch(`${API_BASE}/api/history/${id}`, { headers })
      if (!res.ok) throw new Error("Failed to load conversation details")
      const detail = await res.json()
      onSelectSavedConversation?.(detail)
      onClose()
    } catch (e) {
      setError("Failed to open conversation.")
    } finally {
      setIsOpeningId(null)
    }
  }

  async function handleDeleteSaved(e: React.MouseEvent, id: string) {
    e.stopPropagation()
    const effectiveSessionId = sessionId || (typeof window !== "undefined" ? localStorage.getItem("chai_session_id") || "" : "")
    const headers: Record<string, string> = {}
    if (userId && !userId.startsWith("guest") && userId !== "guest_session") headers["X-User-ID"] = userId
    if (effectiveSessionId) headers["X-Session-ID"] = effectiveSessionId

    try {
      const res = await fetch(`${API_BASE}/api/history/${id}`, {
        method: "DELETE",
        headers,
      })
      if (res.ok) {
        setSavedConversations((prev) => prev.filter((c) => c.id !== id))
        if (id === activeHistoryId) {
          onDeleteActiveConversation?.()
        }
      }
    } catch {
      // ignore delete failure
    }
  }

  const filteredSamples = useMemo(() => {
    if (!debouncedSearch) return SAMPLE_CONVERSATIONS
    const q = debouncedSearch.toLowerCase()
    return SAMPLE_CONVERSATIONS.filter(
      (s) => s.title.toLowerCase().includes(q) || s.prompt.toLowerCase().includes(q)
    )
  }, [debouncedSearch])

  return (
    <div
      id="chat-history-popover"
      ref={popoverRef}
      role="dialog"
      aria-label="Conversation history"
      hidden={!open}
      className="absolute left-3 top-[56px] z-50 flex max-h-[min(82dvh,560px)] w-[min(380px,calc(100vw-1.5rem))] flex-col overflow-hidden rounded-2xl border border-border/80 bg-popover text-popover-foreground shadow-2xl backdrop-blur-md"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border/70 px-4 py-3 bg-muted/20">
        <div className="flex items-center gap-2">
          <Clock className="size-4 text-primary" />
          <h2 className="text-xs font-bold tracking-tight">Conversation History</h2>
        </div>
        <button
          type="button"
          aria-label="Close conversation history"
          onClick={onClose}
          className="grid size-7 place-items-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <X aria-hidden="true" className="size-4" />
        </button>
      </div>

      {/* Search Input */}
      <div className="p-3 border-b border-border/60">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            ref={searchRef}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.currentTarget.value)}
            placeholder="Search conversations..."
            className="h-8 pl-8 pr-7 text-xs bg-background/80"
          />
          {searchTerm && (
            <button
              type="button"
              onClick={() => setSearchTerm("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              aria-label="Clear search"
            >
              <X className="size-3" />
            </button>
          )}
        </div>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-3">
        {/* Active conversation pill */}
        {currentTitle && currentTitle !== "New chat" && !debouncedSearch && (
          <div className="mb-2">
            <p className="px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-muted-foreground">
              Current Chat
            </p>
            <button
              type="button"
              onClick={() => {
                onReturnToCurrent()
                onClose()
              }}
              className="mt-1 flex w-full items-center justify-between gap-3 rounded-xl px-3 py-2 text-left text-xs bg-primary/10 text-primary font-medium"
            >
              <div className="flex items-center gap-2 min-w-0">
                <MessageCircle className="size-3.5 shrink-0 text-primary" />
                <span className="truncate">{currentTitle}</span>
              </div>
              <span className="shrink-0 text-[10px] text-primary font-medium">Active</span>
            </button>
          </div>
        )}

        {/* Saved Conversations Section */}
        <div>
          <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground flex items-center justify-between">
            <span>Saved Conversations</span>
            <span className="text-[9px] font-normal lowercase">
              {isLoading ? "loading..." : `${savedConversations.length} saved`}
            </span>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center gap-2 py-8 text-xs text-muted-foreground">
              <LoaderCircle className="size-4 animate-spin text-primary" />
              <span>Loading history...</span>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center gap-2 py-6 text-xs text-destructive">
              <AlertCircle className="size-4" />
              <span>{error}</span>
            </div>
          ) : savedConversations.length === 0 ? (
            <div className="px-3 py-6 text-center text-xs text-muted-foreground">
              {debouncedSearch ? (
                <p>No conversations found matching &quot;{debouncedSearch}&quot;.</p>
              ) : (
                <p>No saved conversations yet. Chat to save your history automatically.</p>
              )}
            </div>
          ) : (
            <div className="mt-1 flex flex-col gap-1">
              {savedConversations.map((item) => {
                const isSelected = activeHistoryId === item.id
                const isOpening = isOpeningId === item.id

                return (
                  <button
                    key={item.id}
                    type="button"
                    disabled={isOpening}
                    onClick={() => handleSelectSaved(item.id)}
                    className={cn(
                      "group flex w-full items-center justify-between gap-2.5 rounded-xl px-3 py-2 text-left text-xs transition",
                      isSelected
                        ? "bg-primary/15 text-primary font-medium"
                        : "hover:bg-muted/80 text-foreground",
                      isOpening && "opacity-70 cursor-wait",
                    )}
                  >
                    <div className="flex items-start gap-2 min-w-0 flex-1">
                      {isOpening ? (
                        <LoaderCircle className="size-3.5 shrink-0 animate-spin text-primary mt-0.5" />
                      ) : (
                        <MessageCircle className="size-3.5 shrink-0 text-muted-foreground mt-0.5 group-hover:text-foreground" />
                      )}
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-medium leading-snug">{item.title}</p>
                        {item.preview && (
                          <p className="truncate text-[10px] text-muted-foreground mt-0.5 leading-tight font-normal">
                            {item.preview}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0 text-[10px] text-muted-foreground">
                      <span className="whitespace-nowrap">{formatRelativeTime(item.updated_at)}</span>
                      <button
                        type="button"
                        aria-label={`Delete ${item.title}`}
                        onClick={(e) => handleDeleteSaved(e, item.id)}
                        className="opacity-0 group-hover:opacity-100 p-1 hover:text-destructive rounded transition"
                      >
                        <Trash2 className="size-3" />
                      </button>
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </div>

        {/* Sample Threads Section */}
        <div className="pt-2 border-t border-border/50">
          <button
            type="button"
            onClick={() => setSamplesExpanded((v) => !v)}
            className="flex w-full items-center justify-between px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground transition"
          >
            <div className="flex items-center gap-1">
              {samplesExpanded ? <ChevronDown className="size-3" /> : <ChevronRight className="size-3" />}
              <span>Sample Demos ({filteredSamples.length})</span>
            </div>
          </button>

          {samplesExpanded && (
            <div className="mt-1 flex flex-col gap-1">
              {filteredSamples.map((sample) => (
                <button
                  key={sample.id}
                  type="button"
                  onClick={() => {
                    onOpenSample(sample)
                    onClose()
                  }}
                  className={cn(
                    "flex w-full items-center justify-between gap-3 rounded-xl px-3 py-1.5 text-left text-xs transition hover:bg-muted/80 text-foreground",
                    activeHistoryId === sample.id && "bg-primary/10 text-primary font-medium"
                  )}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <FolderGit2 className="size-3 shrink-0 text-muted-foreground" />
                    <span className="truncate">{sample.title}</span>
                  </div>
                  <span className="rounded bg-muted px-1.5 py-0.5 text-[9px] font-medium text-muted-foreground">
                    Demo
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
