export function ThinkingDots() {
  return (
    <div className="mr-6 flex items-center gap-3 rounded-2xl px-4 py-3"
      style={{ border: '1px solid var(--story-border)', background: 'var(--story-bg)' }}
    >
      <img src="/vela-avatar.svg" alt="Vela" width={24} height={24} style={{ borderRadius: '50%', flexShrink: 0 }} />
      <div className="flex items-center gap-1">
        <span className="thinking-dot h-1.5 w-1.5 rounded-full" style={{ background: 'var(--color-accent)', animationDelay: '0ms' }} />
        <span className="thinking-dot h-1.5 w-1.5 rounded-full" style={{ background: 'var(--color-accent)', animationDelay: '120ms' }} />
        <span className="thinking-dot h-1.5 w-1.5 rounded-full" style={{ background: 'var(--color-accent)', animationDelay: '240ms' }} />
      </div>
    </div>
  )
}
