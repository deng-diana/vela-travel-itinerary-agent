export function ThinkingDots() {
  return (
    <div className="mr-6 flex items-center gap-3 rounded-2xl px-4 py-4"
      style={{ border: '1px solid var(--story-border)', background: 'var(--story-bg)' }}
    >
      <img src="/vela-avatar.svg" alt="Vela" width={24} height={24} style={{ borderRadius: '50%', flexShrink: 0 }} />
      <div className="flex items-center gap-1.5">
        <span className="thinking-dot h-2 w-2 rounded-full" style={{ background: 'var(--story-text-muted)', animationDelay: '0ms' }} />
        <span className="thinking-dot h-2 w-2 rounded-full" style={{ background: 'var(--story-text-muted)', animationDelay: '150ms' }} />
        <span className="thinking-dot h-2 w-2 rounded-full" style={{ background: 'var(--story-text-muted)', animationDelay: '300ms' }} />
      </div>
    </div>
  )
}
