import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { Menu, X } from "lucide-react";

export function SiteHeader() {
  const [open, setOpen] = useState(false);

  return (
    <header className="fixed top-0 w-full z-50 flex justify-between items-center px-margin-mobile md:px-margin-desktop h-20 bg-background/80 dark:bg-background/80 backdrop-blur-xl border-b border-white/10">
      <div className="flex items-center gap-4">
        <span className="material-symbols-outlined text-primary font-headline-md text-headline-md">visibility</span>
        <Link to="/" className="font-headline-md text-headline-md font-bold tracking-tighter text-primary dark:text-primary">
          πX
        </Link>
      </div>
      <nav className="hidden md:flex gap-10 items-center">
        <Link className="font-label-caps text-label-caps text-primary transition-colors hover:text-secondary-container" to="/">Vision Hero</Link>
        <Link className="font-label-caps text-label-caps text-on-surface-variant transition-colors hover:text-secondary-container" to="/about">Solutions</Link>
        <Link className="font-label-caps text-label-caps text-on-surface-variant transition-colors hover:text-secondary-container" to="/analytics">Analytics</Link>
        <Link className="font-label-caps text-label-caps text-on-surface-variant transition-colors hover:text-secondary-container" to="/contact">Contact</Link>
      </nav>
      <div className="flex items-center gap-6">
        <button 
          className="material-symbols-outlined text-on-surface-variant hover:text-primary transition-colors lg:hidden"
          onClick={() => setOpen(!open)}
        >
          {open ? 'close' : 'menu'}
        </button>
        <Link to="/login" className="hidden lg:inline-flex border border-white/20 text-primary font-label-caps text-label-caps px-4 py-2 rounded hover:border-white transition-all uppercase tracking-widest">
          Login
        </Link>
      </div>

      {open && (
        <div className="absolute top-20 left-0 w-full bg-background border-b border-white/10 p-6 flex flex-col gap-6 lg:hidden">
          <Link onClick={() => setOpen(false)} className="font-label-caps text-label-caps text-primary uppercase" to="/">Vision Hero</Link>
          <Link onClick={() => setOpen(false)} className="font-label-caps text-label-caps text-on-surface-variant uppercase" to="/about">Solutions</Link>
          <Link onClick={() => setOpen(false)} className="font-label-caps text-label-caps text-on-surface-variant uppercase" to="/analytics">Analytics</Link>
          <Link onClick={() => setOpen(false)} className="font-label-caps text-label-caps text-on-surface-variant uppercase" to="/contact">Contact</Link>
          <Link onClick={() => setOpen(false)} className="font-label-caps text-label-caps text-secondary-fixed-dim uppercase" to="/login">Login</Link>
        </div>
      )}
    </header>
  );
}
