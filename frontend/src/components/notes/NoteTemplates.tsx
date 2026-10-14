'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { 
  FileText, 
  BookOpen, 
  Lightbulb, 
  Calendar, 
  Target, 
  Users, 
  Zap,
  Plus,
  X,
  Check
} from 'lucide-react'

export interface NoteTemplate {
  id: string
  name: string
  description: string
  icon: React.ReactNode
  content: string
  tags: string[]
}

interface NoteTemplatesProps {
  onSelectTemplate: (template: NoteTemplate) => void
  onClose: () => void
}

const templates: NoteTemplate[] = [
  {
    id: 'meeting-notes',
    name: 'Meeting Notes',
    description: 'Structure for capturing meeting discussions and action items',
    icon: <Users className="h-5 w-5" />,
    content: `<h1>Meeting Notes</h1>

<p><strong>Date:</strong> [Date]<br>
<strong>Attendees:</strong> [List attendees]<br>
<strong>Agenda:</strong> [Meeting agenda]</p>

<h2>Discussion Points</h2>
<ul>
<li>[Key point 1]</li>
<li>[Key point 2]</li>
<li>[Key point 3]</li>
</ul>

<h2>Action Items</h2>
<ul>
<li>[ ] [Action item 1] - [Assignee] - [Due date]</li>
<li>[ ] [Action item 2] - [Assignee] - [Due date]</li>
</ul>

<h2>Next Steps</h2>
<ul>
<li>[Next step 1]</li>
<li>[Next step 2]</li>
</ul>

<h2>Notes</h2>
<p>[Additional notes and observations]</p>`,
    tags: ['meeting', 'work', 'collaboration']
  },
  {
    id: 'lecture-notes',
    name: 'Lecture Notes',
    description: 'Template for academic lecture notes with key concepts',
    icon: <BookOpen className="h-5 w-5" />,
    content: `<h1>[Subject] - [Topic]</h1>

<p><strong>Date:</strong> [Date]<br>
<strong>Instructor:</strong> [Instructor name]<br>
<strong>Course:</strong> [Course name]</p>

<h2>Learning Objectives</h2>
<ul>
<li>[Objective 1]</li>
<li>[Objective 2]</li>
<li>[Objective 3]</li>
</ul>

<h2>Key Concepts</h2>
<h3>[Concept 1]</h3>
<ul>
<li>Definition: [Definition]</li>
<li>Example: [Example]</li>
<li>Application: [How it's used]</li>
</ul>

<h3>[Concept 2]</h3>
<ul>
<li>Definition: [Definition]</li>
<li>Example: [Example]</li>
<li>Application: [How it's used]</li>
</ul>

<h2>Important Formulas/Equations</h2>
<ul>
<li>[Formula 1]: [Explanation]</li>
<li>[Formula 2]: [Explanation]</li>
</ul>

<h2>Questions & Clarifications</h2>
<ul>
<li>[Question 1]</li>
<li>[Question 2]</li>
</ul>

<h2>Summary</h2>
<p>[Key takeaways from the lecture]</p>`,
    tags: ['academic', 'lecture', 'education']
  },
  {
    id: 'project-plan',
    name: 'Project Plan',
    description: 'Comprehensive project planning and tracking template',
    icon: <Target className="h-5 w-5" />,
    content: `<h1>[Project Name] - Project Plan</h1>

<p><strong>Project Manager:</strong> [Name]<br>
<strong>Start Date:</strong> [Date]<br>
<strong>Target Completion:</strong> [Date]<br>
<strong>Status:</strong> [Planning/In Progress/On Hold/Completed]</p>

<h2>Project Overview</h2>
<p><strong>Objective:</strong> [Project objective]<br>
<strong>Scope:</strong> [What's included and excluded]<br>
<strong>Success Criteria:</strong> [How success is measured]</p>

<h2>Team & Roles</h2>
<ul>
<li>[Role 1]: [Name] - [Responsibilities]</li>
<li>[Role 2]: [Name] - [Responsibilities]</li>
</ul>

<h2>Timeline & Milestones</h2>
<ul>
<li>[ ] [Milestone 1] - [Due date]</li>
<li>[ ] [Milestone 2] - [Due date]</li>
<li>[ ] [Milestone 3] - [Due date]</li>
</ul>

<h2>Tasks & Deliverables</h2>
<h3>Phase 1: [Phase name]</h3>
<ul>
<li>[ ] [Task 1] - [Assignee] - [Due date]</li>
<li>[ ] [Task 2] - [Assignee] - [Due date]</li>
</ul>

<h3>Phase 2: [Phase name]</h3>
<ul>
<li>[ ] [Task 1] - [Assignee] - [Due date]</li>
<li>[ ] [Task 2] - [Assignee] - [Due date]</li>
</ul>

<h2>Resources & Budget</h2>
<ul>
<li><strong>Budget:</strong> [Amount]</li>
<li><strong>Resources needed:</strong> [List resources]</li>
<li><strong>Tools & Software:</strong> [List tools]</li>
</ul>

<h2>Risks & Mitigation</h2>
<ul>
<li><strong>Risk 1:</strong> [Description] - [Mitigation strategy]</li>
<li><strong>Risk 2:</strong> [Description] - [Mitigation strategy]</li>
</ul>

<h2>Notes</h2>
<p>[Additional project notes]</p>`,
    tags: ['project', 'planning', 'management']
  },
  {
    id: 'daily-journal',
    name: 'Daily Journal',
    description: 'Personal daily reflection and planning template',
    icon: <Calendar className="h-5 w-5" />,
    content: `<h1>[Date] - Daily Journal</h1>

<h2>Today's Goals</h2>
<ul>
<li>[ ] [Goal 1]</li>
<li>[ ] [Goal 2]</li>
<li>[ ] [Goal 3]</li>
</ul>

<h2>What I Accomplished</h2>
<ul>
<li>[Accomplishment 1]</li>
<li>[Accomplishment 2]</li>
<li>[Accomplishment 3]</li>
</ul>

<h2>Challenges & Learnings</h2>
<p><strong>Challenge:</strong> [What was difficult]<br>
<strong>Learning:</strong> [What I learned from it]</p>

<h2>Gratitude</h2>
<ul>
<li>[Thing I'm grateful for 1]</li>
<li>[Thing I'm grateful for 2]</li>
<li>[Thing I'm grateful for 3]</li>
</ul>

<h2>Tomorrow's Focus</h2>
<ul>
<li>[Priority 1]</li>
<li>[Priority 2]</li>
<li>[Priority 3]</li>
</ul>

<h2>Reflection</h2>
<p>[How I'm feeling and what I want to improve]</p>`,
    tags: ['personal', 'journal', 'reflection']
  },
  {
    id: 'idea-capture',
    name: 'Idea Capture',
    description: 'Quick template for capturing and developing ideas',
    icon: <Lightbulb className="h-5 w-5" />,
    content: `<h1>[Idea Title]</h1>

<p><strong>Date:</strong> [Date]<br>
<strong>Status:</strong> [New/In Development/Testing/Implemented/Abandoned]</p>

<h2>The Idea</h2>
<p>[Describe the core idea in 1-2 sentences]</p>

<h2>Problem It Solves</h2>
<p>[What problem does this idea address?]</p>

<h2>Target Audience</h2>
<p>[Who would benefit from this idea?]</p>

<h2>Implementation Approach</h2>
<p>[How could this be implemented?]</p>

<h2>Resources Needed</h2>
<ul>
<li>[Resource 1]</li>
<li>[Resource 2]</li>
<li>[Resource 3]</li>
</ul>

<h2>Potential Challenges</h2>
<ul>
<li>[Challenge 1]</li>
<li>[Challenge 2]</li>
</ul>

<h2>Next Steps</h2>
<ul>
<li>[ ] [Action 1]</li>
<li>[ ] [Action 2]</li>
<li>[ ] [Action 3]</li>
</ul>

<h2>Related Ideas</h2>
<ul>
<li>[Related idea 1]</li>
<li>[Related idea 2]</li>
</ul>

<h2>Notes</h2>
<p>[Additional thoughts and considerations]</p>`,
    tags: ['ideas', 'innovation', 'brainstorming']
  },
  {
    id: 'study-session',
    name: 'Study Session',
    description: 'Template for structured study sessions and review',
    icon: <Zap className="h-5 w-5" />,
    content: `<h1>Study Session - [Subject/Topic]</h1>

<p><strong>Date:</strong> [Date]<br>
<strong>Duration:</strong> [Time spent]<br>
<strong>Materials:</strong> [Textbooks, notes, resources used]</p>

<h2>Study Goals</h2>
<ul>
<li>[Goal 1]</li>
<li>[Goal 2]</li>
<li>[Goal 3]</li>
</ul>

<h2>Topics Covered</h2>
<h3>[Topic 1]</h3>
<ul>
<li>Key points: [Main points]</li>
<li>Understanding level: [1-5 scale]</li>
<li>Questions: [Questions I have]</li>
</ul>

<h3>[Topic 2]</h3>
<ul>
<li>Key points: [Main points]</li>
<li>Understanding level: [1-5 scale]</li>
<li>Questions: [Questions I have]</li>
</ul>

<h2>Practice Problems</h2>
<ul>
<li>[Problem 1]: [Solution approach]</li>
<li>[Problem 2]: [Solution approach]</li>
</ul>

<h2>Difficult Concepts</h2>
<ul>
<li>[Concept 1]: [Why it's difficult] - [How to improve understanding]</li>
<li>[Concept 2]: [Why it's difficult] - [How to improve understanding]</li>
</ul>

<h2>Review Questions</h2>
<ul>
<li>[Question 1]</li>
<li>[Question 2]</li>
<li>[Question 3]</li>
</ul>

<h2>Next Study Session</h2>
<ul>
<li>[What to focus on next]</li>
<li>[Materials to review]</li>
<li>[Practice problems to work on]</li>
</ul>

<h2>Confidence Level</h2>
<p><strong>Overall:</strong> [1-5 scale]<br>
<strong>Areas needing work:</strong> [List areas]</p>`,
    tags: ['study', 'academic', 'learning']
  }
]

