import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

// ── Hard-coded demo credentials for all user types ──
// Password for all demo accounts: Password@123
export const DEMO_CREDENTIALS = {
  manager: { email: 'manager@fleet.com', password: 'Password@123', name: 'Demo Manager', role: 'manager' },
  driver: { email: 'driver@fleet.com', password: 'Password@123', name: 'Demo Driver', role: 'driver' },
  mechanic: { email: 'mechanic@fleet.com', password: 'Password@123', name: 'Demo Mechanic', role: 'mechanic' },
};

// Keep ROLES derived from DEMO_CREDENTIALS so they stay in sync
const ROLES = Object.keys(DEMO_CREDENTIALS);

export default function AuthPage() {
  const [tab, setTab] = useState('signin');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Sign In fields
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  // Sign Up extra fields
  const [name, setName] = useState('');
  const [role, setRole] = useState('driver');

  const navigate = useNavigate();

  const fillDemo = (role) => {
    const creds = DEMO_CREDENTIALS[role];
    setEmail(creds.email);
    setPassword(creds.password);
    if (tab === 'signup') {
      setName(creds.name);
      setRole(creds.role);
    }
    setError('');
  };

  const handleSignIn = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await api.login(email, password);
      localStorage.setItem('token', res.data.data.access_token);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.message || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSignUp = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.register({ email, name, password, role });
      const res = await api.login(email, password);
      localStorage.setItem('token', res.data.data.access_token);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.message || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const tabStyle = (active) => ({
    flex: 1,
    padding: '8px 0',
    border: 'none',
    background: active ? '#0e7490' : 'transparent',
    color: active ? '#fff' : '#6b7684',
    fontSize: '14px',
    fontWeight: 600,
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'background 0.15s, color 0.15s',
  });

  const selectStyle = {
    width: '100%',
    marginTop: '6px',
    padding: '10px',
    border: '1px solid #ccd2d9',
    borderRadius: '8px',
    fontSize: '14px',
    background: '#fff',
  };

  return (
    <div className='auth-wrap'>
      <div className='auth-card'>
        <h1>{tab === 'signin' ? 'Welcome back' : 'Create account'}</h1>
        <p className='sub'>
          {tab === 'signin'
            ? 'Sign in to your fleet dashboard'
            : 'Register to get started'}
        </p>

        {/* Tab bar */}
        <div style={{ display: 'flex', gap: '6px', background: '#f1f5f9', borderRadius: '8px', padding: '4px', marginBottom: '20px' }}>
          <button type='button' style={tabStyle(tab === 'signin')} onClick={() => { setTab('signin'); setError(''); }}>
            Sign In
          </button>
          <button type='button' style={tabStyle(tab === 'signup')} onClick={() => { setTab('signup'); setError(''); }}>
            Sign Up
          </button>
        </div>

        {error && <p className='error'>{error}</p>}

        <div style={{ marginBottom: '16px', padding: '12px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px' }}>
          <p style={{ fontSize: '12px', fontWeight: 700, color: '#334155', margin: '0 0 8px 0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Demo Accounts — Click to Fill</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' }}>
            {Object.entries(DEMO_CREDENTIALS).map(([key, creds]) => (
              <button
                key={key}
                type='button'
                onClick={() => fillDemo(key)}
                style={{
                  padding: '10px 6px',
                  border: '1px solid #cbd5e1',
                  borderRadius: '8px',
                  background: '#fff',
                  cursor: 'pointer',
                  textAlign: 'center',
                  lineHeight: 1.3,
                }}
              >
                <div style={{ fontSize: '13px', fontWeight: 700, color: '#0e7490', textTransform: 'capitalize' }}>{key}</div>
                <div style={{ fontSize: '11px', color: '#64748b', wordBreak: 'break-all' }}>{creds.email}</div>
                <div style={{ fontSize: '11px', color: '#94a3b8' }}>Password@123</div>
              </button>
            ))}
          </div>
          <p style={{ fontSize: '11px', color: '#94a3b8', margin: '8px 0 0 0', textAlign: 'center' }}>All demo accounts use the same password</p>
        </div>

        {tab === 'signin' ? (
          <form onSubmit={handleSignIn}>
            <label>
              Email
              <input
                type='email'
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </label>
            <label>
              Password
              <input
                type='password'
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>
            <button type='submit' disabled={loading}>
              {loading ? 'Signing in…' : 'Sign In'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleSignUp}>
            <label>
              Name
              <input
                type='text'
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </label>
            <label>
              Email
              <input
                type='email'
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </label>
            <label>
              Password
              <input
                type='password'
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>
            <label>
              Role
              <select
                style={selectStyle}
                value={role}
                onChange={(e) => setRole(e.target.value)}
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {r.charAt(0).toUpperCase() + r.slice(1)}
                  </option>
                ))}
              </select>
            </label>
            <button type='submit' disabled={loading}>
              {loading ? 'Creating account…' : 'Sign Up'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
