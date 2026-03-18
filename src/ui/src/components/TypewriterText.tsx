import { useEffect, useState } from 'react'

export function TypewriterText({ text, animate }: { text: string; animate: boolean }) {
  const [visibleText, setVisibleText] = useState(text)

  useEffect(() => {
    if (!animate) return

    let index = 0
    let timer: number | null = null
    const raf = window.requestAnimationFrame(() => {
      setVisibleText('')
      timer = window.setInterval(() => {
        index += 2
        setVisibleText(text.slice(0, index))
        if (index >= text.length && timer) {
          window.clearInterval(timer)
          timer = null
        }
      }, 12)
    })

    return () => {
      window.cancelAnimationFrame(raf)
      if (timer) window.clearInterval(timer)
    }
  }, [text, animate])

  const displayText = animate ? visibleText : text
  return <span className={`whitespace-pre-line ${animate ? 'agent-shimmer-text' : ''}`}>{displayText}</span>
}
