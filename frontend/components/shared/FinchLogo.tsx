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
        {/* Rounded square background */}
        <rect width="36" height="36" rx="8" fill="#10b981" />

        {/* Bird silhouette — simple, bold */}
        <path
          d="M10 22C10 22 9 18 11 15C13 12 16 11 18 10L22 8"
          stroke="white"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Chart line extending from bird — the AI/trading element */}
        <path
          d="M22 8L24 13L26 10L28 12"
          stroke="white"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Wing */}
        <path
          d="M12 19C14 17 16 16 18 16"
          stroke="rgba(255,255,255,0.5)"
          strokeWidth="2"
          strokeLinecap="round"
        />
        {/* Eye — neural dot */}
        <circle cx="19" cy="11.5" r="1.5" fill="white" />

        {/* Small neural dots along the chart — AI feel */}
        <circle cx="24" cy="13" r="1" fill="rgba(255,255,255,0.6)" />
        <circle cx="28" cy="12" r="1" fill="rgba(255,255,255,0.6)" />
      </svg>
      {showText && (
        <span className="font-bold text-gray-900 tracking-tight text-base">Finch</span>
      )}
    </div>
  );
}
