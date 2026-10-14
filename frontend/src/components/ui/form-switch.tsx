import * as React from "react"
import { cn } from "@/lib/utils"

export type SwitchProps = React.InputHTMLAttributes<HTMLInputElement>

const Switch = React.forwardRef<HTMLInputElement, SwitchProps>(
  ({ className, ...props }, ref) => (
    <input
      type="checkbox"
      ref={ref}
      className={cn(
        "h-6 w-11 rounded-full bg-gray-200 transition-colors focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-offset-2 checked:bg-orange-600 dark:bg-gray-700 dark:checked:bg-orange-500",
        className
      )}
      {...props}
    />
  )
)
Switch.displayName = "Switch"

export { Switch }
