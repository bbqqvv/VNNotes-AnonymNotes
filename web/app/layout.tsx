import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://stealthassist.vercel.app"),
  title: "VNNotes - The Invisible Workspace",
  description: "Privacy-focused note-taking and browsing tool for professionals. Invisible to screen sharing, local storage only.",
  icons: {
    icon: "/favicon.ico",
    shortcut: "/favicon.ico",
    apple: "/icon-192.png",
  },
  openGraph: {


    title: "VNNotes - The Invisible Workspace",
    description: "Privacy-focused note-taking and browsing tool for professionals.",
    url: "https://stealthassist.vercel.app",
    siteName: "VNNotes",
    images: [
      {
        url: "/meta.png",
        width: 1200,
        height: 630,
        alt: "VNNotes Preview",
      },
    ],
    locale: "en_US",
    type: "website",
  },
};



export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
