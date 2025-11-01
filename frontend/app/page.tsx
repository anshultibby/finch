import ChatContainer from '@/components/ChatContainer';
import AuthGate from '@/components/PasswordGate';

export default function Home() {
  return (
    <AuthGate>
      <main className="min-h-screen">
        <ChatContainer />
      </main>
    </AuthGate>
  );
}

