import Link from "next/link";
import { ArrowLeft, Calendar, Tag } from "lucide-react";

export default function Changelog() {
    return (
        <div className="min-h-screen bg-neutral-950 text-neutral-100 font-sans selection:bg-emerald-500/30 py-20 px-6">
            <div className="container mx-auto max-w-3xl">
                <div className="mb-12">
                    <Link href="/" className="inline-flex items-center gap-2 text-neutral-400 hover:text-white mb-8 transition-colors">
                        <ArrowLeft className="w-4 h-4" /> Back to Home
                    </Link>
                    <h1 className="text-4xl font-bold mb-4">Changelog</h1>
                    <p className="text-neutral-400">Latest updates and improvements to VNNotes.</p>
                </div>

                <div className="space-y-12">
                    {/* Version 2.0.1 */}
                    <ChangelogEntry
                        version="v2.0.1"
                        date="February 26, 2026"
                        isLatest={true}
                    >
                        <ul className="list-disc list-inside space-y-3 text-neutral-300">
                            <li><strong className="text-white">Security – Stealth Mode Upgrade:</strong> Super Stealth mode now completely hides the application from the Windows Taskbar and Alt+Tab menu dynamically, ensuring absolute privacy when active.</li>
                            <li><strong className="text-white">Security – Locked Folder Mentions:</strong> the `@mention` autocomplete menu no longer exposes the titles of notes stored inside Locked Vaults, preventing accidental privacy leaks.</li>
                            <li><strong className="text-white">Security – Guarded Internal Links:</strong> Clicking an internal `vnnote://` link pointing to a locked document now actively prompts for the correct Vault Password before granting access.</li>
                            <li><strong className="text-white">Fixed – Core Platform Zoom Integration:</strong> Completely rewrote the document zooming mechanism. Zooming via `Ctrl`+`Scroll` now relies on low-level Qt PointSize scaling, resolving a major crash triggered by pixel-level font rendering on fresh notes.</li>
                        </ul>
                    </ChangelogEntry>

                    {/* Version 2.0.0 */}
                    <ChangelogEntry
                        version="v2.0.0"
                        date="February 25, 2026"
                        isLatest={false}
                    >
                        <ul className="list-disc list-inside space-y-3 text-neutral-300">
                            <li><strong className="text-white">Big Update – Core Architecture:</strong> Successfully migrated the entire backend to <strong className="text-emerald-400">SQLite</strong> for military-grade data reliability and blazing-fast search speeds.</li>
                            <li><strong className="text-white">UI Evolution:</strong> Reimagined user interface with a more intuitive and friendly design, focused on professional focus and ease of use.</li>
                            <li><strong className="text-white">Auto-Grid Layout:</strong> New feature to automatically divide your notes into smart grids, perfect for multi-tasking and comparing research data.</li>
                            <li><strong className="text-white">Improved Prompter:</strong> Enhanced teleprompter logic with smoother scrolling and better visibility controls for high-stakes presentations.</li>
                            <li><strong className="text-white">Smarter Sidebar:</strong> Redesigned sidebar with intelligent organization and faster navigation across your entire note library.</li>
                            <li><strong className="text-white">10+ Built-in Themes:</strong> Personalize your workspace with over 10 professionally curated themes, from deep space dark to clean paper light.</li>
                            <li><strong className="text-white">Advanced Rich Text:</strong> Complete control over your content with new options for text color, background highlights (text-bg), and granular font size adjustments.</li>
                            <li><strong className="text-white">Fluid Zoom:</strong> Integrated scroll-in/out (Zoom) functionality for effortless reading and navigation of long documents.</li>
                            <li><strong className="text-white">Controlled Invisibility:</strong> Improved Anti-Capture mode now stays off by default and only activates when you explicitly need it, saving system resources.</li>
                            <li><strong className="text-white">Performance & Fixes:</strong> Massive code logic refactoring for a "butter-smooth" experience. Fixed dozens of micro-bugs including the redundant note restoration glitch.</li>
                        </ul>
                    </ChangelogEntry>

                    {/* Version 1.1.1 */}
                    <ChangelogEntry
                        version="v1.1.1"
                        date="February 20, 2026"
                        isLatest={false}
                    >
                        <ul className="list-disc list-inside space-y-3 text-neutral-300">
                            <li><strong className="text-white">Fixed – Browser Persistence:</strong> Resolved a critical race condition where rapid toggling of the built-in browser via shortcut caused immediate window termination.</li>
                            <li><strong className="text-white">Fixed – Context Menu Collision:</strong> Eliminated layout displacement artifacts triggered by the native browser context menu, ensuring UI alignment integrity.</li>
                            <li><strong className="text-white">Improved – Fault-Tolerance:</strong> Implemented automatic database integrity checks and recovery protocols to prevent startup failure following improper application termination.</li>
                            <li><strong className="text-white">Improved – Windows Filesystem Integration:</strong> Optimized file-locking mechanisms for improved compatibility with real-time antivirus scanning on Windows 10/11.</li>
                            <li><strong className="text-white">Styled – Dark Mode Consistency:</strong> Corrected theme mismatch in the Search/Find interface; input elements now dynamically inherit the active dark mode palette.</li>
                        </ul>
                    </ChangelogEntry>

                    {/* Version 1.1.0 */}
                    <ChangelogEntry
                        version="v1.1.0"
                        date="February 20, 2026"
                        isLatest={false}
                    >
                        <ul className="list-disc list-inside space-y-3 text-neutral-300">
                            <li><strong className="text-white">New – Intelligent Sidebar:</strong> Introduced a high-performance, collapsible navigation tree supporting nested hierarchies and rapid session switching.</li>
                            <li><strong className="text-white">New – Productivity Toolbar:</strong> Integrated a centralized action header for immediate access to document creation, global search, and UI state management.</li>
                            <li><strong className="text-white">Optimized – Core Engine:</strong> Refactored the internal signals-and-slots architecture, resulting in tangible reductions in CPU overhead and faster UI response times.</li>
                            <li><strong className="text-white">Improved – Distribution Layout:</strong> Standardized the installation directory structure to follow professional software conventions, ensuring system resources remain encapsulated.</li>
                            <li><strong className="text-white">Styled – OS Branding:</strong> Full integration with the Windows shell; high-definition iconography now renders correctly in the Taskbar, Start Menu, and System Tray.</li>
                        </ul>
                    </ChangelogEntry>

                    {/* Version 1.0.0 */}
                    <ChangelogEntry
                        version="v1.0.0"
                        date="February 13, 2026"
                        isLatest={false}
                    >
                        <ul className="list-disc list-inside space-y-3 text-neutral-300">
                            <li><strong className="text-white">Anti-Capture Engine:</strong> Proprietary hardware-accelerated invisibility mode for seamless operation during Zoom, Microsoft Teams, and OBS recording.</li>
                            <li><strong className="text-white">Professional Workspace:</strong> Multi-tabbed document architecture designed for high-stakes presentations and real-time script management.</li>
                            <li><strong className="text-white">Integrated Ultra-Hub:</strong> A combined toolset featuring a low-latency mini-browser and a smart-paste clipboard for instantaneous data retrieval.</li>
                            <li><strong className="text-white">Strategic Teleprompter:</strong> Professional-grade floating overlay with transparency controls, optimized for maintaining eye contact during video delivery.</li>
                            <li><strong className="text-white">Privacy-First Storage:</strong> 100% localized data encryption with zero external dependencies, cloud synchronization, or telemetry tracking.</li>
                        </ul>
                    </ChangelogEntry>
                </div>

                {/* Footer */}
                <footer className="mt-20 pt-12 border-t border-white/5 text-center text-neutral-500 text-sm font-light">
                    <p>© 2026 VNNotes. Built for privacy.</p>
                    <p className="mt-1 text-neutral-600">Copyright © VTech Digital Solution</p>
                </footer>
            </div>
        </div>
    );
}

function ChangelogEntry({ version, date, children, isLatest }: { version: string, date: string, children: React.ReactNode, isLatest?: boolean }) {
    return (
        <div className="relative pl-8 border-l border-white/10 pb-8 last:pb-0">
            <div className="absolute -left-[5px] top-0 h-2.5 w-2.5 rounded-full bg-neutral-800 border border-white/20"></div>

            <div className="flex items-center gap-4 mb-4">
                <div className="flex items-center gap-2 bg-white/5 border border-white/10 px-3 py-1 rounded-md">
                    <span className="font-mono font-bold text-emerald-400">{version}</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-neutral-500 font-mono uppercase tracking-wider">
                    {date}
                </div>
                {isLatest && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 uppercase tracking-wide">
                        Latest
                    </span>
                )}
            </div>

            <div className="prose prose-invert prose-emerald max-w-none">
                {children}
            </div>
        </div>
    );
}
