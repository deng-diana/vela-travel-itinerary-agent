import type { ReactNode } from 'react'

export function MarkdownMessage({ text }: { text: string }) {
  const blocks = text
    .trim()
    .split(/\n\s*\n/)
    .filter(Boolean)

  return (
    <div className="space-y-3 text-sm leading-7">
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
  const parts = text.split(/(\*\*.*?\*\*)/g).filter(Boolean)

  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return (
        <strong key={`strong-${index}`} className="font-semibold text-white">
          {part.slice(2, -2)}
        </strong>
      )
    }
    return <InlineText key={`text-${index}`}>{part}</InlineText>
  })
}

function InlineText({ children }: { children: ReactNode }) {
  return <>{children}</>
}
