import path from 'node:path'

export const API_URL = process.env.E2E_API_URL ?? 'http://localhost:8000'
export const CREDENTIALS_FILE = path.join(__dirname, '.auth', 'user.json')
export const SCREENSHOT_DIR = path.join(__dirname, 'screenshots')

export interface E2ECredentials {
  email: string
  password: string
}
