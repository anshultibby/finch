import { View, Text, TouchableOpacity, ActivityIndicator, StyleSheet, TextInput, Alert } from 'react-native';
import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { LinearGradient } from 'expo-linear-gradient';
import Svg, { Path } from 'react-native-svg';
import FinchLogo from '@/components/FinchLogo';
import { MessageSquare } from 'lucide-react-native';

const EXAMPLE_PROMPTS = [
  'Is NVDA overvalued right now?',
  'Build me a momentum strategy',
  'Compare AAPL vs MSFT fundamentals',
  'What biotech catalysts are coming up?',
  'Review my portfolio risk exposure',
];

function useTypingAnimation() {
  const [text, setText] = useState('');
  const promptIndex = useRef(0);
  const charIndex = useRef(0);
  const deleting = useRef(false);
  const paused = useRef(false);

  useEffect(() => {
    const tick = () => {
      const prompt = EXAMPLE_PROMPTS[promptIndex.current];

      if (paused.current) {
        paused.current = false;
        deleting.current = true;
        return 1500;
      }

      if (deleting.current) {
        charIndex.current--;
        setText(prompt.substring(0, charIndex.current));
        if (charIndex.current === 0) {
          deleting.current = false;
          promptIndex.current = (promptIndex.current + 1) % EXAMPLE_PROMPTS.length;
          return 300;
        }
        return 20;
      }

      charIndex.current++;
      setText(prompt.substring(0, charIndex.current));
      if (charIndex.current === prompt.length) {
        paused.current = true;
        return 2000;
      }
      return 40;
    };

    let timeout: ReturnType<typeof setTimeout>;
    const schedule = () => {
      const delay = tick();
      timeout = setTimeout(schedule, delay);
    };
    timeout = setTimeout(schedule, 500);
    return () => clearTimeout(timeout);
  }, []);

  return text;
}

