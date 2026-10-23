import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { API_URL, type E2ECredentials } from './env'

const BACKEND_ENV_FILE = path.join(__dirname, '..', '..', 'backend', '.env')

function databaseUrl(): string {
  if (process.env.E2E_DATABASE_URL) return process.env.E2E_DATABASE_URL
  const line = fs.readFileSync(BACKEND_ENV_FILE, 'utf8').split('\n').find((entry) => entry.startsWith('DATABASE_URL='))
  if (!line) throw new Error(`DATABASE_URL not found in ${BACKEND_ENV_FILE}; set E2E_DATABASE_URL`)
  return line.slice('DATABASE_URL='.length).trim()
}

export async function registerVerifiedUser(label: string = 'e2e'): Promise<E2ECredentials> {
  const stamp = `${Date.now()}${Math.floor(Math.random() * 1000)}`
  const credentials = { email: `${label}-${stamp}@example.com`, password: 'E2e-pass-1234' }
  const response = await fetch(`${API_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...credentials, username: `${label}${stamp}`.replace(/[^a-z0-9]/gi, '').slice(0, 30) }),
  })
  if (!response.ok) throw new Error(`Registering the e2e user failed: ${response.status} ${await response.text()}`)

  // Login requires a verified email, and the local SendGrid key cannot deliver the verification link.
  execFileSync('psql', [databaseUrl(), '-v', `email=${credentials.email}`, '-v', 'ON_ERROR_STOP=1'], {
    input: "update users set verified = true where email = :'email';",
  })
  return credentials
}
