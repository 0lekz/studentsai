const escapeRegExp = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

// Locates the excerpt in the section text even when bullets, line breaks or spacing differ.
export function highlightExcerpt(text: string, excerpt: string): [string, string, string] | null {
  const words = excerpt.trim().split(/\s+/).filter(Boolean)
  if (words.length === 0) return null
  const pattern = new RegExp(words.map(escapeRegExp).join('[\\s\\-•*]+'), 'i')
  const match = pattern.exec(text)
  if (!match) return null
  return [text.slice(0, match.index), match[0], text.slice(match.index + match[0].length)]
}
