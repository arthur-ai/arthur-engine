import { describe, it, expect } from 'vitest';
import { buzzSay } from './prompts.js';

describe('buzzSay', () => {
  it('prefixes with [ BUZZ ] tag', () => {
    const result = buzzSay('Hello world');
    expect(result).toContain('[ BUZZ ]');
    expect(result).toContain('Hello world');
  });

  it('substitutes single variable', () => {
    const result = buzzSay('Running diagnostics on {item}...', { item: 'engines' });
    expect(result).toContain('Running diagnostics on engines...');
  });

  it('substitutes multiple variables', () => {
    const result = buzzSay('{a} and {b}', { a: 'foo', b: 'bar' });
    expect(result).toContain('foo and bar');
  });

  it('leaves unknown placeholders untouched', () => {
    const result = buzzSay('{unknown} placeholder', {});
    expect(result).toContain('{unknown}');
  });

  it('works with no vars', () => {
    const result = buzzSay('Simple message');
    expect(result).toContain('Simple message');
  });

  it('handles empty string', () => {
    const result = buzzSay('');
    expect(result).toContain('[ BUZZ ]');
  });
});
