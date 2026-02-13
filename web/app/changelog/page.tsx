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
                    {/* Version 1.0.0 */}
                    <ChangelogEntry
                        version="v1.0.0"
                        date="February 13, 2026"
                        isLatest={true}
                    >
                        <ul className="list-disc list-inside space-y-3 text-neutral-300">
                            <li><strong className="text-white">Phantom Invisibility:</strong> Advanced Anti-Capture technology to bypass Zoom, Teams, and OBS.</li>
                            <li><strong className="text-white">Multi-Document Workspace:</strong> Manage multiple notes and scripts simultaneously with an intuitive tab system.</li>
                            <li><strong className="text-white">Ultra-Hub Dock:</strong> Integrated Mini-Browser and Smart-Paste Clipboard for lethal productivity.</li>
                            <li><strong className="text-white">Meeting Master Teleprompter:</strong> Professional floating prompts for high-stakes presentations.</li>
                            <li><strong className="text-white">Standalone Private Vault:</strong> 100% local data storage with zero telemetry or tracking.</li>
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
                    <Tag className="w-3 h-3 text-emerald-400" />
                    <span className="font-mono font-bold text-emerald-400">{version}</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-neutral-500 font-mono uppercase tracking-wider">
                    <Calendar className="w-3 h-3" />
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
