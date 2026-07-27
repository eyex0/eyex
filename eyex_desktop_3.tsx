// HEADER
<header className="fixed top-0 w-full z-50 flex justify-between items-center px-margin-desktop h-20 bg-background/80 dark:bg-background/80 backdrop-blur-xl border-b border-white/10">
<div className="flex items-center gap-3">
<span className="material-symbols-outlined text-primary text-[28px]" data-icon="visibility">visibility</span>
<span className="font-headline-md text-headline-md font-bold tracking-tighter text-primary">EyeX</span>
</div>
<nav className="hidden md:flex gap-10">
<a className="font-label-caps text-label-caps text-on-surface-variant hover:text-secondary-container transition-colors" href="#">Vision Hero</a>
<a className="font-label-caps text-label-caps text-primary border-b-2 border-secondary-fixed-dim pb-1" href="#">Solutions</a>
<a className="font-label-caps text-label-caps text-on-surface-variant hover:text-secondary-container transition-colors" href="#">Analytics</a>
<a className="font-label-caps text-label-caps text-on-surface-variant hover:text-secondary-container transition-colors" href="#">Contact</a>
</nav>
<button className="material-symbols-outlined text-primary hover:text-secondary-container transition-colors" data-icon="menu">menu</button>
</header>

// MAIN
<main className="pt-20">
{/* Hero Section */}
<section className="relative h-[819px] flex items-center justify-center overflow-hidden px-margin-desktop">

<div className="relative z-10 text-center max-w-4xl">
<div className="flex items-center justify-center gap-2 mb-6">
<span className="w-2 h-2 rounded-full bg-secondary-fixed-dim animate-pulse"></span>
<span className="font-mono-data text-mono-data text-secondary-fixed-dim tracking-[0.2em] uppercase">Status: Core Active</span>
</div>
<h1 className="font-display-lg text-display-lg text-primary mb-8 tracking-tighter">Advanced Optical Intelligence</h1>
<p className="font-body-lg text-body-lg text-on-surface-variant max-w-2xl mx-auto mb-10">
                    Precision-engineered vision systems designed for the next era of high-performance automation, healthcare, and navigation. 
                </p>
<div className="flex gap-4 justify-center">
<button className="px-8 py-4 bg-primary text-background font-label-caps text-label-caps rounded-lg hover:bg-secondary-fixed-dim transition-all glow-cyan uppercase">Deploy Module</button>
<button className="px-8 py-4 border border-outline-variant text-primary font-label-caps text-label-caps rounded-lg hover:bg-white/5 transition-all uppercase">View SDK</button>
</div>
</div>
<div className="absolute bottom-0 left-0 w-full h-32 bg-gradient-to-t from-background to-transparent"></div>
</section>
{/* Solution Sections (Alternating) */}
{/* Autonomous Navigation */}
<section className="py-24 px-margin-desktop">
<div className="grid md:grid-cols-2 gap-gutter items-center">
<div className="glass-card rounded-xl overflow-hidden aspect-video relative group">
<img className="w-full h-full object-cover grayscale brightness-75 group-hover:scale-105 transition-transform duration-700" data-alt="A futuristic autonomous vehicle sensor array visualizing a complex urban environment in high-contrast cyan and white lidar pulses. The scene is set in a deep midnight black world, with digital wireframes of buildings and pedestrians glowing against the darkness. The aesthetic is technical and precise, emphasizing speed and real-time computation." src="https://lh3.googleusercontent.com/aida-public/AB6AXuB1xW5QfxSopjoUoXD3ctbTkimGN7YIuEhfFdQkPPh4EGHR2VfxqitDtvNFMq__GZN92stNHRij_etBgUQSNFMYpKrPFHC-LwW6pLnI2HqKA5QLwbo_y9jBXbB8_xehb33JBEDmJ41mWixebIMzYPhCpF48zEIGQk0R9ouBuqhAlbxKR2bHE9PXVs6usHTS0DHjPCvpWGMhVns0EQDHnhyeKbgsocxMvKdpJWpWnYH3tpohyo7VXAhS06pg3-1X7MHUjshdKyNxDrnC"/>
<div className="absolute inset-0 bg-gradient-to-t from-background/80 to-transparent"></div>
<div className="absolute bottom-6 left-6 flex items-center gap-2">
<span className="material-symbols-outlined text-secondary-fixed-dim" data-icon="explore">explore</span>
<span className="font-mono-data text-mono-data text-white">MODULE_AUTO_NAV_V4</span>
</div>
</div>
<div className="pl-12">
<span className="font-label-caps text-label-caps text-secondary-fixed-dim block mb-4 uppercase">Navigation Systems</span>
<h2 className="font-headline-md text-headline-md text-primary mb-6">Autonomous Navigation</h2>
<p className="font-body-md text-body-md text-on-surface-variant mb-8 leading-relaxed">
                        EyeX provides sub-millimeter spatial awareness for autonomous platforms. Our proprietary optical-flow algorithms enable high-speed processing in unpredictable environments, from aerial drones to terrestrial logistics fleets.
                    </p>
