import React from 'react'

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  fullWidth?: boolean
}

export function Select({ className, fullWidth = false, children, ...rest }: SelectProps) {
  const classes = [
    fullWidth ? 'w-full' : '',
    'px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500',
    className,
  ].filter(Boolean).join(' ')

  return <select className={classes} {...rest}>{children}</select>
}
