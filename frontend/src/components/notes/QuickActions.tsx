'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'
import { type Note } from '@/lib/api'
import { 
  MoreHorizontal, 
  Copy, 
  Download, 
  Share, 
  Archive, 
  Star, 
  Tag,
  Trash2,
  Edit
} from 'lucide-react'

interface QuickActionsProps {
  note: Note & { starred?: boolean; archived?: boolean }
  onEdit?: () => void
  onDelete?: () => void
  onDuplicate?: () => void
  onArchive?: () => void
  onStar?: () => void
  onAddTags?: () => void
  onExport?: () => void
  onShare?: () => void
}

export function QuickActions({ 
  note, 
  onEdit, 
  onDelete, 
  onDuplicate, 
  onArchive, 
  onStar, 
  onAddTags
}: QuickActionsProps) {
  const [isOpen, setIsOpen] = useState(false)

  const handleExport = () => {
    if (!note) return
    
    const content = `# ${note.title}\n\n${note.content}`
    const blob = new Blob([content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${note.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.md`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleCopy = () => {
    if (!note) return
    
    const content = `# ${note.title}\n\n${note.content}`
    navigator.clipboard.writeText(content)
  }

  const handleShare = () => {
    if (!note) return
    
    if (navigator.share) {
      navigator.share({
        title: note.title,
        text: note.content,
        url: window.location.href
      })
    } else {
      // Fallback to copying to clipboard
      navigator.clipboard.writeText(window.location.href)
    }
  }

  return (
    <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
        >
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuItem onClick={onEdit}>
          <Edit className="h-4 w-4 mr-2" />
          Edit Note
        </DropdownMenuItem>
        
        <DropdownMenuItem onClick={onDuplicate}>
          <Copy className="h-4 w-4 mr-2" />
          Duplicate
        </DropdownMenuItem>
        
        <DropdownMenuSeparator />
        
        <DropdownMenuItem onClick={onAddTags}>
          <Tag className="h-4 w-4 mr-2" />
          Add Tags
        </DropdownMenuItem>
        
        <DropdownMenuItem onClick={onStar}>
          <Star className="h-4 w-4 mr-2" />
          {note?.starred ? 'Remove Star' : 'Star Note'}
        </DropdownMenuItem>
        
        <DropdownMenuItem onClick={onArchive}>
          <Archive className="h-4 w-4 mr-2" />
          {note?.archived ? 'Unarchive' : 'Archive'}
        </DropdownMenuItem>
        
        <DropdownMenuSeparator />
        
        <DropdownMenuItem onClick={handleCopy}>
          <Copy className="h-4 w-4 mr-2" />
          Copy Content
        </DropdownMenuItem>
        
        <DropdownMenuItem onClick={handleExport}>
          <Download className="h-4 w-4 mr-2" />
          Export as Markdown
        </DropdownMenuItem>
        
        <DropdownMenuItem onClick={handleShare}>
          <Share className="h-4 w-4 mr-2" />
          Share Note
        </DropdownMenuItem>
        
        <DropdownMenuSeparator />
        
        <DropdownMenuItem 
          onClick={onDelete}
          className="text-red-600 dark:text-red-400"
        >
          <Trash2 className="h-4 w-4 mr-2" />
          Delete Note
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
