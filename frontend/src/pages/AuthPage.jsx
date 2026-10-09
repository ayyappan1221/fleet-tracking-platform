import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { errorMessage } from '../utils/errors.js';

const ROLES = ['driver', 'manager', 'mechanic'];

const ROLE_NOTES = {
  driver: 'Drivers run planned routes, mark stops arrived, and record GPS pings.',
  manager: 'Managers see fleet-wide alerts, vehicles, routes, and can mark alerts read.',
  mechanic: 'Mechanics track maintenance records and update their status.',
};

// Same five rules the backend enforces (app/core/password.py).
const PASSWORD_RULES = [
  { key: 'length', label: 'At least 8 characters', test: (v) => v.length >= 8 },
  { key: 'upper', label: 'One uppercase letter (A–Z)', test: (v) => /[A-Z]/.test(v) },
  { key: 'lower', label: 'One lowercase letter (a–z)', test: (v) => /[a-z]/.test(v) },
  { key: 'digit', label: 'One digit (0–9)', test: (v) => /[0-9]/.test(v) },
  {
    key: 'special',
    label: 'One special character (e.g. !@#$)',
    test: (v) => /[^A-Za-z0-9]/.test(v),
  },
];

const passwordMeetsAll = (value) => PASSWORD_RULES.every((r) => r.test(value || ''));

// Seeded by the backend on startup (app/main.py) — pre-verified demo logins.
const DEMO_ACCOUNTS = {
  manager: { email: 'manager@fleet.com', password: 'Password@123' },
  driver: { email: 'driver@fleet.com', password: 'Password@123' },
  mechanic: { email: 'mechanic@fleet.com', password: 'Password@123' },
};

