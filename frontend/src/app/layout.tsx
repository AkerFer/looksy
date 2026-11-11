import type { Metadata } from "next";
import { SessionProvider } from "@/components/core";
import "./globals.css";
export const metadata: Metadata = {
  title: "Looksy — ваш гардероб, новые возможности",
  description: "Личный цифровой гардероб и образы из ваших настоящих вещей.",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <body>
        <SessionProvider>{children}</SessionProvider>
      </body>
    </html>
  );
}
