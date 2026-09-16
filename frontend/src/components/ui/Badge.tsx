import React from 'react';
import './Badge.css';

interface BadgeProps {
  children: React.ReactNode;
  severity?: 'INFO' | 'WARNING' | 'CRITICAL' | 'SUCCESS' | 'OFFLINE' | 'ROUTINE' | 'URGENT' | string;
  className?: string;
  showDot?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({ 
  children, 
  severity = 'INFO', 
  className = '',
  showDot = true
}) => {
  // Map ROUTINE to info, URGENT to warning if not styled explicitly
  let variant = severity.toLowerCase();
  if (variant === 'routine') variant = 'info';
  if (variant === 'urgent') variant = 'warning';

  return (
    <span className={`badge badge-${variant} ${className}`}>
      {showDot && <span className="badge-dot"></span>}
      {children}
    </span>
  );
};
