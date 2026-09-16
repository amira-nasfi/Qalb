import React from 'react';
import './Card.css';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: React.ReactNode;
  footer?: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({ children, className = '', title, footer }) => {
  return (
    <div className={`card ${className}`}>
      {title && (
        <div className="card-header">
          {typeof title === 'string' ? <h3 className="card-title">{title}</h3> : title}
        </div>
      )}
      <div className="card-body">
        {children}
      </div>
      {footer && (
        <div className="card-footer">
          {footer}
        </div>
      )}
    </div>
  );
};
