'use client'

import { useState } from 'react'

export function PricingCTA() {
  const [isAnnual, setIsAnnual] = useState(false)
  const [showProNote, setShowProNote] = useState(false)

  const plans = [
    {
      name: 'Free',
      price: '$0',
      period: 'forever',
      description: 'Perfect for getting started with AI-powered studying',
      features: [
        'Create unlimited notes',
        'Generate up to 50 flashcards per month',
        'Basic spaced repetition',
        'AI summary generation (5 per month)',
        'Community support'
      ],
      cta: 'Get Started Free',
      popular: false,
      color: 'from-gray-500 to-gray-600'
    },
    {
      name: 'Pro',
      price: isAnnual ? '$4' : '$5',
      period: isAnnual ? 'per month' : 'per month',
      description: 'Unlock the full potential of AI-powered learning',
      features: [
        'Everything in Free',
        'Unlimited flashcard generation',
        'Advanced spaced repetition algorithms',
        'Unlimited AI summaries',
        'Knowledge graph visualization',
        'Progress analytics & insights',
        'Priority support',
        'Export to multiple formats'
      ],
      cta: 'Coming Soon',
      popular: true,
      color: 'from-orange-500 to-orange-600'
    }
  ]

  const handleProClick = () => {
    setShowProNote(true)
  }

  return (
    <div className="w-full">
      {/* Header */}
      <div className="text-center mb-16">
        <h2 className="text-5xl font-semibold text-gray-900 dark:text-white mb-6">
          Start Learning Smarter Today
        </h2>
        <p className="text-xl text-gray-600 dark:text-gray-300 max-w-3xl mx-auto mb-8">
          Join thousands of students who are already using AI to accelerate their learning
        </p>
        
        {/* Billing Toggle */}
        <div className="flex items-center justify-center space-x-4">
          <span className={`text-sm ${!isAnnual ? 'text-gray-900 dark:text-white' : 'text-gray-500'}`}>
            Monthly
          </span>
          <button
            onClick={() => setIsAnnual(!isAnnual)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              isAnnual ? 'bg-orange-500' : 'bg-gray-300'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                isAnnual ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
          <span className={`text-sm ${isAnnual ? 'text-gray-900 dark:text-white' : 'text-gray-500'}`}>
            Annual
            <span className="ml-1 text-orange-500 font-medium">Save 20%</span>
          </span>
        </div>
      </div>

      {/* Pricing Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-5xl mx-auto mb-16">
        {plans.map((plan) => (
          <div
            key={plan.name}
            className={`relative bg-white dark:bg-[#141820] rounded-3xl border-2 transition-all duration-300 hover:scale-105 ${
              plan.popular 
                ? 'border-orange-500 shadow-2xl shadow-orange-500/20' 
                : 'border-gray-200 dark:border-[#232a36] shadow-xl'
            } overflow-hidden`}
          >
            {/* Popular Badge */}
            {plan.popular && (
              <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                <div className="bg-orange-500 text-white px-4 py-2 rounded-full text-sm font-medium">
                  Most Popular
                </div>
              </div>
            )}

            <div className="p-8 flex flex-col h-full">
              {/* Plan Header */}
              <div className="text-center mb-8">
                <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                  {plan.name}
                </h3>
                <div className="mb-2">
                  <span className="text-4xl font-bold text-gray-900 dark:text-white">
                    {plan.price}
                  </span>
                  <span className="text-gray-500 dark:text-gray-400 ml-2">
                    {plan.period}
                  </span>
                </div>
                <p className="text-gray-600 dark:text-gray-300">
                  {plan.description}
                </p>
              </div>

              {/* Features */}
              <ul className="space-y-4 mb-8 flex-1">
                {plan.features.map((feature, index) => (
                  <li key={index} className="flex items-start gap-3">
                    <div className={`w-5 h-5 rounded-full bg-gradient-to-br ${plan.color} flex items-center justify-center flex-shrink-0 mt-0.5`}>
                      <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                    <span className="text-gray-700 dark:text-gray-300">{feature}</span>
                  </li>
                ))}
              </ul>

              {/* CTA Button */}
              <button 
                className={`w-full py-4 px-6 rounded-xl font-semibold text-white transition-all duration-300 ${
                  plan.popular
                    ? 'bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 shadow-lg hover:shadow-xl'
                    : 'bg-gradient-to-r from-gray-500 to-gray-600 hover:from-gray-600 hover:to-gray-700'
                }`}
                onClick={plan.popular ? handleProClick : () => window.location.href = '/auth'}
              >
                {plan.cta}
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Pro Plan Note Modal */}
      {showProNote && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-[#141820] rounded-2xl p-8 max-w-2xl mx-auto shadow-2xl">
            <div className="text-center mb-6">
              <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                🚧 Pro Plan Coming Soon!
              </h3>
              <p className="text-gray-600 dark:text-gray-300">
                We&apos;re working hard to bring you the best features
              </p>
            </div>
            
            <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-xl p-6 mb-6">
              <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed">
                <strong>Not trying to scam anyone</strong> - the app is in early stages, so the pro tier is not available now. Check it out later to get all the best features, like early access to the mobile app, extended API calls, etc.
              </p>
            </div>

            <div className="text-center">
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                If you wish to support the project and bring the development to the next level, you can buy me coffee here:
              </p>
              <a 
                href="https://buymeacoffee.com/oleksiizh" 
                target="_blank" 
                rel="noopener noreferrer"
                className="inline-block bg-orange-500 hover:bg-orange-600 text-white px-6 py-3 rounded-xl font-semibold transition-colors duration-300"
              >
                ☕ Buy Me a Coffee
              </a>
            </div>

            <button
              onClick={() => setShowProNote(false)}
              className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Bottom CTA - More Subtle */}
      <div className="text-center">
        <div className="bg-gray-50 dark:bg-[#0f1115] border border-gray-200 dark:border-[#232a36] rounded-2xl p-8 md:p-12">
          <h3 className="text-2xl font-semibold text-gray-900 dark:text-white mb-3">
            Ready to get started?
          </h3>
          <p className="text-gray-600 dark:text-gray-300 mb-6 max-w-2xl mx-auto">
            Be the first to explore and support the project, together we can do something great!
          </p>
          <button 
            className="bg-orange-500 hover:bg-orange-600 text-white px-8 py-3 rounded-xl font-semibold transition-colors duration-300"
            onClick={() => window.location.href = '/auth'}
          >
            Join Completely Free
          </button>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-4">
            No credit card required • Early access to new features • Help shape the future
          </p>
        </div>
      </div>
    </div>
  )
}
