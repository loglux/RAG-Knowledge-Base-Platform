import React from 'react'

interface FieldProps {
  label?: React.ReactNode
  hint?: React.ReactNode
  children: React.ReactNode
  className?: string
  labelClassName?: string
  hintClassName?: string
}

export function Field({
  label,
  hint,
  children,
  className,
  labelClassName,
  hintClassName,
}: FieldProps) {
  return (
    <div className={className}>
      {label && (
        <label className={[
          'block text-sm font-medium text-gray-300 mb-2',
          labelClassName,
        ].filter(Boolean).join(' ')}>
          {label}
        </label>
      )}
      {children}
      {hint && (
        <p className={[
          'text-xs text-gray-400 mt-1',
          hintClassName,
        ].filter(Boolean).join(' ')}>
          {hint}
        </p>
      )}
    </div>
  )
}
