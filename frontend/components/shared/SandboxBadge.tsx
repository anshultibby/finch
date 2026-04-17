'use client';

export default function SandboxBadge({ className = '' }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-amber-600 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full ${className}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
      Sandbox
    </span>
  );
}
