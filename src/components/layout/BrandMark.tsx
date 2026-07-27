import { Eye } from "lucide-react";

export function BrandMark({ className = "" }: { className?: string }) {
  return (
    <span className={`flex items-center gap-2.5 text-eye-white ${className}`}>
      <span className="flex items-center justify-center w-8 h-8 bg-eye-surface border border-eye-border rounded-lg">
        <Eye size={16} className="text-primary" />
      </span>
      <span className="font-display font-medium text-[15px] tracking-tight leading-none">
        πX <span className="text-eye-text font-light">Technologies</span>
      </span>
    </span>
  );
}
