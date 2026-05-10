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
        {/* Abstract swift — three strokes pinched right */}
        <path d="M8 14h12l4-4" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M8 18h16" stroke="white" strokeWidth="2.5" strokeLinecap="round" />
        <path d="M8 22h12l4 4" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      {showText && (
        <span className="font-bold text-gray-900 tracking-tight text-base">Finch</span>
      )}
    </div>
  );
}
