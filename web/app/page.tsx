"use client";

import { Download, Ghost, FileText, Globe, Move, Shield, Zap } from "lucide-react";
import Link from "next/link";
import { motion } from "framer-motion";

export default function Home() {
  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 font-sans selection:bg-emerald-500/30">

      {/* Navbar */}
      <nav className="fixed top-0 w-full z-50 border-b border-white/5 bg-neutral-950/80 backdrop-blur-md">
        <div className="container mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3 font-bold text-xl tracking-tight">
            <img src="/logo.png" alt="VNNotes Logo" className="w-8 h-8 object-contain" />
            <span><span className="text-emerald-500">VN</span>Notes</span>
          </div>
          <div className="flex items-center gap-6 text-sm font-medium text-neutral-400">
            <Link href="#features" className="hover:text-white transition-colors">Features</Link>
            <Link href="/changelog" className="hover:text-white transition-colors">Changelog</Link>
            <Link
              href="https://github.com/bbqqvv/VNNotes-AnonymNotes/releases/latest"
              className="bg-white text-black px-4 py-2 rounded-full hover:bg-neutral-200 transition-colors"
            >
              Download
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-6 relative overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[500px] bg-emerald-500/20 blur-[120px] rounded-full pointer-events-none" />

        <div className="container mx-auto text-center relative z-10 max-w-4xl">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs font-medium text-emerald-400 mb-8"
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            v2.0.0 Stable is now live.
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="text-5xl md:text-7xl font-bold tracking-tight mb-8 bg-gradient-to-b from-white to-white/60 bg-clip-text text-transparent"
          >
            The Secret Weapon <br /> for Professional Flow.
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-lg md:text-xl text-neutral-400 mb-12 max-w-2xl mx-auto leading-relaxed"
          >
            The only workspace designed to be <span className="text-emerald-400 font-semibold italic text-emerald-400">completely invisible</span> to screen sharing.
            Bridge your workflow between Word, Web, and Notes—secretly.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
          >
            <Link
              href="https://github.com/bbqqvv/VNNotes-AnonymNotes/releases/latest/download/VNNotes_Setup.exe"
              className="group flex items-center gap-2 bg-white text-black px-8 py-4 rounded-full font-semibold hover:bg-neutral-200 transition-all hover:scale-105 active:scale-95"
            >
              <Download className="w-5 h-5 group-hover:animate-bounce" />
              Download for Windows
            </Link>
            <Link
              href="#features"
              className="px-8 py-4 rounded-full font-medium text-neutral-400 hover:text-white transition-colors"
            >
              Learn more
            </Link>
          </motion.div>

          {/* App Preview Mockup */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.4 }}
            className="mt-20 relative rounded-xl border border-white/10 bg-neutral-900/50 backdrop-blur-sm shadow-2xl overflow-hidden p-2"
          >
            <div className="absolute inset-0 bg-gradient-to-tr from-emerald-500/10 to-purple-500/10 pointer-events-none" />
            {/* Placeholder for screenshot - using a div for now to represent the UI */}
            <div className="aspect-[16/9] bg-neutral-900 rounded-lg flex items-center justify-center border border-white/5 overflow-hidden shadow-2xl">
              <video
                src="/video.mp4"
                autoPlay
                muted
                loop
                playsInline
                className="w-full h-full object-cover pointer-events-none"
              />
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="py-32 px-6 bg-neutral-900/30">
        <div className="container mx-auto max-w-6xl">
          <div className="text-center mb-20">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">Powerful. Private. Invisible.</h2>
            <p className="text-neutral-400">Everything you need to work secretly, built into one lightweight app.</p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            <FeatureCard
              icon={<Shield className="w-6 h-6 text-emerald-400" />}
              title="SQLite Core Architecture"
              description="Now powered by SQLite for massive performance and reliability. Your notes are stored in a professional database, ensuring zero data loss and lightning-fast search."
            />
            <FeatureCard
              icon={<Zap className="w-6 h-6 text-yellow-400" />}
              title="Smart Grid Workspace"
              description="Automatically split your notes into customizable grids. Perfect for multi-tasking, comparing scripts, and managing complex research projects in one view."
            />
            <FeatureCard
              icon={<Move className="w-6 h-6 text-orange-400" />}
              title="Scroll-In/Out Fluid Zoom"
              description="Seamlessly zoom in and out of your documents using your mouse scroll. Maintain legibility for long scripts while keeping the UI clean and focused."
            />
            <FeatureCard
              icon={<FileText className="w-6 h-6 text-blue-400" />}
              title="10+ Professional Themes"
              description="Choose from over 10 built-in themes to match your environment. From high-contrast dark modes to soft light themes, your workspace stays custom."
            />
            <FeatureCard
              icon={<Globe className="w-6 h-6 text-purple-400" />}
              title="Advanced Rich Formatting"
              description="Full control over text color, background highlights, and font sizes. Format your scripts exactly how you need them for perfect readability."
            />
            <FeatureCard
              icon={<Ghost className="w-6 h-6 text-red-500" />}
              title="Intelligent Invisibility"
              description="100% invisible to Zoom and Teams. Anti-capture technology now stays off by default, only activating when you need it for maximum efficiency."
            />
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 px-6 text-center">
        <div className="container mx-auto max-w-3xl">
          <h2 className="text-4xl font-bold mb-8">Ready to work in stealth?</h2>
          <p className="text-neutral-400 mb-10 text-lg">
            Join thousands of professionals who value their privacy and workflow.
            <br />Free and open source.
          </p>
          <Link
            href="https://github.com/bbqqvv/VNNotes-AnonymNotes/releases/latest/download/VNNotes_Setup.exe"
            className="inline-flex items-center gap-2 bg-emerald-600 text-white px-8 py-4 rounded-full font-bold hover:bg-emerald-500 transition-all hover:scale-105 shadow-lg shadow-emerald-500/20"
          >
            <Download className="w-5 h-5" />
            Download v2.0.0
          </Link>
          <p className="mt-6 text-sm text-neutral-600">
            Windows 10/11 • 64-bit • Installer (~121MB)
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-12 text-center text-neutral-500 text-sm font-light">
        <p>© 2026 VNNotes. Built for privacy.</p>
        <p className="mt-1 text-neutral-600">Copyright © VTech Digital Solution</p>
        <div className="flex justify-center gap-6 mt-6">
          <Link href="https://github.com/bbqqvv/VNNotes-AnonymNotes" className="hover:text-white">GitHub</Link>
          <Link href="/changelog" className="hover:text-white">Changelog</Link>
          {/* <Link href="/privacy" className="hover:text-white">Privacy</Link> */}
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode, title: string, description: string }) {
  return (
    <div className="p-6 rounded-xl border border-white/5 bg-white/5 hover:bg-white/10 transition-colors">
      <div className="mb-4 p-3 rounded-lg bg-black/30 w-fit">{icon}</div>
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      <p className="text-neutral-400 leading-relaxed">{description}</p>
    </div>
  );
}
