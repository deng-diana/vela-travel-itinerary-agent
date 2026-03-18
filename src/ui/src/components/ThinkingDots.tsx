export function ThinkingDots() {
  return (
    <div className="mr-6 flex items-center gap-2 rounded-[22px] border border-slate-700 bg-slate-950 px-4 py-4">
      <div className="mb-1 text-[11px] uppercase tracking-[0.24em] text-slate-400">Vela</div>
      <div className="flex items-center gap-1.5 pl-1">
        <span className="thinking-dot h-2 w-2 rounded-full bg-slate-400" style={{ animationDelay: '0ms' }} />
        <span className="thinking-dot h-2 w-2 rounded-full bg-slate-400" style={{ animationDelay: '150ms' }} />
        <span className="thinking-dot h-2 w-2 rounded-full bg-slate-400" style={{ animationDelay: '300ms' }} />
      </div>
    </div>
  )
}
