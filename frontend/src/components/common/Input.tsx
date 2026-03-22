import React from 'react'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  fullWidth?: boolean
}

export function Input({ className, fullWidth = true, ...rest }: InputProps) {
  const classes = [
    fullWidth ? 'w-full' : '',
    'px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500',
    className,
  ].filter(Boolean).join(' ')

  return <input className={classes} {...rest} />
}
