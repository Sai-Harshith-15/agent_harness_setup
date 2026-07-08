import Nav from "./nav";

export const metadata = { title: "Mission Control" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "ui-sans-serif, system-ui", margin: 0, background: "#0b0f17", color: "#e6edf3" }}>
        <Nav />
        {children}
      </body>
    </html>
  );
}
