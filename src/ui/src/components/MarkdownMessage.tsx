import { useState, type ReactNode } from 'react'

export function MarkdownMessage({ text }: { text: string }) {
  const blocks = text
    .trim()
    .split(/\n\s*\n/)
    .filter(Boolean)

  return (
    <div className="space-y-2 text-sm leading-7">
      {blocks.map((block, index) => {
        const lines = block
          .split('\n')
          .map((line) => line.trim())
          .filter(Boolean)
        const unordered = lines.every((line) => /^[-*]\s+/.test(line))
        const ordered = lines.every((line) => /^\d+\.\s+/.test(line))

        if (unordered) {
          return (
            <ul key={`ul-${index}`} className="space-y-2 pl-5">
              {lines.map((line, lineIndex) => (
                <li key={`li-${index}-${lineIndex}`} className="list-disc text-slate-100">
                  {renderInlineMarkdown(line.replace(/^[-*]\s+/, ''))}
                </li>
              ))}
            </ul>
          )
        }

        if (ordered) {
          return (
            <ol key={`ol-${index}`} className="space-y-2 pl-5">
              {lines.map((line, lineIndex) => (
                <li key={`oli-${index}-${lineIndex}`} className="list-decimal text-slate-100">
                  {renderInlineMarkdown(line.replace(/^\d+\.\s+/, ''))}
                </li>
              ))}
            </ol>
          )
        }

        return (
          <p key={`p-${index}`} className="text-slate-100">
            {lines.map((line, lineIndex) => (
              <span key={`line-${index}-${lineIndex}`}>
                {renderInlineMarkdown(line)}
                {lineIndex < lines.length - 1 ? <br /> : null}
              </span>
            ))}
          </p>
        )
      })}
    </div>
  )
}

function renderInlineMarkdown(text: string) {
  // Split by both bold markers (**text**) and markdown links ([text](url))
  const boldAndLinkPattern = /(\*\*.*?\*\*|\[.*?\]\(.*?\))/g
  const parts = text.split(boldAndLinkPattern).filter(Boolean)

  return parts.map((part, index) => {
    // Handle bold text
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return (
        <strong key={`strong-${index}`} className="font-semibold text-white">
          {part.slice(2, -2)}
        </strong>
      )
    }
    // Handle markdown links [text](url)
    if (part.startsWith('[') && part.includes('](')) {
      const linkMatch = part.match(/\[(.*?)\]\((.*?)\)/)
      if (linkMatch) {
        const [, linkText, url] = linkMatch
        if (url === '#scroll-to-top') {
          return <ViewPlanLink key={`link-${index}`} text={linkText} />
        }
        return (
          <a
            key={`link-${index}`}
            onClick={(e) => { e.preventDefault(); window.location.href = url }}
            href={url}
            className="cursor-pointer transition-opacity hover:opacity-80"
            style={{ color: 'var(--color-accent)', textDecoration: 'underline' }}
          >
            {linkText}
          </a>
        )
      }
    }
    return <InlineText key={`text-${index}`}>{part}</InlineText>
  })
}

/** "View itinerary plan →" button that scrolls the right story panel to top with a click animation */
function ViewPlanLink({ text }: { text: string }) {
  const [clicked, setClicked] = useState(false)

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault()

    // Scroll right panel to top
    const storyScroll = document.querySelector('[data-story-scroll]')
    if (storyScroll) {
      storyScroll.scrollTo({ top: 0, behavior: 'smooth' })
    }

    // Trigger click animation
    setClicked(true)
    setTimeout(() => setClicked(false), 600)
  }

  return (
    <a
      onClick={handleClick}
      href="#scroll-to-top"
      className="inline-flex items-center gap-1.5 cursor-pointer transition-all duration-200 hover:opacity-80"
      style={{
        color: 'var(--color-accent)',
        textDecoration: 'none',
        fontWeight: 500,
        transform: clicked ? 'scale(0.96)' : 'scale(1)',
        opacity: clicked ? 0.6 : 1,
        transition: 'transform 0.3s cubic-bezier(0.22,1,0.36,1), opacity 0.3s ease',
      }}
    >
      <span style={{ textDecoration: 'underline', textUnderlineOffset: '3px' }}>{text}</span>
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{
          transform: clicked ? 'translateX(3px)' : 'translateX(0)',
          transition: 'transform 0.3s cubic-bezier(0.22,1,0.36,1)',
        }}
      >
        <path d="M5 12h14" />
        <path d="m12 5 7 7-7 7" />
      </svg>
    </a>
  )
}

function InlineText({ children }: { children: ReactNode }) {
  return <>{children}</>
}
