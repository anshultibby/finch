import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Privacy Policy - Finch',
};

export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-3xl mx-auto px-6 py-16">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Privacy Policy</h1>
        <p className="text-sm text-gray-500 mb-10">Last updated: May 11, 2026</p>

        <div className="space-y-8 text-gray-700 text-[15px] leading-relaxed">
          <section>
            <h2 className="text-lg font-semibold text-gray-900 mb-2">What is Finch</h2>
            <p>
              Finch is an AI-powered financial assistant that helps you research markets,
              manage watchlists, and automate trading strategies. Finch is operated by
              Anshul Tibrewal.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Information We Collect</h2>
            <p className="mb-3">When you sign in with Google, we receive:</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>Your email address</li>
              <li>Your name and profile picture</li>
            </ul>
            <p className="mt-3">When you use Finch, we also store:</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>Chat messages and conversations with the AI assistant</li>
              <li>Trading bot configurations and execution history</li>
              <li>API keys you provide for third-party services (encrypted)</li>
              <li>Files you upload during chat sessions</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 mb-2">How We Use Your Information</h2>
            <ul className="list-disc pl-5 space-y-1">
              <li>To authenticate you and provide access to the platform</li>
              <li>To deliver the AI assistant and trading bot features you use</li>
              <li>To send notifications you opt into (email alerts, trade confirmations)</li>
            </ul>
            <p className="mt-3">We do not sell your personal information to third parties.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Third-Party Services</h2>
            <p>Finch integrates with third-party services that have their own privacy policies:</p>
            <ul className="list-disc pl-5 space-y-1 mt-2">
              <li>Google (authentication)</li>
              <li>Supabase (database and file storage)</li>
              <li>Brokerage providers you connect (e.g., Alpaca, SnapTrade)</li>
              <li>Market data providers</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Data Security</h2>
            <p>
              We use industry-standard security measures including encrypted connections (HTTPS),
              secure authentication tokens, and encrypted storage for sensitive data like API keys.
              Your brokerage credentials are never stored directly — we use OAuth-based connections
              through authorized providers.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Data Retention and Deletion</h2>
            <p>
              Your data is retained as long as your account is active. You can request deletion
              of your account and all associated data by contacting us. Upon deletion, we remove
              your personal data, chat history, bot configurations, and stored files.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Contact</h2>
            <p>
              If you have questions about this privacy policy or your data, contact us
              at{' '}
              <a href="mailto:anshul.tibrewal2203@gmail.com" className="text-blue-600 hover:underline">
                anshul.tibrewal2203@gmail.com
              </a>.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
