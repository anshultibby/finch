import type { Metadata } from 'next'
import { DM_Sans, Space_Grotesk } from 'next/font/google'
import './globals.css'
import 'katex/dist/katex.min.css'
import { AuthProvider } from '@/contexts/AuthContext'
import { CreditsProvider } from '@/contexts/CreditsContext'
import { GoogleOAuthWrapper } from '@/contexts/GoogleOAuthWrapper'

const dmSans = DM_Sans({ subsets: ['latin'], variable: '--font-body' })
// Distinctive numerals for prices/figures — gives the data a terminal-instrument feel.
const spaceGrotesk = Space_Grotesk({ subsets: ['latin'], weight: ['500', '600', '700'], variable: '--font-numeric' })

export const metadata: Metadata = {
  title: 'Finch - Trading Bots',
  description: 'AI-powered trading bots',
  viewport: {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 1,
    userScalable: false,
    viewportFit: 'cover'
  },
  themeColor: '#2563eb',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: 'Finch'
  }
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${dmSans.variable} ${spaceGrotesk.variable} ${dmSans.className}`}>
        <GoogleOAuthWrapper>
          <AuthProvider>
            <CreditsProvider>
              {children}
            </CreditsProvider>
          </AuthProvider>
        </GoogleOAuthWrapper>
      </body>
    </html>
  )
}
