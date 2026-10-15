import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { API_URL, CREDENTIALS_FILE, type E2ECredentials } from './env'

const BACKEND_ENV_FILE = path.join(__dirname, '..', '..', 'backend', '.env')

function databaseUrl(): string {
  if (process.env.E2E_DATABASE_URL) return process.env.E2E_DATABASE_URL
  const line = fs.readFileSync(BACKEND_ENV_FILE, 'utf8').split('\n').find((entry) => entry.startsWith('DATABASE_URL='))
  if (!line) throw new Error(`DATABASE_URL not found in ${BACKEND_ENV_FILE}; set E2E_DATABASE_URL`)
  return line.slice('DATABASE_URL='.length).trim()
}

async function registerUser(): Promise<E2ECredentials> {
  const stamp = Date.now()
  const credentials = { email: `e2e-${stamp}@example.com`, password: 'E2e-pass-1234' }
  const response = await fetch(`${API_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...credentials, username: `e2e${stamp}` }),
  })
  if (!response.ok) throw new Error(`Registering the e2e user failed: ${response.status} ${await response.text()}`)

  // Login requires a verified email, and the local SendGrid key cannot deliver the verification link.
  execFileSync('psql', [databaseUrl(), '-v', `email=${credentials.email}`, '-v', 'ON_ERROR_STOP=1'], {
    input: "update users set verified = true where email = :'email';",
  })
  return credentials
}

export default async function globalSetup() {
  const credentials: E2ECredentials =
    process.env.E2E_EMAIL && process.env.E2E_PASSWORD
      ? { email: process.env.E2E_EMAIL, password: process.env.E2E_PASSWORD }
      : await registerUser()
  fs.mkdirSync(path.dirname(CREDENTIALS_FILE), { recursive: true })
  fs.writeFileSync(CREDENTIALS_FILE, JSON.stringify(credentials))
}
