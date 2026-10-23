'use client'

import { Heart, Github, ExternalLink, Linkedin, Coffee, User } from 'lucide-react'

export function SiteFooter() {
  return (
    <footer className="bg-gray-50 border-t mt-16 dark:bg-gray-950 dark:border-gray-800">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="grid gap-8 md:grid-cols-4">
          {/* Project Info */}
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <h3 className="font-semibold text-gray-900 dark:text-gray-100">StudentsAI</h3>
            </div>
            <p className="text-sm text-gray-600 leading-relaxed dark:text-gray-400">
              A tutor that has read your course. Bring your slides, practice with feedback that cites them, and see what to study next.
            </p>
            <div className="flex items-center space-x-1 text-sm text-gray-600 dark:text-gray-400">
              <span>Early access, open source</span>
            </div>
          </div>

          {/* Features */}
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-900 dark:text-gray-100">Features</h3>
            <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
              <li className="flex items-center space-x-2">
                <div className="w-1 h-1 bg-orange-600 rounded-full" />
                <span>Practice with graded feedback</span>
              </li>
              <li className="flex items-center space-x-2">
                <div className="w-1 h-1 bg-orange-600 rounded-full" />
                <span>Answers that cite your slides</span>
              </li>
              <li className="flex items-center space-x-2">
                <div className="w-1 h-1 bg-orange-600 rounded-full" />
                <span>Concept map with mastery</span>
              </li>
              <li className="flex items-center space-x-2">
                <div className="w-1 h-1 bg-orange-600 rounded-full" />
                <span>Spaced repetition across courses</span>
              </li>
            </ul>
          </div>

          {/* Tech Stack */}
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-900 dark:text-gray-100">Built With</h3>
            <div className="grid grid-cols-2 gap-2 text-sm text-gray-600 dark:text-gray-400">
              <div className="space-y-1">
                <div>React 19</div>
                <div>Tailwind CSS</div>
                <div>shadcn/ui</div>
                <div>Next.js</div>
              </div>
              <div className="space-y-1">
                <div>FastAPI</div>
                <div>Python</div>
                <div>PostgreSQL</div>
              </div>
            </div>
            <div className="flex space-x-3 pt-2">
              <a
                href="https://github.com/0lekz/studentsai"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center space-x-1 text-sm text-gray-600 hover:text-orange-600 dark:text-gray-400 dark:hover:text-orange-400 transition-colors"
              >
                <Github className="w-4 h-4" />
                <span>Source Code</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>

          {/* Author */}
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <User className="w-5 h-5 text-orange-600" />
              <h3 className="font-semibold text-gray-900 dark:text-gray-100">Author</h3>
            </div>
            <div className="space-y-3">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Created by <span className="font-medium text-gray-900 dark:text-gray-100">Oleksii Zhukov</span>
              </p>
              <p className="text-xs text-gray-600 leading-relaxed dark:text-gray-400">
                This project is open source and I’m paying for API calls and hosting from my own pocket. Your support helps keep this tool free for students!
              </p>
              <div className="flex flex-col space-y-2">
                <a
                  href="https://github.com/0lekz"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center space-x-2 text-sm text-gray-600 hover:text-orange-600 dark:text-gray-400 dark:hover:text-orange-400 transition-colors"
                >
                  <Github className="w-4 h-4" />
                  <span>GitHub</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
                <a
                  href="https://www.linkedin.com/in/oleksiizhukov/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center space-x-2 text-sm text-gray-600 hover:text-orange-600 dark:text-gray-400 dark:hover:text-orange-400 transition-colors"
                >
                  <Linkedin className="w-4 h-4" />
                  <span>LinkedIn</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
                <a
                  href="https://buymeacoffee.com/oleksiizh"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center space-x-2 text-sm bg-orange-50 text-orange-700 hover:bg-orange-100 dark:bg-orange-950/40 dark:text-orange-300 dark:hover:bg-orange-950/60 transition-colors px-3 py-2 rounded-lg border border-orange-200 dark:border-orange-900/40"
                >
                  <Coffee className="w-4 h-4" />
                  <span>Buy me a coffee</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Section */}
        <div className="border-t border-gray-200 dark:border-gray-800 mt-8 pt-6 flex flex-col md:flex-row items-center justify-between space-y-4 md:space-y-0">
          <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
            <span>Built with</span>
            <Heart className="w-4 h-4 text-red-500 fill-current" />
            <span>for students everywhere by Oleksii Zhukov</span>
          </div>
          <div className="flex items-center space-x-4 text-xs text-gray-600 dark:text-gray-400">
            <span>© {new Date().getFullYear()} StudentsAI</span>
          </div>
        </div>
      </div>
    </footer>
  )
}


