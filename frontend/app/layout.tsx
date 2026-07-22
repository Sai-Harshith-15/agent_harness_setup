import "./globals.css";
import Nav from "./nav";
import { Inter } from "next/font/google";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata = { title: "Mission Control" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable} suppressHydrationWarning>
      <body suppressHydrationWarning className="font-sans antialiased min-h-screen flex flex-col md:flex-row selection:bg-accent/30">
        <Nav />
        <div className="flex-1 overflow-x-hidden max-h-screen overflow-y-auto">
          {children}
        </div>
      </body>
    </html>
  );
}
