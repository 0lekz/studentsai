export interface PasswordStrength {
  score: number
  feedback: string
  meetsRequirements: boolean
}

const COMMON_PASSWORDS = ['password', '123456', 'qwerty', 'admin', 'letmein']
export const MAX_PASSWORD_SCORE = 6

export function evaluatePasswordStrength(password: string): PasswordStrength {
  if (!password) return { score: 0, feedback: '', meetsRequirements: false }

  const checks: Array<[boolean, string]> = [
    [password.length >= 8, 'At least 8 characters'],
    [/[a-z]/.test(password), 'Include lowercase letters'],
    [/[A-Z]/.test(password), 'Include uppercase letters'],
    [/[0-9]/.test(password), 'Include numbers'],
    [/[^A-Za-z0-9]/.test(password), 'Include special characters'],
    [!COMMON_PASSWORDS.includes(password.toLowerCase()), 'Avoid common passwords'],
  ]
  const score = checks.filter(([passed]) => passed).length
  const feedback = checks.filter(([passed]) => !passed).map(([, hint]) => hint)

  return {
    score,
    feedback: feedback.join(', '),
    meetsRequirements: score >= 4 && password.length >= 8,
  }
}

export function strengthLabel(score: number): string {
  if (score <= 2) return 'Weak'
  if (score <= 3) return 'Fair'
  if (score <= 4) return 'Good'
  return 'Strong'
}
