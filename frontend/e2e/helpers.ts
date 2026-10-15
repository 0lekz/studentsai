import path from 'node:path'
import { expect, type Page } from '@playwright/test'
import { SCREENSHOT_DIR, type E2ECredentials } from './env'

export async function screenshot(page: Page, project: string, name: string, { settle = true }: { settle?: boolean } = {}) {
  if (settle) await page.waitForLoadState('networkidle')
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, project, `${name}.png`),
    animations: 'disabled',
    style: 'nextjs-portal { display: none !important; }',
  })
}

export function isPhone(page: Page): boolean {
  return (page.viewportSize()?.width ?? 0) < 768
}

export async function signIn(page: Page, { email, password }: E2ECredentials) {
  await page.goto('/auth', { waitUntil: 'networkidle' })
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign In' }).click()
  await expect(page).toHaveURL(/\/today$/)
}

export async function openSection(page: Page, section: 'Materials' | 'Practice' | 'Ask' | 'Map' | 'Notes') {
  const nav = page.getByRole('navigation', { name: 'Course sections' }).filter({ visible: true })
  await nav.getByRole('link', { name: section }).click()
  await expect(page).toHaveURL(new RegExp(`/courses/[^/]+/${section.toLowerCase()}`))
}

export function collectPageErrors(page: Page): string[] {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(`${page.url()}: ${error.message}\n${error.stack ?? ''}`))
  return errors
}
