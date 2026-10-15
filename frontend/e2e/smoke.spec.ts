import fs from 'node:fs'
import path from 'node:path'
import { expect, test, type Page } from '@playwright/test'
import { CREDENTIALS_FILE, SCREENSHOT_DIR, type E2ECredentials } from './env'
import { buildPdf } from './pdf'

const SECTIONS = ['Materials', 'Practice', 'Ask', 'Map', 'Notes'] as const

function credentials(): E2ECredentials {
  return JSON.parse(fs.readFileSync(CREDENTIALS_FILE, 'utf8'))
}

async function screenshot(page: Page, project: string, name: string) {
  await page.waitForLoadState('networkidle')
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, project, `${name}.png`),
    animations: 'disabled',
    style: 'nextjs-portal { display: none !important; }',
  })
}

function isPhone(page: Page): boolean {
  return (page.viewportSize()?.width ?? 0) < 768
}

async function writeNote(page: Page, title: string, body: string) {
  const newNote = page.getByRole('button', { name: 'New note' })
  if (await page.getByRole('button', { name: 'Back to notes' }).isVisible()) {
    await page.getByRole('button', { name: 'Back to notes' }).click()
  }
  await newNote.first().click()
  await page.getByLabel('Note title').fill(title)
  await page.locator('.ProseMirror').click()
  await page.keyboard.type(body, { delay: 10 })
  await page.getByRole('button', { name: 'Create note' }).click()
  await expect(page).toHaveURL(/\?note=/)
  await expect(page.getByText(/^Saved/).first()).toBeVisible()
}

async function openSection(page: Page, section: (typeof SECTIONS)[number]) {
  const nav = page.getByRole('navigation', { name: 'Course sections' }).filter({ visible: true })
  await nav.getByRole('link', { name: section }).click()
  await expect(page).toHaveURL(new RegExp(`/courses/[^/]+/${section.toLowerCase()}`))
}

test('signs in, creates a course and opens every section', async ({ page }, testInfo) => {
  const project = testInfo.project.name
  const pageErrors: string[] = []
  page.on('pageerror', (error) => pageErrors.push(`${page.url()}: ${error.message}\n${error.stack ?? ''}`))

  const { email, password } = credentials()
  await page.goto('/auth', { waitUntil: 'networkidle' })
  await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible()
  await screenshot(page, project, '00-sign-in')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign In' }).click()
  await expect(page).toHaveURL(/\/today$/)
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  await screenshot(page, project, '01-today')

  if (isPhone(page)) {
    await page.getByRole('button', { name: 'Open navigation' }).click()
    const drawer = page.getByRole('dialog', { name: 'Navigation' })
    await expect(drawer).toBeVisible()
    await screenshot(page, project, '02-navigation-drawer')
    await drawer.getByRole('link', { name: 'Add course' }).click()
  } else {
    await page.getByRole('complementary').getByRole('link', { name: 'Add course' }).click()
  }
  await expect(page).toHaveURL(/\/courses\/new$/)
  const courseName = `Cell Biology ${project}`
  await page.getByLabel('Name').fill(courseName)
  await page.getByLabel(/Term/).fill('Fall 2026')
  await page.getByLabel(/Exam date/).fill('2026-11-02')
  await screenshot(page, project, '03-new-course')
  await page.getByRole('button', { name: 'Create course' }).click()

  await expect(page).toHaveURL(/\/courses\/[^/]+\/materials$/)
  await expect(page.getByRole('heading', { name: courseName })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Bring the course in' })).toBeVisible()
  await screenshot(page, project, '04-materials-empty')

  await page.getByTestId('materials-file-input').setInputFiles({
    name: 'lecture-01-cell-division.pdf',
    mimeType: 'application/pdf',
    buffer: buildPdf([
      { heading: 'Cell division', lines: ['Mitosis produces two identical daughter cells.', 'Prophase, metaphase, anaphase, telophase.'] },
      { heading: 'Meiosis', lines: ['Meiosis halves the chromosome number.', 'Crossing over happens in prophase I.'] },
      { heading: 'Checkpoints', lines: ['The G1 checkpoint controls entry into S phase.'] },
    ]),
  })
  await expect(page.getByText('lecture-01-cell-division.pdf')).toBeVisible()
  await expect(page.getByText(/3 pages/)).toBeVisible()
  await screenshot(page, project, '05-materials')

  await openSection(page, 'Practice')
  await expect(page.getByRole('heading', { name: 'Practice from your slides' })).toBeVisible()
  await screenshot(page, project, '06-practice')

  await openSection(page, 'Ask')
  await expect(page.getByRole('heading', { name: `Ask ${courseName}` })).toBeVisible()
  await screenshot(page, project, '07-ask')

  await openSection(page, 'Notes')
  await expect(page.getByText('No notes yet')).toBeVisible()
  await writeNote(page, 'Meiosis', 'Meiosis halves the chromosome number. Crossing over happens in prophase I.')
  await writeNote(page, 'Mitosis', 'Mitosis splits one cell into two identical cells. Compare with [[Meiosis]].')
  await page.getByRole('button', { name: 'Save', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Save', exact: true })).toBeEnabled()
  await expect(page.getByText(/^Saved/).first()).toBeVisible()
  await screenshot(page, project, '08-notes-editor')
  if (isPhone(page)) {
    await page.getByRole('button', { name: 'Back to notes' }).click()
    await expect(page.getByRole('listitem').filter({ hasText: 'Mitosis' })).toBeVisible()
    await screenshot(page, project, '09-notes-list')
  }

  await openSection(page, 'Map')
  await expect(page.getByText(/2 notes · 1 link/)).toBeVisible()
  await expect(page.getByRole('img', { name: /notes connect/ }).locator('circle')).toHaveCount(2)
  await page.waitForTimeout(1500)
  await screenshot(page, project, '10-map')

  await page.goto('/settings')
  await expect(page.getByRole('heading', { name: 'Settings', level: 1 })).toBeVisible()
  await screenshot(page, project, '11-settings')

  await page.goto('/today')
  await expect(page.getByRole('link', { name: new RegExp(courseName) }).first()).toBeVisible()
  await screenshot(page, project, '12-today-with-course')

  expect(pageErrors, `uncaught page errors: ${pageErrors.join('\n')}`).toEqual([])
})
