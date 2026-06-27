import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Orator — Government Content Studio",
  description:
    "Draft speeches and press releases that are stylistically authentic, factually airtight, and fully source-traceable.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
