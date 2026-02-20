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
                    {/* Version 1.1.1 */}
                    <ChangelogEntry
                        version="v1.1.1"
                        date="February 20, 2026"
                        isLatest={true}
                    >
                        <ul className="list-disc list-inside space-y-3 text-neutral-300">
                            <li><strong className="text-white">Sửa lỗi – Trình duyệt biến mất:</strong> Trước đây nhấn <kbd className="bg-white/10 px-1 rounded text-xs">Ctrl+Shift+Space</kbd> hai lần liên tiếp khiến cửa sổ trình duyệt tích hợp biến mất hoàn toàn. Lỗi này đã được sửa.</li>
                            <li><strong className="text-white">Sửa lỗi – Giao diện bị vỡ khi click chuột phải:</strong> Click chuột phải vào trình duyệt đôi khi làm bố cục giao diện bị lệch. Đã được khắc phục hoàn toàn.</li>
                            <li><strong className="text-white">Sửa lỗi – App bị crash khi khởi động lại:</strong> Một số trường hợp tắt app đột ngột hoặc máy tính bị giật có thể khiến dữ liệu lưu bị hỏng, gây crash ở lần mở tiếp theo. App giờ tự động phát hiện và phục hồi mà không mất dữ liệu quan trọng.</li>
                            <li><strong className="text-white">Sửa lỗi – Ô tìm kiếm bị trắng ở chế độ tối:</strong> Khi dùng giao diện tối (dark mode), ô Search/Find hiển thị nền trắng trông rất lạc quẻ. Đã được sửa để hiển thị đúng màu tối.</li>
                            <li><strong className="text-white">Cải thiện – Lưu dữ liệu ổn định hơn trên Windows:</strong> Cơ chế lưu file được nâng cấp để hoạt động tốt hơn trên Windows 10/11, đặc biệt với các máy có phần mềm diệt virus hoặc bảo mật chạy ngầm — giảm nguy cơ mất dữ liệu khi lưu.</li>
                        </ul>
                    </ChangelogEntry>

                    {/* Version 1.1.0 */}
                    <ChangelogEntry
                        version="v1.1.0"
                        date="February 20, 2026"
                        isLatest={false}
                    >
                        <ul className="list-disc list-inside space-y-3 text-neutral-300">
                            <li><strong className="text-white">New Sidebar:</strong> Brand-new collapsible note tree sidebar for fast file navigation — create folders, notes, and switch between them instantly.</li>
                            <li><strong className="text-white">Quick Actions Toolbar:</strong> One-click shortcuts for all common actions (new note, new folder, collapse all, refresh) right in the sidebar header.</li>
                            <li><strong className="text-white">Performance Optimization:</strong> Major refactor of core architecture — faster startup, smoother tab switching, and lower memory usage.</li>
                            <li><strong className="text-white">Stability Fix:</strong> Resolved a crash on launch caused by missing QtWebEngine dependencies after install.</li>
                            <li><strong className="text-white">Clean Install Experience:</strong> Resources folder is now hidden post-install for a professional directory layout.</li>
                            <li><strong className="text-white">Branding Polish:</strong> VTech icon now correctly displayed in the Windows taskbar and Start Menu via AppUserModelID.</li>
                        </ul>
                    </ChangelogEntry>

                    {/* Version 1.0.0 */}
                    <ChangelogEntry
                        version="v1.0.0"
                        date="February 13, 2026"
                        isLatest={false}
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
