import ChatContainer from '@/components/ChatContainer';
import PasswordGate from '@/components/PasswordGate';

export default function Home() {
  return (
    <PasswordGate>
      <main className="min-h-screen">
        <ChatContainer />
      </main>
    </PasswordGate>
  );
}

