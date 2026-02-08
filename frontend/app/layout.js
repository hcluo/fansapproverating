export const metadata = {
  title: 'FansApprove Rating',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body style={{fontFamily: 'sans-serif', margin: '1rem 2rem'}}>{children}</body>
    </html>
  );
}
