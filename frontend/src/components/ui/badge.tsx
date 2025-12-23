import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-1.5 py-0.5 text-[11px] font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-[var(--accent)] text-white",
        secondary:
          "border-transparent bg-[var(--background-subtle)] text-[var(--text-secondary)]",
        destructive:
          "border-transparent bg-[var(--error)] text-white",
        outline: "border-[var(--border)] text-[var(--text-secondary)] bg-transparent",
        success:
          "border-transparent bg-[var(--success-subtle)] text-[var(--success)]",
        warning:
          "border-transparent bg-[var(--warning-subtle)] text-[var(--warning)]",
        langchain:
          "border-transparent bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
        llamaindex:
          "border-transparent bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400",
        openai:
          "border-transparent bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
