import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Contact Us - Finch',
};

export default function ContactUs() {
  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-3xl mx-auto px-6 py-16">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Contact Us</h1>
        <p className="text-sm text-gray-500 mb-10">We&apos;d love to hear from you.</p>

        <div className="space-y-8 text-gray-700 text-[15px] leading-relaxed">
          <section>
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Get in Touch</h2>
            <p>
              Finch is an AI-powered financial assistant operated by Anshul Tibrewal.
              Whether you have a question, found a bug, want to request a feature, or
              need help with your account, reach out and we&apos;ll get back to you.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Email</h2>
            <p>
              The fastest way to reach us is by email at{' '}
              <a
                href="mailto:anshul.tibrewal2203@gmail.com"
                className="text-blue-600 hover:underline"
              >
                anshul.tibrewal2203@gmail.com
              </a>
              . We typically respond within a couple of business days.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Account &amp; Data Requests</h2>
            <p>
              To request deletion of your account and associated data, or to ask about
              the information we store, email us using the address above and we&apos;ll
              take care of it. See our{' '}
              <a href="/privacy" className="text-blue-600 hover:underline">
                Privacy Policy
              </a>{' '}
              for more details on how your data is handled.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