<ul className="space-y-4">
<li className="flex items-start gap-3 border-b border-white/5 pb-4">
<span className="material-symbols-outlined text-secondary-fixed-dim" data-icon="check_circle">check_circle</span>
<span className="font-body-md text-on-surface">Ultra-low latency inference ( &lt; 2ms )</span>
</li>
<li className="flex items-start gap-3 border-b border-white/5 pb-4">
<span className="material-symbols-outlined text-secondary-fixed-dim" data-icon="check_circle">check_circle</span>
<span className="font-body-md text-on-surface">Adverse weather pattern compensation</span>
</li>
</ul>
</div>
</div>
</section>
{/* Healthcare Diagnostics */}
<section className="py-24 px-margin-desktop bg-surface-container-lowest/30">
<div className="grid md:grid-cols-2 gap-gutter items-center">
<div className="order-2 md:order-1 pr-12">
<span className="font-label-caps text-label-caps text-secondary-fixed-dim block mb-4 uppercase">Bio-Imaging</span>
<h2 className="font-headline-md text-headline-md text-primary mb-6">Healthcare Diagnostics</h2>
<p className="font-body-md text-body-md text-on-surface-variant mb-8 leading-relaxed">
                        Precision diagnostics powered by hyper-spectral vision. Our sensors identify micro-anomalies in tissue structures before they become clinically visible, integrating directly into robotic surgical suites and remote triage units.
                    </p>
