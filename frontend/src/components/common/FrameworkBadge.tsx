import { Badge } from '@/components/ui/badge'

interface FrameworkBadgeProps {
  framework: string
  small?: boolean
}

export function FrameworkBadge({ framework, small = false }: FrameworkBadgeProps) {
  const frameworks = framework.split(',').map((f) => f.trim().toLowerCase())

  return (
    <div className="flex items-center gap-1">
      {frameworks.map((f) => {
        let variant: 'langchain' | 'llamaindex' | 'openai' | 'secondary' = 'secondary'
        let label = f

        if (f.includes('langchain')) {
          variant = 'langchain'
          label = 'LangChain'
        } else if (f.includes('llamaindex') || f.includes('llama_index')) {
          variant = 'llamaindex'
          label = 'LlamaIndex'
        } else if (f.includes('openai')) {
          variant = 'openai'
          label = 'OpenAI'
        }

        return (
          <Badge
            key={f}
            variant={variant}
            className={small ? 'text-xs px-1.5 py-0' : ''}
          >
            {label}
          </Badge>
        )
      })}
    </div>
  )
}
