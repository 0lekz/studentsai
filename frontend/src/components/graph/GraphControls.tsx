import type { GraphSettings } from './drawGraph'
import { Input } from '@/components/ui/input'

interface GraphControlsProps {
  settings: GraphSettings
  hideIsolated: boolean
  onHideIsolatedChange: (value: boolean) => void
  onSettingsChange: (patch: Partial<GraphSettings>) => void
}

const checkboxClass = 'h-4 w-4 rounded border-input accent-[hsl(var(--primary))]'

export function GraphControls({ settings, hideIsolated, onHideIsolatedChange, onSettingsChange }: GraphControlsProps) {
  return (
    <div className="grid grid-cols-2 items-center gap-3 text-caption text-muted-foreground sm:grid-cols-3 xl:grid-cols-6">
      <label className="flex items-center gap-2">
        <input type="checkbox" className={checkboxClass} checked={hideIsolated} onChange={(event) => onHideIsolatedChange(event.target.checked)} />
        Hide isolated
      </label>
      <label className="flex items-center gap-2">
        Distance
        <Input
          type="number"
          step={1}
          value={settings.linkDistance}
          onChange={(event) => onSettingsChange({ linkDistance: Number(event.target.value) || 0 })}
          className="h-7 w-16 px-2 text-caption"
        />
      </label>
      <label className="flex items-center gap-2">
        Node size
        <Input
          type="number"
          step={0.01}
          value={settings.nodeSizeBase}
          onChange={(event) => onSettingsChange({ nodeSizeBase: Number(event.target.value) || 0 })}
          className="h-7 w-16 px-2 text-caption"
        />
      </label>
      <label className="flex items-center gap-2">
        Edge width
        <Input
          type="number"
          step={0.01}
          value={settings.linkThicknessMul}
          onChange={(event) => onSettingsChange({ linkThicknessMul: Number(event.target.value) || 0 })}
          className="h-7 w-16 px-2 text-caption"
        />
      </label>
      <label className="flex items-center gap-2">
        <input type="checkbox" className={checkboxClass} checked={settings.colorCoded} onChange={(event) => onSettingsChange({ colorCoded: event.target.checked })} />
        Color coded
      </label>
      <label className="flex items-center gap-2">
        <input type="checkbox" className={checkboxClass} checked={settings.showLabels} onChange={(event) => onSettingsChange({ showLabels: event.target.checked })} />
        Labels
      </label>
    </div>
  )
}