export default function LoginScreen() {
  const { signInWithGoogle, signInWithEmail, signUpWithEmail } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [showEmailLogin, setShowEmailLogin] = useState(false);
  const [emailMode, setEmailMode] = useState<'signin' | 'signup'>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const typingText = useTypingAnimation();

  const handleSignIn = async () => {
    setIsLoading(true);
    try {
      await signInWithGoogle();
    } catch (error) {
      console.error('Sign in error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleEmailSignIn = async () => {
    if (!email || !password) return;
    setIsLoading(true);
    try {
      if (emailMode === 'signup') {
        const { needsConfirmation } = await signUpWithEmail(email, password);
        if (needsConfirmation) {
          Alert.alert(
            'Confirm your email',
            'Account created. Check your email to confirm, then sign in.'
          );
          setEmailMode('signin');
        }
      } else {
        await signInWithEmail(email, password);
      }
    } catch (error: any) {
      Alert.alert(
        emailMode === 'signup' ? 'Sign up failed' : 'Sign in failed',
        error.message || 'Invalid credentials'
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <LinearGradient colors={['#ecfdf5', '#f0fdfa', '#ffffff']} style={styles.container}>
      <View style={styles.content}>
        {/* Logo */}
        <View style={styles.logoRow}>
          <FinchLogo size={28} />
          <Text style={styles.logoText}>Finch</Text>
        </View>

        {/* Hero */}
        <View style={styles.hero}>
          <Text style={styles.headline}>
            Your AI{'\n'}investment{'\n'}
            <Text style={styles.headlineGreen}>research desk</Text>
          </Text>

          <View style={styles.features}>
            <Text style={styles.feature}>Real-time portfolio sync</Text>
            <Text style={styles.featureDot}>·</Text>
            <Text style={styles.feature}>Code sandbox</Text>
            <Text style={styles.featureDot}>·</Text>
            <Text style={styles.feature}>Deep research</Text>
          </View>
        </View>

        {/* Fake chat input */}
        <View style={styles.chatPreview}>
          <MessageSquare size={16} color="#9ca3af" />
          <Text style={styles.chatText} numberOfLines={1}>
            {typingText}
            <Text style={styles.cursor}>|</Text>
          </Text>
        </View>

        {/* CTA */}
        <TouchableOpacity
          onPress={handleSignIn}
          disabled={isLoading}
          style={styles.ctaBtn}
          activeOpacity={0.85}
        >
          {isLoading ? (
            <ActivityIndicator color="#374151" />
          ) : (
            <View style={styles.ctaInner}>
              <Svg width={18} height={18} viewBox="0 0 48 48">
                <Path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
                <Path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
                <Path fill="#FBBC05" d="M10.53 28.59a14.5 14.5 0 010-9.18l-7.98-6.19a24.01 24.01 0 000 21.56l7.98-6.19z" />
                <Path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
              </Svg>
              <Text style={styles.ctaText}>Continue with Google</Text>
            </View>
          )}
        </TouchableOpacity>

        <Text style={styles.disclaimer}>Free to sign up · No credit card required</Text>

        {showEmailLogin ? (
          <View style={styles.emailForm}>
            <TextInput
              style={styles.input}
              placeholder="Email"
              placeholderTextColor="#9ca3af"
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              keyboardType="email-address"
            />
            <TextInput
              style={styles.input}
              placeholder="Password"
              placeholderTextColor="#9ca3af"
              value={password}
              onChangeText={setPassword}
              secureTextEntry
            />
            <TouchableOpacity
              onPress={handleEmailSignIn}
              disabled={isLoading}
              style={styles.emailBtn}
              activeOpacity={0.85}
            >
              {isLoading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.emailBtnText}>
                  {emailMode === 'signup' ? 'Create account' : 'Sign in'}
                </Text>
              )}
            </TouchableOpacity>
            <TouchableOpacity
              onPress={() => setEmailMode(emailMode === 'signup' ? 'signin' : 'signup')}
              style={styles.emailToggle}
            >
              <Text style={styles.emailToggleText}>
                {emailMode === 'signup'
                  ? 'Already have an account? Sign in'
                  : "Don't have an account? Sign up"}
              </Text>
            </TouchableOpacity>
          </View>
        ) : (
          <TouchableOpacity onPress={() => setShowEmailLogin(true)} style={styles.emailToggle}>
            <Text style={styles.emailToggleText}>Sign in with email</Text>
          </TouchableOpacity>
        )}
      </View>

      <Text style={styles.legal}>
        By continuing, you agree to our Terms of Service and Privacy Policy
      </Text>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    flex: 1,
    paddingHorizontal: 32,
    justifyContent: 'center',
  },
  logoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 32,
  },
  logoText: {
    fontSize: 18,
    fontFamily: 'DMSans-Bold',
    color: '#111827',
    letterSpacing: -0.5,
  },
  hero: {
    marginBottom: 40,
  },
  headline: {
    fontSize: 38,
    fontFamily: 'DMSans-Bold',
    color: '#111827',
    lineHeight: 44,
    letterSpacing: -1,
  },
  headlineGreen: {
    color: '#059669',
  },
  features: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 16,
    flexWrap: 'wrap',
  },
  feature: {
    fontSize: 13,
    fontFamily: 'DMSans',
    color: '#6b7280',
  },
  featureDot: {
    fontSize: 13,
    color: '#d1d5db',
    marginHorizontal: 8,
  },
  chatPreview: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: '#ffffff',
    borderRadius: 16,
    paddingHorizontal: 16,
    paddingVertical: 14,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.04,
    shadowRadius: 8,
    elevation: 2,
  },
  chatText: {
    flex: 1,
    fontSize: 15,
    fontFamily: 'DMSans',
    color: '#374151',
  },
  cursor: {
    color: '#059669',
    fontWeight: '300',
  },
  ctaBtn: {
    backgroundColor: '#ffffff',
    borderRadius: 14,
    paddingVertical: 15,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#e5e7eb',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 3,
  },
  ctaInner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  ctaText: {
    color: '#374151',
    fontSize: 16,
    fontFamily: 'DMSans-Medium',
  },
  disclaimer: {
    textAlign: 'center',
    fontSize: 12,
    fontFamily: 'DMSans',
    color: '#9ca3af',
    marginTop: 12,
  },
  emailToggle: {
    alignItems: 'center',
    marginTop: 8,
  },
  emailToggleText: {
    fontSize: 13,
    fontFamily: 'DMSans',
    color: '#9ca3af',
  },
  emailForm: {
    marginTop: 12,
    gap: 10,
  },
  input: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 13,
    fontSize: 15,
    fontFamily: 'DMSans',
    color: '#111827',
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  emailBtn: {
    backgroundColor: '#059669',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  emailBtnText: {
    color: '#ffffff',
    fontSize: 15,
    fontFamily: 'DMSans-Medium',
  },
  legal: {
    textAlign: 'center',
    fontSize: 11,
    fontFamily: 'DMSans',
    color: '#d1d5db',
    paddingHorizontal: 40,
    paddingBottom: 32,
    lineHeight: 16,
  },
});