export function NoteTemplates({ onSelectTemplate, onClose }: NoteTemplatesProps) {
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTag, setSelectedTag] = useState<string | null>(null)

  // Get all unique tags
  const allTags = Array.from(new Set(templates.flatMap(t => t.tags))).sort()

  // Filter templates
  const filteredTemplates = templates.filter(template => {
    const matchesSearch = template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         template.description.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesTag = !selectedTag || template.tags.includes(selectedTag)
    return matchesSearch && matchesTag
  })

  const handleSelectTemplate = (template: NoteTemplate) => {
    setSelectedTemplate(template.id)
    setTimeout(() => {
      onSelectTemplate(template)
    }, 200)
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-[#141820] rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-[#232a36]">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Note Templates</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">Choose a template to get started quickly</p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="h-8 w-8 p-0"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Search and Filters */}
        <div className="p-6 border-b border-gray-200 dark:border-[#232a36] space-y-4">
          <div className="relative">
            <input
              type="text"
              placeholder="Search templates..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-4 py-2 border border-gray-200 dark:border-[#232a36] rounded-lg bg-gray-50 dark:bg-[#0f1115] text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-orange-500 focus:border-transparent"
            />
          </div>

          {/* Tag Filters */}
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setSelectedTag(null)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                !selectedTag
                  ? 'bg-orange-500 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
            >
              All
            </button>
            {allTags.map(tag => (
              <button
                key={tag}
                onClick={() => setSelectedTag(selectedTag === tag ? null : tag)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  selectedTag === tag
                    ? 'bg-orange-500 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                {tag}
              </button>
            ))}
          </div>
        </div>

        {/* Templates Grid */}
        <div className="p-6 overflow-y-auto max-h-96">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredTemplates.map(template => (
              <Card
                key={template.id}
                className={`cursor-pointer transition-all hover:shadow-md ${
                  selectedTemplate === template.id
                    ? 'ring-2 ring-orange-500 bg-orange-50 dark:bg-orange-950/20'
                    : 'hover:border-orange-300 dark:hover:border-orange-600'
                }`}
                onClick={() => handleSelectTemplate(template)}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
                      {template.icon}
                    </div>
                    <div>
                      <CardTitle className="text-lg">{template.name}</CardTitle>
                      <CardDescription className="text-sm">
                        {template.description}
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="flex flex-wrap gap-1 mb-3">
                    {template.tags.map(tag => (
                      <span
                        key={tag}
                        className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 text-xs rounded"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                  
                  {selectedTemplate === template.id && (
                    <div className="flex items-center text-orange-600 dark:text-orange-400 text-sm">
                      <Check className="h-4 w-4 mr-1" />
                      Selected
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>

          {filteredTemplates.length === 0 && (
            <div className="text-center py-8">
              <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500 dark:text-gray-400">No templates found</p>
              <p className="text-sm text-gray-400 dark:text-gray-500">Try adjusting your search or filters</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 dark:border-[#232a36] bg-gray-50 dark:bg-[#0f1115]">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {filteredTemplates.length} template{filteredTemplates.length !== 1 ? 's' : ''} available
            </p>
            <div className="flex space-x-2">
              <Button variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button
                onClick={() => {
                  const template = templates.find(t => t.id === selectedTemplate)
                  if (template) onSelectTemplate(template)
                }}
                disabled={!selectedTemplate}
                className="bg-orange-500 hover:bg-orange-600 text-white"
              >
                <Plus className="h-4 w-4 mr-1" />
                Use Template
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