export default function AuthPage() {
  const [tab, setTab] = useState('signin');
  const [method, setMethod] = useState('password'); // signin only: 'password' | 'otp'
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(false);

  // Shared fields
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  // Sign Up extra fields
  const [name, setName] = useState('');
  const [role, setRole] = useState('driver');

  // OTP step state (signup verification + otp login share the code box)
  const [otpSent, setOtpSent] = useState(false);
  const [otpCode, setOtpCode] = useState('');
  const [demoCode, setDemoCode] = useState('');

  const navigate = useNavigate();

  const switchTab = (next) => {
    setTab(next);
    setError('');
    setNotice('');
    setOtpSent(false);
    setOtpCode('');
    setDemoCode('');
  };

  const switchMethod = (next) => {
    setMethod(next);
    setError('');
    setNotice('');
    setOtpSent(false);
    setOtpCode('');
    setDemoCode('');
  };

  const storeTokenAndGo = (res) => {
    localStorage.setItem('token', res.data.data.access_token);
    navigate('/');
  };

  // ----- password sign in ----------------------------------------------------
  const handleSignIn = async (e) => {
    e.preventDefault();
    setError('');
    setNotice('');
    setLoading(true);
    try {
      const res = await api.login(email, password);
      storeTokenAndGo(res);
    } catch (err) {
      const msg = errorMessage(err, 'Login failed. Please try again.');
      setError(msg);
      if (/not verified/i.test(msg)) {
        setNotice('Your email is not verified yet — switch to Sign Up and enter the code sent at registration, or request a fresh code below.');
      }
    } finally {
      setLoading(false);
    }
  };

  // ----- sign up -------------------------------------------------------------
  const handleSignUp = async (e) => {
    e.preventDefault();
    setError('');
    setNotice('');
    if (!passwordMeetsAll(password)) {
      setError('Password does not meet all strength requirements yet.');
      return;
    }
    setLoading(true);
    try {
      const res = await api.register({ email, name, password, role });
      const devOtp = res?.data?.data?.dev_otp;
      setOtpSent(true);
      setDemoCode(devOtp || '');
      setNotice(
        devOtp
          ? 'Account created. Enter the 6-digit code below to activate it.'
          : 'Account created. Check your email for the 6-digit activation code.'
      );
    } catch (err) {
      setError(errorMessage(err, 'Registration failed. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  const handleVerifySignup = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.verifySignup(email, otpCode.trim());
      const res = await api.login(email, password);
      storeTokenAndGo(res);
    } catch (err) {
      setError(errorMessage(err, 'Verification failed. Check the code and try again.'));
    } finally {
      setLoading(false);
    }
  };

  const handleResendSignupCode = async () => {
    setError('');
    setLoading(true);
    try {
      const res = await api.requestOtp(email, 'signup_verify');
      const devOtp = res?.data?.data?.dev_otp;
      setDemoCode(devOtp || '');
      setNotice('A fresh code was sent.');
    } catch (err) {
      setError(errorMessage(err, 'Could not resend the code.'));
    } finally {
      setLoading(false);
    }
  };

  // ----- OTP sign in ---------------------------------------------------------
  const handleSendLoginCode = async (e) => {
    e.preventDefault();
    setError('');
    setNotice('');
    setLoading(true);
    try {
      const res = await api.requestOtp(email, 'login_otp');
      const devOtp = res?.data?.data?.dev_otp;
      setOtpSent(true);
      setDemoCode(devOtp || '');
      setNotice(
        devOtp
          ? 'Code sent. Enter it below to sign in.'
          : 'Code sent. Check your email, then enter it below.'
      );
    } catch (err) {
      setError(errorMessage(err, 'Could not send a login code.'));
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyLoginCode = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await api.loginWithOtp(email, otpCode.trim());
      storeTokenAndGo(res);
    } catch (err) {
      setError(errorMessage(err, 'Login failed. Check the code and try again.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className='auth-wrap'>
      <div className='auth-card'>
        <div className='auth-badge' aria-hidden='true'>
          F
        </div>
        <h1>{tab === 'signin' ? 'Welcome back' : 'Create account'}</h1>
        <p className='sub'>
          {tab === 'signin'
            ? 'Sign in with your password or a one-time email code.'
            : 'Register once — the first account becomes the manager; later sign-ups may be restricted.'}
        </p>

        <div className='tabs' role='tablist' aria-label='Sign in or sign up'>
          <button
            type='button'
            role='tab'
            aria-selected={tab === 'signin'}
            className={`tab${tab === 'signin' ? ' active' : ''}`}
            onClick={() => switchTab('signin')}
          >
            Sign In
          </button>
          <button
            type='button'
            role='tab'
            aria-selected={tab === 'signup'}
            className={`tab${tab === 'signup' ? ' active' : ''}`}
            onClick={() => switchTab('signup')}
          >
            Sign Up
          </button>
        </div>

        {error && <p className='error'>{error}</p>}
        {notice && <p className='success-note'>{notice}</p>}
        {demoCode && (
          <p className='demo-code' role='status'>
            Demo mode — your code is <strong>{demoCode}</strong>
          </p>
        )}

        {tab === 'signin' ? (
          <div>
            <div className='tabs' role='tablist' aria-label='Sign in method'>
              <button
                type='button'
                role='tab'
                aria-selected={method === 'password'}
                className={`tab${method === 'password' ? ' active' : ''}`}
                onClick={() => switchMethod('password')}
              >
                Password
              </button>
              <button
                type='button'
                role='tab'
                aria-selected={method === 'otp'}
                className={`tab${method === 'otp' ? ' active' : ''}`}
                onClick={() => switchMethod('otp')}
              >
                Email code
              </button>
            </div>

            {method === 'password' ? (
              <form onSubmit={handleSignIn}>
                <label>
                  Email
                  <input
                    type='email'
                    autoComplete='email'
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </label>
                <label>
                  Password
                  <input
                    type='password'
                    autoComplete='current-password'
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                </label>
                <button type='submit' className='btn btn-block' disabled={loading}>
                  {loading ? 'Signing in…' : 'Sign In'}
                </button>
                <div className='demo-row' aria-label='Demo logins'>
                  <span className='hint'>Try a demo account:</span>
                  {Object.keys(DEMO_ACCOUNTS).map((demoRole) => (
                    <button
                      key={demoRole}
                      type='button'
                      className='btn btn-sm btn-ghost'
                      disabled={loading}
                      onClick={async () => {
                        setError('');
                        setNotice('');
                        setLoading(true);
                        try {
                          const creds = DEMO_ACCOUNTS[demoRole];
                          const res = await api.login(creds.email, creds.password);
                          storeTokenAndGo(res);
                        } catch (err) {
                          setError(errorMessage(err, 'Demo login failed. Is the backend seeded?'));
                        } finally {
                          setLoading(false);
                        }
                      }}
                    >
                      {demoRole}
                    </button>
                  ))}
                </div>
              </form>
            ) : !otpSent ? (
              <form onSubmit={handleSendLoginCode}>
                <label>
                  Email
                  <input
                    type='email'
                    autoComplete='email'
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </label>
                <button type='submit' className='btn btn-block' disabled={loading}>
                  {loading ? 'Sending code…' : 'Send login code'}
                </button>
              </form>
            ) : (
              <form onSubmit={handleVerifyLoginCode}>
                <label>
                  6-digit code
                  <input
                    type='text'
                    inputMode='numeric'
                    autoComplete='one-time-code'
                    maxLength={6}
                    placeholder='e.g. 482913'
                    value={otpCode}
                    onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                    required
                  />
                </label>
                <button type='submit' className='btn btn-block' disabled={loading}>
                  {loading ? 'Verifying…' : 'Sign In with code'}
                </button>
                <button
                  type='button'
                  className='btn btn-ghost btn-block'
                  disabled={loading}
                  onClick={() => switchMethod('otp')}
                >
                  Use a different email
                </button>
              </form>
            )}
          </div>
        ) : !otpSent ? (
          <form onSubmit={handleSignUp}>
            <label>
              Name
              <input
                type='text'
                autoComplete='name'
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </label>
            <label>
              Email
              <input
                type='email'
                autoComplete='email'
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </label>
            <label>
              Password
              <input
                type='password'
                autoComplete='new-password'
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                aria-describedby='pw-rules'
              />
            </label>
            <ul className='pw-checks' id='pw-rules' aria-label='Password requirements'>
              {PASSWORD_RULES.map((rule) => {
                const met = rule.test(password || '');
                return (
                  <li key={rule.key} className={`pw-check${met ? ' met' : ''}`}>
                    <span className='pw-box' aria-hidden='true'>
                      {met ? '✓' : ''}
                    </span>
                    {rule.label}
                  </li>
                );
              })}
            </ul>
            <label>
              Role
              <select value={role} onChange={(e) => setRole(e.target.value)}>
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {r.charAt(0).toUpperCase() + r.slice(1)}
                  </option>
                ))}
              </select>
            </label>
            <p className='role-note'>{ROLE_NOTES[role]}</p>
            <button
              type='submit'
              className='btn btn-block'
              disabled={loading || !passwordMeetsAll(password)}
            >
              {loading ? 'Creating account…' : 'Sign Up'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleVerifySignup}>
            <label>
              6-digit activation code
              <input
                type='text'
                inputMode='numeric'
                autoComplete='one-time-code'
                maxLength={6}
                placeholder='e.g. 482913'
                value={otpCode}
                onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                required
              />
              <span className='hint'>Sent to {email}. It expires in 10 minutes.</span>
            </label>
            <button type='submit' className='btn btn-block' disabled={loading}>
              {loading ? 'Verifying…' : 'Verify & create account'}
            </button>
            <button
              type='button'
              className='btn btn-ghost btn-block'
              disabled={loading}
              onClick={handleResendSignupCode}
            >
              Resend code
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
