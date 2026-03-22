import React from 'react'

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  fullWidth?: boolean
}

export function Textarea({ className, fullWidth = true, ...rest }: TextareaProps) {
  const classes = [
    fullWidth ? 'w-full' : '',
    'px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500',
    className,
  ].filter(Boolean).join(' ')

  return <textarea className={classes} {...rest} />
}
