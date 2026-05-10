'use client';

interface FinchLogoProps {
  size?: number;
  showText?: boolean;
  className?: string;
}

export default function FinchLogo({ size = 28, showText = false, className = '' }: FinchLogoProps) {
  return (
    <div className={`flex items-center gap-2 select-none ${className}`}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 36 36"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <rect width="36" height="36" rx="8" fill="#10b981" />
        {/* Bar chart forming an F */}
        <rect x="8" y="8" width="5" height="20" rx="1.5" fill="white" />
        <rect x="15" y="8" width="5" height="12" rx="1.5" fill="white" />
        <rect x="22" y="14" width="5" height="6" rx="1.5" fill="white" />
      </svg>
      {showText && (
        <span className="font-bold text-gray-900 tracking-tight text-base">Finch</span>
      )}
    </div>
  );
}
