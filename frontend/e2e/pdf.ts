function escapePdfText(text: string): string {
  return text.replace(/[\\()]/g, (char) => `\\${char}`)
}

function pageStream(heading: string, lines: string[]): string {
  const body = lines.map((line, index) => `BT /F1 14 Tf 72 ${640 - index * 24} Td (${escapePdfText(line)}) Tj ET`).join('\n')
  return `BT /F1 28 Tf 72 700 Td (${escapePdfText(heading)}) Tj ET\n${body}`
}

export function buildPdf(pages: Array<{ heading: string; lines: string[] }>): Buffer {
  const fontId = 3 + pages.length * 2
  const objects: string[] = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    `<< /Type /Pages /Kids [${pages.map((_, index) => `${3 + index * 2} 0 R`).join(' ')}] /Count ${pages.length} >>`,
  ]
  pages.forEach((page, index) => {
    const contentId = 4 + index * 2
    const stream = pageStream(page.heading, page.lines)
    objects.push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents ${contentId} 0 R /Resources << /Font << /F1 ${fontId} 0 R >> >> >>`)
    objects.push(`<< /Length ${Buffer.byteLength(stream)} >>\nstream\n${stream}\nendstream`)
  })
  objects.push('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')

  let pdf = '%PDF-1.4\n'
  const offsets: number[] = []
  objects.forEach((object, index) => {
    offsets.push(Buffer.byteLength(pdf))
    pdf += `${index + 1} 0 obj\n${object}\nendobj\n`
  })
  const xrefOffset = Buffer.byteLength(pdf)
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`
  pdf += offsets.map((offset) => `${String(offset).padStart(10, '0')} 00000 n \n`).join('')
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF\n`
  return Buffer.from(pdf)
}
