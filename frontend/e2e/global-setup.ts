import fs from 'node:fs'
import path from 'node:path'
import { CREDENTIALS_FILE, type E2ECredentials } from './env'
import { registerVerifiedUser } from './users'

export default async function globalSetup() {
  const credentials: E2ECredentials =
    process.env.E2E_EMAIL && process.env.E2E_PASSWORD
      ? { email: process.env.E2E_EMAIL, password: process.env.E2E_PASSWORD }
      : await registerVerifiedUser()
  fs.mkdirSync(path.dirname(CREDENTIALS_FILE), { recursive: true })
  fs.writeFileSync(CREDENTIALS_FILE, JSON.stringify(credentials))
}
