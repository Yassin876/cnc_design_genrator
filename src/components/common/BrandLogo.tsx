import React from 'react';
import defaultLogo from '../../assets/anti-design-logo.png';

interface BrandLogoProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showText?: boolean;
  className?: string;
  logoSrc?: string;
}

export const BrandLogo: React.FC<BrandLogoProps> = ({
  size = 'md',
  showText = true,
  className = '',
  logoSrc = defaultLogo
}) => {
  const textSizeClass = {
    sm: 'text-xs font-bold',
    md: 'text-sm font-black',
    lg: 'text-lg font-black',
    xl: 'text-2xl font-black'
  }[size];

  const imgHeightClass = {
    sm: 'h-6 max-h-6',
    md: 'h-8 max-h-8',
    lg: 'h-10 max-h-10',
    xl: 'h-14 max-h-14'
  }[size];

  return (
    <div className={`flex items-center space-x-2.5 select-none ${className}`}>
      <div className={`${imgHeightClass} flex items-center justify-center shrink-0 transition-transform duration-200 group-hover:scale-105`}>
        <img
          src={logoSrc}
          alt="Anti Design Logo"
          className="h-full w-auto object-contain drop-shadow-sm"
          onError={(e) => {
            // Fallback to public asset path if bundler asset fails
            (e.currentTarget as HTMLImageElement).src = '/anti-design-logo.png';
          }}
        />
      </div>

      {showText && (
        <span className={`${textSizeClass} tracking-tight bg-gradient-to-r from-purple-700 via-indigo-600 to-indigo-900 bg-clip-text text-transparent whitespace-nowrap`}>
          Anti Design
        </span>
      )}
    </div>
  );
};
