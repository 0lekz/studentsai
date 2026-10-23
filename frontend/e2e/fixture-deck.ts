import { execFileSync } from 'node:child_process'
import os from 'node:os'
import path from 'node:path'

const BACKEND_DIR = path.join(__dirname, '..', '..', 'backend')
const PYTHON = process.env.E2E_PYTHON ?? path.join(BACKEND_DIR, 'venv', 'bin', 'python')

export const DECK_FILENAME = 'lecture-03-cell-division.pdf'

export const DECK_SLIDES = [
  {
    title: 'The cell cycle',
    bullets: [
      'The cell cycle is the ordered series of events in which a cell grows, copies its DNA and divides into two daughter cells.',
      'Interphase covers the G1, S and G2 phases, and the cell copies its DNA during the S phase.',
      'The mitotic phase follows interphase and ends with cytokinesis.',
    ],
  },
  {
    title: 'Mitosis',
    bullets: [
      'Mitosis divides one nucleus into two genetically identical nuclei.',
      'Its stages are prophase, metaphase, anaphase and telophase.',
      'During metaphase the chromosomes line up along the metaphase plate before the sister chromatids separate.',
    ],
  },
  {
    title: 'Meiosis',
    bullets: [
      'Meiosis produces four haploid gametes from one diploid cell.',
      'It halves the chromosome number through two rounds of division, meiosis I and meiosis II.',
      'Meiosis creates genetic variation through crossing over and independent assortment.',
    ],
  },
  {
    title: 'Crossing over',
    bullets: [
      'Crossing over exchanges segments between homologous chromosomes during prophase I.',
      'The exchange happens at chiasmata, where non-sister chromatids touch.',
      'Crossing over produces recombinant chromosomes with new combinations of alleles.',
    ],
  },
  {
    title: 'Cell cycle checkpoints',
    bullets: [
      'Checkpoints stop the cell cycle when something has gone wrong.',
      'The G1 checkpoint checks cell size, nutrients and DNA damage before the cell commits to S phase.',
      'The spindle checkpoint holds anaphase until every chromosome is attached to the spindle.',
    ],
  },
  {
    title: 'Apoptosis',
    bullets: [
      'Apoptosis is programmed cell death that removes damaged or unneeded cells.',
      'Caspase enzymes dismantle the cell from the inside in an orderly way.',
      'When checkpoints fail and apoptosis does not happen, damaged cells can divide without control and form tumors.',
    ],
  },
]

const BUILD_DECK = `
import json, sys
from tests.fixtures.pdfs import Slide, slide_deck
slides = [Slide(title=slide["title"], bullets=tuple(slide["bullets"])) for slide in json.load(sys.stdin)]
with open(sys.argv[1], "wb") as target:
    target.write(slide_deck(slides, footer="BIO 110 - Lecture 3"))
`

// Builds the deck with the backend's own test fixture helper, so the e2e input matches what the ingestion tests use.
export function buildFixtureDeck(name: string): string {
  const target = path.join(os.tmpdir(), `studentsai-e2e-${name}-${process.pid}.pdf`)
  execFileSync(PYTHON, ['-c', BUILD_DECK, target], { cwd: BACKEND_DIR, input: JSON.stringify(DECK_SLIDES) })
  return target
}
