import type { ReactNode } from 'react'

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
        const handleClick = (e: React.MouseEvent) => {
          e.preventDefault()
          if (url === '#scroll-to-top') {
            // Scroll the messages area to top
            const messagesArea = document.querySelector('.messages-area')
            if (messagesArea) {
              messagesArea.scrollTo({ top: 0, behavior: 'smooth' })
            }
          } else {
            window.location.href = url
          }
        }
        return (
          <a
            key={`link-${index}`}
            onClick={handleClick}
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

function InlineText({ children }: { children: ReactNode }) {
  return <>{children}</>
}