<div className="grid grid-cols-2 gap-4">
<div className="glass-card p-4 rounded">
<div className="text-secondary-fixed-dim font-headline-md text-[24px] mb-1">99.8%</div>
<div className="text-on-surface-variant font-label-caps text-[10px] uppercase">Accuracy Rate</div>
</div>
<div className="glass-card p-4 rounded">
<div className="text-secondary-fixed-dim font-headline-md text-[24px] mb-1">REAL-TIME</div>
<div className="text-on-surface-variant font-label-caps text-[10px] uppercase">Analysis Engine</div>
</div>
</div>
</div>
<div className="order-1 md:order-2 glass-card rounded-xl overflow-hidden aspect-video relative group">
<img className="w-full h-full object-cover grayscale brightness-90 group-hover:scale-105 transition-transform duration-700" data-alt="Close-up of a high-tech medical imaging display showing a microscopic cell structure in luminescent white and electric blue. The interface features surgical overlays and HUD data points in a minimalist Swiss style. The background is a clean matte black, suggesting a sophisticated sterile environment with high-end optical equipment." src="https://lh3.googleusercontent.com/aida-public/AB6AXuAJvzyx0gyqdbn7aVCseQNF58kXcvQ0ePZUHUyWm3AQ2-IqOH7HzmfWdihqnihwhkZeBeNegRl7WOrooch6WUyTA4jrKNGFnH5FMZy_HgdGMrGgjT2ymnoNowcsT19iW_Ux8pkSFETQfWBkuvce-uiQ6jsO13xlExgpMWPcdACcjYr0mHfKdCbVMFJvuVqYi3U5Csn4bspBdRwIL9SmfQpsu12k09Uu1Df54CZFtIc346NtCuyxj5warpMbaaCggh840xWg2Xfvdvm5"/>
<div className="absolute inset-0 bg-gradient-to-t from-background/80 to-transparent"></div>
<div className="absolute bottom-6 left-6 flex items-center gap-2">
<span className="material-symbols-outlined text-secondary-fixed-dim" data-icon="biotech">biotech</span>
<span className="font-mono-data text-mono-data text-white">MODULE_BIO_VIS_X1</span>
</div>
</div>
</div>
</section>
{/* Industrial Automation */}
<section className="py-24 px-margin-desktop">
<div className="grid md:grid-cols-2 gap-gutter items-center">
<div className="glass-card rounded-xl overflow-hidden aspect-video relative group">
<img className="w-full h-full object-cover grayscale brightness-75 group-hover:scale-105 transition-transform duration-700" data-alt="A wide shot of a dark, automated industrial warehouse where robotic arms are highlighted by sharp shafts of white light. Digital tracking squares and orange-tinted heatmaps overlap the machinery, visualizing the AI's sight path. The color scheme is predominantly black with white and secondary cyan accents, reflecting a technical luxury aesthetic." src="https://lh3.googleusercontent.com/aida-public/AB6AXuA-3O9TDZYWGe4wjXu_clAgqGFnd-a85V-xrDtY4u4Co7qvEmSDbMr74-nA6VFp5zS4RM8nKUeypBJo74XUPwlO3MqB1MWe_icIo0Y-q_u0pgXOrPUGPpJ35pjCcyJqUSCziSsKFywGmtVIJt3nWDGgXQQIjXcF2HGuFqmkqvIv4sSKa5rdgasK4rVTa2hVwLsNEPSx5LTp8eWTtDD6f5HwHBFYDUWxkPNIHYAkBVraIq2EbNX87efFEH-h09ZoIpKMvWIOPaZDtOMV"/>
<div className="absolute inset-0 bg-gradient-to-t from-background/80 to-transparent"></div>
<div className="absolute bottom-6 left-6 flex items-center gap-2">
<span className="material-symbols-outlined text-secondary-fixed-dim" data-icon="precision_manufacturing">precision_manufacturing</span>
<span className="font-mono-data text-mono-data text-white">MODULE_IND_PROC_S9</span>
</div>
</div>
<div className="pl-12">
<span className="font-label-caps text-label-caps text-secondary-fixed-dim block mb-4 uppercase">Robotic Logistics</span>
<h2 className="font-headline-md text-headline-md text-primary mb-6">Industrial Automation</h2>
<p className="font-body-md text-body-md text-on-surface-variant mb-8 leading-relaxed">
                        Scale production with machine vision that never blinks. From defect detection on high-speed assembly lines to collaborative robotics in smart factories, EyeX ensures absolute consistency in every cycle.
                    </p>
<button className="group flex items-center gap-3 text-primary font-label-caps text-label-caps uppercase tracking-widest">
                        Technical Datasheet 
                        <span className="material-symbols-outlined group-hover:translate-x-2 transition-transform" data-icon="arrow_forward">arrow_forward</span>
</button>
</div>
</div>
</section>
{/* Developer Integration Code Block */}
<section className="py-24 bg-surface-dim">
<div className="max-w-6xl mx-auto px-margin-mobile md:px-0">
<div className="mb-12 text-center">
<h2 className="font-headline-md text-headline-md text-primary mb-4">Developer-First Integration</h2>
<p className="font-body-md text-on-surface-variant">Three lines of code to initialize the future of optical compute.</p>
</div>
<div className="rounded-xl overflow-hidden border border-outline-variant bg-[#050505] shadow-2xl">
<div className="flex items-center justify-between px-6 py-4 bg-[#111111] border-b border-outline-variant">
<div className="flex gap-2">
<div className="w-3 h-3 rounded-full bg-error/40"></div>
<div className="w-3 h-3 rounded-full bg-surface-tint/40"></div>
<div className="w-3 h-3 rounded-full bg-secondary-fixed-dim/40"></div>
</div>
<div className="text-on-surface-variant font-mono-data text-[12px]">pix_main.py</div>
<button className="material-symbols-outlined text-on-surface-variant hover:text-primary transition-colors text-[18px]" data-icon="content_copy">content_copy</button>
</div>
<div className="p-8 font-mono-data text-mono-data text-[14px] leading-relaxed overflow-x-auto">
<pre className="text-[#888]"><code><span className="text-secondary-fixed-dim">import</span> pix_core <span className="text-secondary-fixed-dim">as</span> ex

