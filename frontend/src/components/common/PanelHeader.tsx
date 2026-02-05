import React from 'react'

interface PanelHeaderProps {
  title: React.ReactNode
  actions?: React.ReactNode
  className?: string
}

export function PanelHeader({ title, actions, className }: PanelHeaderProps) {
  const classes = ['flex items-center justify-between', className].filter(Boolean).join(' ')
  return (
    <div className={classes}>
      <div className="min-w-0">{title}</div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}
