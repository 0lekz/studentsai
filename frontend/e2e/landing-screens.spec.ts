import fs from 'node:fs'
import path from 'node:path'
import { expect, test, type Page } from '@playwright/test'
import { DECK_FILENAME, buildFixtureDeck } from './fixture-deck'
import { openSection, signIn } from './helpers'
import { registerVerifiedUser } from './users'

const SCREENS_DIR = path.join(__dirname, '..', 'public', 'screens')

test.use({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: 2, colorScheme: 'light' })

async function capture(page: Page, name: string, options: Parameters<Page['screenshot']>[0] = {}) {
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: path.join(SCREENS_DIR, `${name}.png`), animations: 'disabled', style: 'nextjs-portal { display: none !important; }', ...options })
}

// Refreshes the product screenshots on the landing page. Run with E2E_CAPTURE_LANDING=1 against a fully working backend.
test('captures the landing page screenshots', async ({ page }, testInfo) => {
  test.skip(!process.env.E2E_CAPTURE_LANDING || testInfo.project.name !== 'desktop', 'Set E2E_CAPTURE_LANDING=1 to refresh the landing screenshots')

  await signIn(page, await registerVerifiedUser('landing'))
  await page.getByRole('main').getByRole('link', { name: 'Add course' }).click()
  await page.getByLabel('Name').fill('Cell Biology')
  await page.getByLabel(/Term/).fill('Fall 2026')
  await page.getByRole('button', { name: 'Create course' }).click()
  await expect(page).toHaveURL(/\/materials$/)
  await page.getByTestId('materials-file-input').setInputFiles({ name: DECK_FILENAME, mimeType: 'application/pdf', buffer: fs.readFileSync(buildFixtureDeck('landing')) })
  await page.getByRole('button', { name: 'Extract concepts' }).click()
  await expect(page.getByRole('heading', { name: /concepts? mapped/ })).toBeVisible()

  await page.goto('/today')
  await page.getByRole('link', { name: 'Start session' }).click()
  const session = page.getByRole('dialog', { name: 'Practice session' })
  let capturedFeedback = false
  for (let step = 0; step < 10; step += 1) {
    const question = session.locator('[data-question-kind]')
    await expect(question).toBeVisible()
    const kind = await question.getAttribute('data-question-kind')
    if (kind === 'mcq') {
      await session.getByRole('group', { name: 'Choices' }).getByRole('button').first().click()
    } else {
      await session.getByLabel('Your answer').fill(kind === 'recall' ? 'The cell grows and copies its DNA, then divides into two cells.' : 'interphase')
      await session.getByRole('button', { name: 'Check answer' }).click()
    }
    const feedback = session.getByRole('region', { name: 'Feedback' })
    await expect(feedback).toBeVisible()
    if (kind === 'recall' && !capturedFeedback) {
      await page.waitForTimeout(400)
      await capture(page, 'practice-feedback', { clip: { x: 128, y: 0, width: 1024, height: 800 } })
      capturedFeedback = true
    }
    const next = session.getByRole('button', { name: /Next question|See summary/ })
    const isLast = (await next.textContent())?.includes('See summary')
    await next.click()
    if (isLast) break
  }
  await session.getByRole('button', { name: 'Back to Today' }).click()
  await expect(page.getByRole('list', { name: 'Weakest concepts in Cell Biology' })).toBeVisible()
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByRole('button', { name: 'Open navigation' })).toBeVisible()
  const hero = await page.locator('section[aria-labelledby="hero-title"]').boundingBox()
  const courses = await page.locator('section[aria-labelledby="courses-title"]').boundingBox()
  if (!hero || !courses) throw new Error('Today layout not found')
  await capture(page, 'today', { clip: { x: 0, y: hero.y - 16, width: 390, height: courses.y + courses.height - hero.y + 32 } })
  await page.setViewportSize({ width: 1280, height: 800 })
  const main = await page.getByRole('main').boundingBox()
  if (!main) throw new Error('App layout not found')

  await page.getByRole('link', { name: 'Practice', exact: true }).first().click()
  await openSection(page, 'Ask')
  await page.getByLabel('Your question').fill('What happens during metaphase?')
  await page.getByLabel('Your question').press('Enter')
  await expect(page.getByRole('heading', { name: 'Sources' })).toBeVisible()
  await page.getByLabel('Your question').blur()
  await capture(page, 'ask-answer', { clip: main })

  await openSection(page, 'Map')
  await expect(page.getByRole('group', { name: /^Concept map/ }).locator('[data-concept-id]').first()).toBeVisible()
  await page.mouse.move(0, 0)
  await capture(page, 'concept-map', { clip: main })
})
