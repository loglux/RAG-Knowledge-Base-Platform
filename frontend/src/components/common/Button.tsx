import React from 'react'

type ButtonVariant = 'primary' | 'secondary'
type ButtonSize = 'md' | 'sm' | 'xs' | 'xs-wide'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
}

const sizeClassMap: Record<ButtonSize, string> = {
  md: '',
  sm: 'btn-sm',
  xs: 'btn-xs',
  'xs-wide': 'btn-xs-wide',
}

export function Button({
  variant = 'secondary',
  size = 'md',
  className,
  ...rest
}: ButtonProps) {
  const baseClass = variant === 'primary' ? 'btn-primary' : 'btn-secondary'
  const sizeClass = sizeClassMap[size]
  const classes = [baseClass, sizeClass, className].filter(Boolean).join(' ')

  return <button className={classes} {...rest} />
}
