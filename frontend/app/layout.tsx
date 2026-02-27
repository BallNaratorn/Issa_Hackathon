import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "Issa Compass Chat",
  description: "Self-learning visa assistant chat UI",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-950 text-slate-50 antialiased">
        <div className="min-h-screen flex items-center justify-center">
          {children}
        </div>
      </body>
    </html>
  );
}

