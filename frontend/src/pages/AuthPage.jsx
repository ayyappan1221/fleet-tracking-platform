import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

const ROLES = ['driver', 'manager', 'mechanic'];

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
