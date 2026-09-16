import React from 'react';
import './Button.css';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  className = '',
  disabled,
  ...props
}) => {
  const baseClass = `btn btn-${variant} btn-${size} ${isLoading ? 'btn-loading' : ''} ${className}`;
  
  return (
    <button className={baseClass.trim()} disabled={disabled || isLoading} {...props}>
      {children}
    </button>
  );
};
