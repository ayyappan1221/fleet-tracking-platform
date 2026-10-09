import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { decodeToken, isTokenExpired, getTokenRole, isManager } from './auth.js';

function b64url(obj) {
  return Buffer.from(JSON.stringify(obj)).toString('base64url');
}

function token(payload) {
  return `h.${b64url(payload)}.s`;
}

describe('decodeToken', () => {
  it('returns null for missing or malformed tokens', () => {
    assert.equal(decodeToken(null), null);
    assert.equal(decodeToken(''), null);
    assert.equal(decodeToken('not.a.jwt.at.all.extra'), null);
  });

  it('decodes the payload', () => {
    const payload = { sub: '1', email: 'a@b.c', role: 'manager' };
    assert.deepEqual(decodeToken(token(payload)), payload);
  });
});

describe('isTokenExpired', () => {
  it('flags past exp and passes future exp', () => {
    const past = token({ exp: Math.floor(Date.now() / 1000) - 60 });
    const future = token({ exp: Math.floor(Date.now() / 1000) + 3600 });
    assert.equal(isTokenExpired(past), true);
    assert.equal(isTokenExpired(future), false);
  });

  it('returns false when exp is missing', () => {
    assert.equal(isTokenExpired(token({ role: 'driver' })), false);
  });
});

describe('roles', () => {
  it('reads role and detects managers', () => {
    assert.equal(getTokenRole(token({ role: 'manager' })), 'manager');
    assert.equal(getTokenRole(token({ role: 'driver' })), 'driver');
    assert.equal(getTokenRole(null), null);
    assert.equal(isManager(token({ role: 'manager' })), true);
    assert.equal(isManager(token({ role: 'mechanic' })), false);
  });
});
