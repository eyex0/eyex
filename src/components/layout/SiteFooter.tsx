export function SiteFooter() {
  return (
    <footer className="w-full py-20 px-margin-desktop bg-background border-t border-white/10">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-12 mb-20">
        <div className="col-span-1 md:col-span-1 space-y-6">
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-primary text-2xl">visibility</span>
            <span className="font-label-caps text-label-caps text-primary text-xl">πX</span>
          </div>
          <p className="font-body-md text-on-surface-variant opacity-60 max-w-xs">
            Engineering the next generation of visual intelligence. High-performance, low-latency, mission-ready.
          </p>
        </div>
        <div className="space-y-6">
          <h5 className="font-label-caps text-label-caps text-primary uppercase tracking-widest">Platform</h5>
          <ul className="space-y-4 font-mono-data text-mono-data text-on-surface-variant">
            <li><a className="hover:text-secondary-fixed-dim underline decoration-transparent hover:decoration-secondary-fixed-dim transition-all" href="#">Documentation</a></li>
            <li><a className="hover:text-secondary-fixed-dim underline decoration-transparent hover:decoration-secondary-fixed-dim transition-all" href="#">API Reference</a></li>
            <li><a className="hover:text-secondary-fixed-dim underline decoration-transparent hover:decoration-secondary-fixed-dim transition-all" href="#">Core Systems</a></li>
            <li><a className="hover:text-secondary-fixed-dim underline decoration-transparent hover:decoration-secondary-fixed-dim transition-all" href="#">Changelog</a></li>
          </ul>
        </div>
        <div className="space-y-6">
          <h5 className="font-label-caps text-label-caps text-primary uppercase tracking-widest">Company</h5>
          <ul className="space-y-4 font-mono-data text-mono-data text-on-surface-variant">
            <li><a className="hover:text-secondary-fixed-dim underline decoration-transparent hover:decoration-secondary-fixed-dim transition-all" href="/about">About πX</a></li>
            <li><a className="hover:text-secondary-fixed-dim underline decoration-transparent hover:decoration-secondary-fixed-dim transition-all" href="#">Careers</a></li>
            <li><a className="hover:text-secondary-fixed-dim underline decoration-transparent hover:decoration-secondary-fixed-dim transition-all" href="/contact">Contact</a></li>
            <li><a className="hover:text-secondary-fixed-dim underline decoration-transparent hover:decoration-secondary-fixed-dim transition-all" href="#">Privacy</a></li>
          </ul>
        </div>
        <div className="space-y-6">
          <h5 className="font-label-caps text-label-caps text-primary uppercase tracking-widest">Newsletter</h5>
          <div className="flex flex-col gap-4">
            <div className="relative">
              <input className="w-full bg-transparent border border-white/20 px-4 py-3 font-mono-data text-xs text-primary focus:outline-none focus:border-secondary-fixed-dim transition-colors uppercase tracking-widest" placeholder="YOUR@EMAIL.COM" type="email" />
              <button className="absolute right-2 top-1/2 -translate-y-1/2 material-symbols-outlined text-secondary-fixed-dim">arrow_forward</button>
            </div>
          </div>
        </div>
      </div>
      <div className="flex flex-col md:flex-row justify-between items-center pt-8 border-t border-white/5">
        <span className="font-mono-data text-mono-data text-on-surface-variant/40">© 2024 πX CORE. ALL RIGHTS RESERVED.</span>
        <div className="flex gap-8 mt-4 md:mt-0 font-mono-data text-mono-data text-on-surface-variant/40">
          <span>V4.0.2</span>
          <span>STATUS: STABLE</span>
        </div>
      </div>
    </footer>
  );
}
