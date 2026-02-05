import React from 'react'

type PanelProps<T extends React.ElementType = 'div'> = {
  as?: T
  className?: string
  children?: React.ReactNode
} & React.ComponentPropsWithoutRef<T>

export function Panel<T extends React.ElementType = 'div'>({
  as,
  className,
  children,
  ...rest
}: PanelProps<T>) {
  const Component = as || 'div'
  const classes = ['panel', className].filter(Boolean).join(' ')
  return (
    <Component className={classes} {...rest}>
      {children}
    </Component>
  )
}
