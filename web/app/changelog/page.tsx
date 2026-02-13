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
                    <p className="text-neutral-400">Latest updates and improvements to Stealth Assist.</p>
                </div>

                <div className="space-y-12">
                    {/* Version 1.5.1 */}
                    <ChangelogEntry
                        version="v1.5.1"
                        date="February 12, 2026"
                        isLatest={true}
                    >
                        <ul className="list-disc list-inside space-y-2 text-neutral-300">
                            <li><strong className="text-white">New:</strong> Fixed Application Icon not showing in title bar.</li>
                            <li><strong className="text-white">New:</strong> App now starts Maximized by default for better visibility.</li>
                            <li><strong className="text-white">Improvement:</strong> Enhanced drag-and-drop stability.</li>
                        </ul>
                    </ChangelogEntry>

                    {/* Version 1.5.0 */}
                    <ChangelogEntry
                        version="v1.5.0"
                        date="February 12, 2026"
                    >
                        <ul className="list-disc list-inside space-y-2 text-neutral-300">
                            <li><strong className="text-white">Feature:</strong> <strong>Image Alignment</strong>. Right-click images to align Left, Center, or Right.</li>
                            <li><strong className="text-white">Feature:</strong> <strong>Drag & Drop</strong>. Move images and text within the editor naturally.</li>
                            <li><strong className="text-white">UI:</strong> Removed legacy drag-to-resize handles in favor of cleaner interactions.</li>
                        </ul>
                    </ChangelogEntry>

                    {/* Version 1.4.0 */}
                    <ChangelogEntry
                        version="v1.4.0"
                        date="February 10, 2026"
                    >
                        <ul className="list-disc list-inside space-y-2 text-neutral-300">
                            <li><strong className="text-white">Feature:</strong> Double-click images to resize them precisely via dialog.</li>
                            <li><strong className="text-white">Feature:</strong> Right-click Context Menu for images (Resize, Reset, Save As).</li>
                            <li><strong className="text-white">Fix:</strong> Resolved issue where images would disappear after resizing.</li>
                        </ul>
                    </ChangelogEntry>

                    {/* Version 1.3.0 */}
                    <ChangelogEntry
                        version="v1.3.0"
                        date="January 25, 2026"
                    >
                        <ul className="list-disc list-inside space-y-2 text-neutral-300">
                            <li><strong className="text-white">Feature:</strong> Ghost Mode (Opacity Slider).</li>
                            <li><strong className="text-white">Feature:</strong> Auto-Update system checks GitHub Releases.</li>
                        </ul>
                    </ChangelogEntry>
                </div>
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
