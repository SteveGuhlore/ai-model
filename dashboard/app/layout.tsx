import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/nav";

export const metadata: Metadata = {
  title: "Creator Studio",
  description: "SFW multi-persona content studio",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="flex min-h-screen">
          <Nav />
          <main className="flex-1 px-8 py-6 max-w-6xl">{children}</main>
        </div>
      </body>
    </html>
  );
}
