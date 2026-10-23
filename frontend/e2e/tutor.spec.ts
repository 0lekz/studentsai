import fs from 'node:fs'
import { expect, test, type Locator, type Page } from '@playwright/test'
import { DECK_FILENAME, DECK_SLIDES, buildFixtureDeck } from './fixture-deck'
import { collectPageErrors, openSection, screenshot, signIn } from './helpers'
import { registerVerifiedUser } from './users'

type Kind = 'mcq' | 'short_answer' | 'recall'

async function closeSheet(page: Page) {
  await page.getByRole('dialog').last().getByRole('button', { name: 'Close' }).click()
}

async function nextQuestion(session: Locator) {
  await session.getByRole('button', { name: /Next question|See summary/ }).click()
}

test('a new student goes from slides to a practice session, an answer with citations, and the concept map', async ({ page }, testInfo) => {
  const project = testInfo.project.name
  const pageErrors = collectPageErrors(page)

  await signIn(page, await registerVerifiedUser(`tutor${project.replace(/-/g, '')}`))
  await expect(page.getByRole('heading', { name: 'Start with a course' })).toBeVisible()
  await screenshot(page, project, '20-today-onboarding')

  await page.getByRole('main').getByRole('link', { name: 'Add course' }).click()
  await page.getByLabel('Name').fill('Cell Biology')
  await page.getByLabel(/Term/).fill('Fall 2026')
  await page.getByLabel(/Exam date/).fill('2026-11-02')
  await page.getByRole('button', { name: 'Create course' }).click()
  await expect(page).toHaveURL(/\/courses\/[^/]+\/materials$/)
  const coursePath = new URL(page.url()).pathname.replace(/\/materials$/, '')

  await page.getByTestId('materials-file-input').setInputFiles({
    name: DECK_FILENAME,
    mimeType: 'application/pdf',
    buffer: fs.readFileSync(buildFixtureDeck(project)),
  })
  await expect(page.getByText(DECK_FILENAME)).toBeVisible()
  await expect(page.getByText(new RegExp(`${DECK_SLIDES.length} (slides|pages)`))).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Turn these files into concepts' })).toBeVisible()
  await screenshot(page, project, '21-materials-ready-to-extract')

  await page.getByRole('button', { name: 'Extract concepts' }).click()
  await expect(page.getByRole('progressbar', { name: 'Extracting concepts' })).toBeVisible()
  await screenshot(page, project, '22-materials-extracting', { settle: false })
  await expect(page.getByRole('heading', { name: /\d+ concepts? mapped/ })).toBeVisible()
  await expect(page.getByText(/^Found \d+ concepts?/)).toBeVisible()
  await screenshot(page, project, '23-materials-extracted')

  await page.goto('/today')
  await expect(page.getByRole('heading', { name: /Ready for today.s session|questions? due today/ })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Cell Biology', exact: true }).last()).toBeVisible()
  await screenshot(page, project, '24-today')

  await page.getByRole('link', { name: 'Start session' }).click()
  const session = page.getByRole('dialog', { name: 'Practice session' })
  const emptySession = page.getByText(/^No questions could be written/)
  await expect(session.locator('[data-question-kind]').or(emptySession)).toBeVisible({ timeout: 90_000 })
  if (await emptySession.isVisible()) {
    // The backend wrote no questions, which is what its fake LLM provider does; the practice steps need a real provider.
    testInfo.annotations.push({ type: 'limited', description: 'Practice session came back empty; answering steps not exercised' })
    await screenshot(page, project, '25-practice-empty-session')
  } else {
    await practiceOneOfEachKind(page, project)
  }

  await page.goto(`${coursePath}/practice`)
  await expect(page.getByRole('heading', { name: 'Practice session' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Needs the most work' })).toBeVisible()
  await screenshot(page, project, '33-practice-start')

  await askTheCourse(page, project, testInfo.annotations)
  await checkTheMap(page, project)

  expect(pageErrors, `uncaught page errors: ${pageErrors.join('\n')}`).toEqual([])
})

async function practiceOneOfEachKind(page: Page, project: string) {
  const session = page.getByRole('dialog', { name: 'Practice session' })

  const graded = new Set<Kind>()
  let selfGraded = false
  for (let step = 0; step < 12 && !(graded.size === 3 && selfGraded); step += 1) {
    const question = session.locator('[data-question-kind]')
    await expect(question).toBeVisible()
    const kind = (await question.getAttribute('data-question-kind')) as Kind
    const feedback = session.getByRole('region', { name: 'Feedback' })

    const firstOfKind = !graded.has(kind)
    if (kind === 'recall' && !firstOfKind && !selfGraded) {
      await session.getByRole('button', { name: 'Show answer' }).click()
      await expect(session.getByRole('group', { name: 'Grade your recall' })).toBeVisible()
      await screenshot(page, project, '29-practice-recall-show-answer')
      await session.getByRole('group', { name: 'Grade your recall' }).getByRole('button', { name: /Good/ }).click()
      await expect(session.getByText(/^Next review/)).toBeVisible()
      await screenshot(page, project, '29-practice-recall-self-graded')
      selfGraded = true
    } else if (kind === 'mcq') {
      if (firstOfKind) await screenshot(page, project, '25-practice-mcq')
      await session.getByRole('group', { name: 'Choices' }).getByRole('button').first().click()
      await expect(feedback).toBeVisible()
      if (firstOfKind) await screenshot(page, project, '26-practice-mcq-feedback')
    } else {
      await session.getByLabel('Your answer').fill(kind === 'recall' ? 'The cell grows and then divides into two cells.' : 'chromosomes')
      if (firstOfKind && kind === 'short_answer') await screenshot(page, project, '27-practice-short-answer')
      await session.getByRole('button', { name: 'Check answer' }).click()
      await expect(feedback).toBeVisible()
      await expect(feedback.getByText('Reference answer')).toBeVisible()
      if (firstOfKind) await screenshot(page, project, kind === 'recall' ? '28-practice-recall-feedback' : '27-practice-short-answer-feedback')
      if (firstOfKind && kind === 'recall') {
        await feedback.getByRole('button', { name: /^Open source/ }).click()
        await expect(page.getByRole('heading', { name: 'Cited passage' })).toBeVisible()
        await expect(page.getByRole('heading', { name: /On the page: / })).toBeVisible()
        await screenshot(page, project, '30-practice-source')
        await closeSheet(page)
      }
    }
    graded.add(kind)

    if (graded.size === 3 && selfGraded) break
    await nextQuestion(session)
  }
  expect([...graded].sort()).toEqual(['mcq', 'recall', 'short_answer'])

  if (await session.locator('[data-question-kind]').isVisible()) await session.getByRole('button', { name: 'End session' }).click()
  await expect(session.getByRole('heading', { name: /Session (complete|ended)/ })).toBeVisible()
  await screenshot(page, project, '31-practice-summary')
  await session.getByRole('button', { name: 'Back to Today' }).click()
  await expect(page).toHaveURL(/\/today$/)
  await expect(page.getByRole('list', { name: 'Weakest concepts in Cell Biology' })).toBeVisible()
  await screenshot(page, project, '32-today-after-session')
}

async function askTheCourse(page: Page, project: string, annotations: Array<{ type: string; description?: string }>) {
  await openSection(page, 'Ask')
  await expect(page.getByRole('heading', { name: 'Ask Cell Biology' })).toBeVisible()
  await screenshot(page, project, '34-ask-intro')
  await page.getByLabel('Your question').fill('What happens during metaphase?')
  await page.getByLabel('Your question').press('Enter')
  const answer = page.getByRole('article', { name: /What happens during metaphase/ })
  const sources = answer.getByRole('heading', { name: 'Sources' })
  await expect(page.locator('article[data-status="answered"]')).toHaveCount(1, { timeout: 90_000 })
  await screenshot(page, project, '35-ask-answer')
  if (await sources.isVisible()) {
    await answer.getByRole('button', { name: 'Open source 1', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Cited passage' })).toBeVisible()
    await expect(page.getByRole('heading', { name: /On the page: / })).toBeVisible()
    await screenshot(page, project, '36-ask-source')
    await closeSheet(page)
  } else {
    annotations.push({ type: 'limited', description: 'The grounded answer had no citations; the source panel was not exercised from Ask' })
  }
  await page.getByLabel('Your question').fill('Who won the 1998 World Cup?')
  await page.getByRole('button', { name: 'Ask', exact: true }).click()
  await expect(page.getByRole('article', { name: /1998 World Cup/ }).getByText('Not in your materials')).toBeVisible({ timeout: 90_000 })
  await screenshot(page, project, '37-ask-not-covered')
}

async function checkTheMap(page: Page, project: string) {
  await openSection(page, 'Map')
  const map = page.getByRole('group', { name: /^Concept map/ })
  const nodes = map.locator('[data-concept-id]')
  await expect(nodes.first()).toBeVisible()
  const nodeCount = await nodes.count()
  expect(nodeCount).toBeGreaterThan(0)
  const labels = map.locator('[data-concept-id] .concept-label')
  await expect(labels).toHaveCount(nodeCount)
  for (const label of await labels.all()) await expect(label).toHaveCSS('opacity', '1')
  await expect(page.getByRole('heading', { name: 'Study this next' })).toBeVisible()
  await expect(page.getByRole('list', { name: 'Mastery' }).first()).toBeAttached()
  await screenshot(page, project, '38-map')

  await nodes.first().click()
  const panel = page.getByRole('dialog')
  await expect(panel.getByRole('link', { name: 'Practice this concept' })).toBeVisible()
  await screenshot(page, project, '39-map-concept')
  await panel.getByRole('button', { name: 'Rename' }).click()
  await panel.getByLabel('Concept name').fill('Cell cycle overview')
  await panel.getByRole('button', { name: 'Save' }).click()
  await expect(panel.getByRole('heading', { name: 'Cell cycle overview' })).toBeVisible()
  await closeSheet(page)
  await expect(page.getByRole('region', { name: 'All concepts' }).getByText('Cell cycle overview')).toBeVisible()
}

test('the landing page tells the tutor story', async ({ page }, testInfo) => {
  const pageErrors = collectPageErrors(page)
  await page.goto('/landing', { waitUntil: 'networkidle' })
  await expect(page.getByRole('heading', { level: 1 })).toContainText('tutor')
  await expect(page.getByText(/activity|streak|AI summar|Pro plan/i)).toHaveCount(0)
  await page.screenshot({ path: `e2e/screenshots/${testInfo.project.name}/40-landing.png`, fullPage: true, animations: 'disabled' })
  expect(pageErrors).toEqual([])
})
