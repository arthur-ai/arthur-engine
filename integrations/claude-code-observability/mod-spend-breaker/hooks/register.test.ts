import { expect, mock, test } from 'claude-code/testing'

// The engine's $.store and $.env, in memory for the test (cap $0.10).
function engine(on: any) {
  mock.store(on)
  mock.env(on, { ARTHUR_BREAKER_CAP_USD: '0.10' })
}

const USAGE = { input_tokens: 0, output_tokens: 0, cache_creation_input_tokens: 0, cache_read_input_tokens: 0 }

// Drain a turn.step stream: the text it showed and the step's result.
async function step($: any, index: number, turnId = 't1') {
  const stream = $.turn.step({ turnId, index, model: 'claude-haiku-4-5', messageCount: 1 })
  let text = ''
  for (let r = await stream.next(); ; r = await stream.next()) {
    if (r.done) return { text, result: r.value }
    if (r.value.kind === 'text') text += r.value.text
  }
}

test('a prompt under the cap reaches the model', async ($, on) => {
  engine(on)
  on('prompt.submit', ($, e) => ({ text: e.text }))
  await expect($.prompt.submit({ text: 'hello', wait: false })).resolves.toEqual(expect.objectContaining({ text: 'hello' }))
})

test('once spend passes the cap the next model request is answered without the model', async ($, on) => {
  engine(on)
  let sent = 0
  on('turn.step', async function* ($, e) {
    sent += 1
    yield { kind: 'text', index: 0, text: 'ok' }
    // 20,000 output tokens of Haiku at $5/M: $0.10, the default cap.
    return { turnId: e.turnId, index: e.index, answer: 'ok', toolUses: [], stopReason: 'end_turn', usage: { ...USAGE, output_tokens: 20000, model: 'claude-haiku-4-5' } }
  })
  on('prompt.submit', ($, e) => ({ text: e.text }))
  await $.prompt.submit({ text: 'breaker reset', wait: false })
  await step($, 0)
  const second = await step($, 1)
  expect(sent).toBe(1)
  expect(second.text).toContain('Arthur spend breaker')
  const next = await $.prompt.submit({ text: 'more', wait: false })
  expect(next.drop).toContain('Paused')
})

test('breaker override lifts it and the command never reaches the model', async ($, on) => {
  engine(on)
  let prompts = 0
  on('prompt.submit', ($, e) => { prompts += 1; return { text: e.text } })
  const out = await $.prompt.submit({ text: 'breaker override', wait: false })
  expect(out.drop).toContain('lifted until')
  await $.prompt.submit({ text: 'breaker reset', wait: false })
  expect(prompts).toBe(0)
})

test('a long answer is cut mid-stream once its own output would pass the cap', async ($, on) => {
  mock.store(on, { [`spend:${Date.now()}:earlier`]: 0.095 }) // $0.095 already spent in the window
  mock.env(on, { ARTHUR_BREAKER_CAP_USD: '0.10' })
  let pieces = 0
  on('turn.step', async function* ($, e) {
    // Ten 1,000-character pieces: ~250 output tokens each, ~$0.00125 at $5/M.
    for (let i = 0; i < 10; i++) {
      pieces += 1
      yield { kind: 'text', index: 0, text: 'x'.repeat(1000) }
    }
    return { turnId: e.turnId, index: e.index, answer: '', toolUses: [], stopReason: 'end_turn', usage: { ...USAGE, output_tokens: 2500, model: 'claude-haiku-4-5' } }
  })
  const { text } = await step($, 0)
  expect(text).toContain('stopped this answer mid-stream')
  expect(pieces).toBeLessThan(10)
})

test('a cap that is not a positive number falls back to $0.10 instead of disabling the breaker', async ($, on) => {
  mock.store(on)
  mock.env(on, { ARTHUR_BREAKER_CAP_USD: 'ten dollars' })
  let sent = 0
  on('turn.step', async function* ($, e) {
    sent += 1
    return { turnId: e.turnId, index: e.index, answer: '', toolUses: [], stopReason: 'end_turn', usage: { ...USAGE, output_tokens: 20000, model: 'claude-haiku-4-5' } }
  })
  await step($, 0) // $0.10
  const second = await step($, 1)
  expect(sent).toBe(1)
  expect(second.text).toContain('(cap $0.1)')
})

test('requests finishing at the same time are all counted', async ($, on) => {
  mock.store(on)
  mock.env(on, { ARTHUR_BREAKER_CAP_USD: '0.10' })
  on('turn.step', async function* ($, e) {
    // 6,000 output tokens: $0.03 each; three together cross the cap only if none is lost.
    return { turnId: e.turnId, index: e.index, answer: '', toolUses: [], stopReason: 'end_turn', usage: { ...USAGE, output_tokens: 6000, model: 'claude-haiku-4-5' } }
  })
  on('prompt.submit', ($, e) => ({ text: e.text }))
  await Promise.all([step($, 0, 'a'), step($, 0, 'b'), step($, 0, 'c'), step($, 0, 'd')])
  const status = await $.prompt.submit({ text: 'breaker status', wait: false })
  expect(status.drop).toContain('$0.1200')
})

test('a cut request also counts its input side, estimated from the request before it', async ($, on) => {
  mock.store(on)
  mock.env(on, { ARTHUR_BREAKER_CAP_USD: '0.10' })
  let call = 0
  on('turn.step', async function* ($, e) {
    call += 1
    if (call === 1) {
      // A finished request: 90,000 prompt tokens at $1/M, $0.09.
      return { turnId: e.turnId, index: e.index, answer: '', toolUses: [], stopReason: 'end_turn', usage: { ...USAGE, input_tokens: 90000, model: 'claude-haiku-4-5' } }
    }
    for (let i = 0; i < 40; i++) yield { kind: 'text', index: 0, text: 'x'.repeat(1000) }
    return { turnId: e.turnId, index: e.index, answer: '', toolUses: [], stopReason: 'end_turn', usage: { ...USAGE, output_tokens: 10000, model: 'claude-haiku-4-5' } }
  })
  on('prompt.submit', ($, e) => ({ text: e.text }))
  await step($, 0)
  const { text } = await step($, 1)
  // $0.09 spent + the resent 90,000-token prompt at the cache-read price ($0.009)
  // leaves $0.001 of room: about 800 characters, so the cut comes on the first piece.
  // Counting output alone would have allowed 8,000.
  expect(text.length).toBeLessThan(1200)
  const status = await $.prompt.submit({ text: 'breaker status', wait: false })
  expect(status.drop).toMatch(/\$0\.100/)
})
