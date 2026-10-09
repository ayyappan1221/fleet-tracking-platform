import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { errorMessage } from './errors.js';

describe('errorMessage', () => {
  it('prefers FastAPI string detail', () => {
    assert.equal(
      errorMessage({ response: { data: { detail: 'Nope' } } }, 'fb'),
      'Nope'
    );
  });

  it('joins validation-error arrays', () => {
    const err = { response: { data: { detail: [{ msg: 'bad x' }, { msg: 'bad y' }] } } };
    assert.equal(errorMessage(err, 'fb'), 'bad x; bad y');
  });

  it('falls back to envelope message then the fallback', () => {
    assert.equal(
      errorMessage({ response: { data: { message: 'Env msg' } } }, 'fb'),
      'Env msg'
    );
    assert.equal(errorMessage({}, 'fb'), 'fb');
    assert.equal(errorMessage(null), 'Something went wrong.');
  });
});