<span className="text-[#555]"># Initialize optical cluster with neural prioritization</span>
cluster = ex.VisionCluster(config=<span className="text-[#00eefc]">"ultra_low_latency"</span>)

<span className="text-[#555]"># Deploy diagnostic module to active feed</span>
module = cluster.deploy(<span className="text-secondary-fixed-dim">"BIO_VIS_X1"</span>)

<span className="text-[#555]"># Stream inference results at 240fps</span>
<span className="text-secondary-fixed-dim">while</span> cluster.is_active:
    telemetry = module.get_telemetry()
    <span className="text-primary">print</span>(f<span className="text-[#00eefc]">"Inference: {telemetry.accuracy}% | Latency: {telemetry.ms}ms"</span>)</code></pre>
</div>
</div>
</div>
</section>
{/* Engineering Specifications Table */}
<section className="py-24 px-margin-desktop">
<div className="mb-12">
<div className="line-detail mb-8"></div>
<h2 className="font-headline-md text-headline-md text-primary tracking-tight">Engineering Specifications</h2>
</div>
<div className="overflow-x-auto">
<table className="w-full text-left border-collapse">
<thead>
<tr className="border-b-2 border-primary">
<th className="py-6 font-label-caps text-label-caps text-on-surface-variant uppercase tracking-widest">Parameter</th>
<th className="py-6 font-label-caps text-label-caps text-on-surface-variant uppercase tracking-widest">Standard Core</th>
<th className="py-6 font-label-caps text-label-caps text-on-surface-variant uppercase tracking-widest">Quantum Ultra</th>
<th className="py-6 font-label-caps text-label-caps text-on-surface-variant uppercase tracking-widest">Enterprise Hub</th>
</tr>
</thead>
<tbody className="font-mono-data text-mono-data">
<tr className="border-b border-white/5 hover:bg-white/[0.02] transition-colors group">
<td className="py-6 text-on-surface-variant">Optical Resolution</td>
<td className="py-6 text-primary">8K Raw</td>
<td className="py-6 text-primary">12K Hyper</td>
<td className="py-6 text-secondary-fixed-dim">Dynamic Array</td>
</tr>
<tr className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
<td className="py-6 text-on-surface-variant">Inference Speed</td>
<td className="py-6 text-primary">120 FPS</td>
<td className="py-6 text-primary">480 FPS</td>
<td className="py-6 text-secondary-fixed-dim">Sub-ms Cluster</td>
</tr>
<tr className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
<td className="py-6 text-on-surface-variant">Spectral Range</td>
<td className="py-6 text-primary">RGB + IR</td>
<td className="py-6 text-primary">Full Hyper-S</td>
<td className="py-6 text-secondary-fixed-dim">User Defined</td>
</tr>
<tr className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
<td className="py-6 text-on-surface-variant">Neural Core Count</td>
<td className="py-6 text-primary">128 TOPS</td>
<td className="py-6 text-primary">512 TOPS</td>
<td className="py-6 text-secondary-fixed-dim">Scalable Hub</td>
</tr>
</tbody>
</table>
</div>
</section>
</main>

// FOOTER
<footer className="w-full py-12 px-margin-desktop flex flex-col md:flex-row justify-between items-center gap-4 bg-background border-t border-white/5">
<div className="flex flex-col items-center md:items-start gap-2">
<span className="font-label-caps text-label-caps text-primary uppercase tracking-widest">EyeX Core</span>
<span className="font-mono-data text-mono-data text-on-surface-variant text-[10px]">© 2024 EYEX CORE. ALL RIGHTS RESERVED.</span>
</div>
<div className="flex gap-8">
<a className="font-mono-data text-mono-data text-on-surface-variant hover:text-secondary-fixed-dim underline transition-all" href="#">Documentation</a>
<a className="font-mono-data text-mono-data text-on-surface-variant hover:text-secondary-fixed-dim underline transition-all" href="#">Privacy</a>
<a className="font-mono-data text-mono-data text-on-surface-variant hover:text-secondary-fixed-dim underline transition-all" href="#">API</a>
<a className="font-mono-data text-mono-data text-on-surface-variant hover:text-secondary-fixed-dim underline transition-all" href="#">Terms</a>
</div>
</footer>