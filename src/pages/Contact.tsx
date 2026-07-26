export function ContactPage() {
  return (
    <div className="relative min-h-screen pt-32 pb-20 px-margin-mobile md:px-margin-desktop">
      {/* Subtle Ambient Background Shader */}
      <div className="fixed inset-0 pointer-events-none z-[-1] opacity-40"></div>
      
      <div className="max-w-[1400px] mx-auto">
        {/* Hero Section */}
        <div className="mb-16">
          <div className="flex items-center gap-3 mb-4">
            <span className="w-2 h-2 rounded-full bg-secondary-fixed-dim animate-pulse"></span>
            <span className="font-mono-data text-mono-data text-secondary-fixed-dim tracking-widest">SYSTEM_READY // INQUIRY_PORTAL</span>
          </div>
          <h1 className="font-display-lg text-display-lg max-w-4xl text-primary leading-none uppercase">
            Deploy High-Performance Vision into Your Infrastructure
          </h1>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-gutter items-start">
          {/* Left Column: Brand Trust & Coordinates */}
          <div className="lg:col-span-5 space-y-8">
            {/* Direct Line Priority */}
            <div className="glass-panel p-8 rounded-lg border border-white/5">
              <h3 className="font-label-caps text-label-caps text-secondary-fixed-dim mb-6 uppercase tracking-widest">Direct Line Priority</h3>
              <div className="space-y-6">
                <div className="flex items-start gap-4">
                  <span className="material-symbols-outlined text-outline-variant" style={{ fontVariationSettings: "'FILL' 1" }}>verified_user</span>
                  <div>
                    <p className="font-mono-data text-white mb-1">SECURE ENCRYPTED CHANNEL</p>
                    <p className="text-on-surface-variant text-sm">All inquiries are processed through our Tier-4 data facility with end-to-end AES-256 encryption.</p>
                  </div>
                </div>
                <div className="flex items-start gap-4">
                  <span className="material-symbols-outlined text-outline-variant" style={{ fontVariationSettings: "'FILL' 1" }}>speed</span>
                  <div>
                    <p className="font-mono-data text-white mb-1">RAPID RESPONSE PROTOCOL</p>
                    <p className="text-on-surface-variant text-sm">Strategic deployment specialists respond to infrastructure queries within 4 business hours.</p>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Secure/Intel Details */}
            <div className="grid grid-cols-2 gap-4">
              <div className="glass-panel p-6 border border-white/5 rounded-lg">
                <p className="font-label-caps text-[10px] text-outline-variant mb-2">NETWORK_STATUS</p>
                <p className="font-mono-data text-white text-lg">OPTIMIZED</p>
              </div>
              <div className="glass-panel p-6 border border-white/5 rounded-lg">
                <p className="font-label-caps text-[10px] text-outline-variant mb-2">ACTIVE_NODES</p>
                <p className="font-mono-data text-white text-lg">1,402 / GBL</p>
              </div>
            </div>
            
            {/* Global Hub Coordinates Map */}
            <div className="relative w-full aspect-video glass-panel overflow-hidden rounded-lg group border border-white/5">
              <div className="absolute inset-0 z-10 bg-gradient-to-t from-black/60 to-transparent"></div>
              <div className="absolute top-4 left-4 z-20 flex items-center gap-2 bg-black/80 px-3 py-1 border border-white/10 rounded">
                <span className="material-symbols-outlined text-secondary-fixed-dim text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>location_on</span>
                <span className="font-mono-data text-[10px] text-white">HUB_COORDS: 37.7749° N, 122.4194° W</span>
              </div>
              <img className="w-full h-full object-cover grayscale opacity-60 group-hover:grayscale-0 group-hover:opacity-80 transition-all duration-700 scale-110 group-hover:scale-100" alt="Global Hub Coordinates Map" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDGB3Yo6RWUx_CBn7S-dvX22doukjpQzF6-vfAW7llF2E9qbQ9XMZkMZ6L-D4k3TasU8mI6dK6HJ2ZW9LX_NrgjT7kJYSbr0uO95o-9LQoNNS0_n7QlUTSZW41fN9Z599nsXRD2fvthS-w95h4KGci88YyzbQxfMuhvzUJazbaHxueVm2eW9Ygk6XFVihYWJiv35-JQs82P6yUsIac2-bRWAUBTDA0RkUCU8afNv2dK7x_kK7w2R7r_cEm_JEQyzXXCBpbmi4UnRYh5" />
            </div>
          </div>
          
          {/* Right Column: Inquiry Registry Form */}
          <div className="lg:col-span-7 glass-panel p-10 rounded-lg border border-secondary-fixed-dim/20 relative overflow-hidden">
            <div className="absolute inset-0 bg-secondary-fixed-dim/5 pointer-events-none"></div>
            <div className="relative z-10">
              <div className="mb-10">
                <h2 className="font-headline-md text-headline-md text-primary mb-2">Inquiry Registry</h2>
                <p className="text-on-surface-variant">Complete the protocol below to initiate the architectural review for your vision deployment.</p>
              </div>
              
              <form className="space-y-8" onSubmit={(e) => e.preventDefault()}>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div className="relative">
                    <label className="font-label-caps text-label-caps text-outline-variant absolute -top-2.5 left-3 bg-background px-2">FULL_NAME</label>
                    <input className="w-full bg-transparent border border-outline-variant focus:border-secondary-fixed-dim focus:ring-0 rounded-lg p-4 font-mono-data text-white placeholder-white/10 transition-colors" placeholder="Your Full Name" type="text" />
                  </div>
                  <div className="relative">
                    <label className="font-label-caps text-label-caps text-outline-variant absolute -top-2.5 left-3 bg-background px-2">EMAIL_ADDRESS</label>
                    <input className="w-full bg-transparent border border-outline-variant focus:border-secondary-fixed-dim focus:ring-0 rounded-lg p-4 font-mono-data text-white placeholder-white/10 transition-colors" placeholder="your.email@organization.com" type="email" />
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div className="relative">
                    <label className="font-label-caps text-label-caps text-outline-variant absolute -top-2.5 left-3 bg-background px-2">ORGANIZATION</label>
                    <input className="w-full bg-transparent border border-outline-variant focus:border-secondary-fixed-dim focus:ring-0 rounded-lg p-4 font-mono-data text-white placeholder-white/10 transition-colors" placeholder="Your Organization's Name" type="text" />
                  </div>
                  <div className="relative">
                    <label className="font-label-caps text-label-caps text-outline-variant absolute -top-2.5 left-3 bg-background px-2">INFRASTRUCTURE_SCALE</label>
                    <select className="w-full bg-surface-dim border border-outline-variant focus:border-secondary-fixed-dim focus:ring-0 rounded-lg p-4 font-mono-data text-white appearance-none transition-colors">
                      <option>SELECT SCALE...</option>
                      <option>REGIONAL_CLUSTER</option>
                      <option>ENTERPRISE_CORE</option>
                      <option>GLOBAL_NETWORK</option>
                    </select>
                  </div>
                </div>
                
                <div className="relative">
                  <label className="font-label-caps text-label-caps text-outline-variant absolute -top-2.5 left-3 bg-background px-2">DEPLOYMENT_OBJECTIVES</label>
                  <textarea className="w-full bg-transparent border border-outline-variant focus:border-secondary-fixed-dim focus:ring-0 rounded-lg p-4 font-mono-data text-white placeholder-white/10 transition-colors" placeholder="Briefly describe your project or what you'd like to achieve with πX." rows={5}></textarea>
                </div>
                
                <div className="flex items-center gap-3 py-2">
                  <input className="w-5 h-5 rounded-sm border-outline-variant bg-transparent checked:bg-secondary-fixed-dim text-secondary-fixed-dim focus:ring-0 cursor-pointer transition-colors" id="nda" type="checkbox" />
                  <label className="font-mono-data text-xs text-on-surface-variant cursor-pointer select-none" htmlFor="nda">I REQUIRE A PRE-DISCLOSURE NON-DISCLOSURE AGREEMENT (NDA)</label>
                </div>
                
                <button className="w-full py-5 bg-white text-black font-bold font-label-caps text-label-caps tracking-widest hover:bg-secondary-fixed-dim transition-all active:scale-[0.98] flex justify-center items-center gap-4 group" type="submit">
                  INITIATE DEPLOYMENT REQUEST
                  <span className="material-symbols-outlined group-hover:translate-x-2 transition-transform">arrow_forward</span>
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
