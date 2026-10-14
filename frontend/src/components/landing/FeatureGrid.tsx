'use client'

import { useState } from 'react'
import { MediaFrame } from './MediaFrame'

interface FeatureItem {
  src: string
  alt: string
  title: string
  description: string
  icon: React.ReactNode
}

interface FeatureGridProps {
  features: FeatureItem[]
}

export function FeatureGrid({ features }: FeatureGridProps) {
  const [selectedFeature, setSelectedFeature] = useState<FeatureItem | null>(null)

  const openModal = (feature: FeatureItem) => {
    setSelectedFeature(feature)
  }

  const closeModal = () => {
    setSelectedFeature(null)
  }

  return (
    <div className="w-full">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-10">
        {features.map((feature, index) => (
          <div
            key={index}
            className="group relative cursor-pointer"
            onClick={() => openModal(feature)}
          >
            {/* Feature Card */}
            <div className="relative bg-white dark:bg-[#141820] rounded-2xl border border-gray-200 dark:border-[#232a36] overflow-hidden shadow-sm hover:shadow-xl transition-all duration-500 ease-out transform hover:-translate-y-2 flex flex-col">
              
              {/* Icon and Title Header */}
              <div className="p-8 pb-6">
                <div className="flex items-center space-x-4 mb-4">
                  <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl flex items-center justify-center text-white">
                    {feature.icon}
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                    {feature.title}
                  </h3>
                </div>
                
                {/* Description */}
                <p className="text-gray-600 dark:text-gray-300 text-base leading-relaxed">
                  {feature.description}
                  {index === 0 && <span className="block h-8"></span>}
                  {index === 1 && <span className="block h-8"></span>}
                </p>
              </div>

              {/* Screenshot - aligned to bottom */}
              <div className="relative overflow-hidden mt-auto">
                <div className="transform transition-transform duration-700 ease-out group-hover:scale-105">
                  <MediaFrame
                    src={feature.src}
                    alt={feature.alt}
                    className="w-full"
                  />
                </div>
                
                {/* Hover Overlay */}
                <div className={`absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 ease-out`}>
                  <div className="absolute bottom-4 left-4 right-4">
                    <div className="bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm rounded-lg p-3">
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        Click to view full size
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Hover Glow Effect */}
              <div className={`absolute inset-0 rounded-2xl bg-gradient-to-r from-orange-500/20 via-transparent to-orange-500/20 opacity-0 group-hover:opacity-100 transition-opacity duration-500 ease-out pointer-events-none`} />
            </div>
          </div>
        ))}
      </div>

      {/* Modal for full-size screenshot */}
      {selectedFeature && (
        <div 
          className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={closeModal}
        >
          <div className="relative max-w-7xl max-h-[90vh] overflow-auto">
            {/* Close button */}
            <button
              onClick={closeModal}
              className="absolute top-4 right-4 z-10 bg-white/90 dark:bg-gray-800/90 hover:bg-white dark:hover:bg-gray-800 text-gray-800 dark:text-white rounded-full p-3 transition-colors duration-200 shadow-lg"
              aria-label="Close modal"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            
            {/* Screenshot */}
            <div className="relative">
              <img
                src={selectedFeature.src}
                alt={selectedFeature.alt}
                className="w-full h-auto max-w-none rounded-lg shadow-2xl"
                style={{ maxHeight: 'none' }}
              />
              
              {/* Feature info overlay */}
              <div className="absolute bottom-4 left-4 right-4">
                <div className="bg-white/95 dark:bg-gray-800/95 backdrop-blur-sm rounded-lg p-4 shadow-lg">
                  <div className="flex items-center space-x-3 mb-2">
                    <div className="w-8 h-8 bg-gradient-to-br from-orange-500 to-orange-600 rounded-lg flex items-center justify-center text-white">
                      {selectedFeature.icon}
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                      {selectedFeature.title}
                    </h3>
                  </div>
                  <p className="text-gray-600 dark:text-gray-300 text-sm">
                    {selectedFeature.description}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
