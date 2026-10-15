import type { EngineInterface, Register } from 'claude-code'

// USD per million tokens by model id prefix, from Anthropic's list prices; edit
// for your contract. The first matching prefix wins, so specific ids come before
// their family. Cache writes are priced at the 1-hour rate: the usage a mod sees
// does not say which cache was written, so this errs high rather than low.
type Rate = { input: number; output: number; cacheWrite: number; cacheRead: number }
const RATES: [string, Rate][] = [
  ['claude-fable-5-1', { input: 10, output: 50, cacheWrite: 20, cacheRead: 0.25 }],
  ['claude-mythos-5-1', { input: 10, output: 50, cacheWrite: 20, cacheRead: 0.25 }],
  ['claude-fable', { input: 10, output: 50, cacheWrite: 20, cacheRead: 1 }],
  ['claude-mythos', { input: 10, output: 50, cacheWrite: 20, cacheRead: 1 }],
  ['claude-opus-5-5', { input: 4, output: 20, cacheWrite: 8, cacheRead: 0.2 }],
  ['claude-opus-4-1', { input: 15, output: 75, cacheWrite: 30, cacheRead: 1.5 }],
  ['claude-opus-4-0', { input: 15, output: 75, cacheWrite: 30, cacheRead: 1.5 }],
  ['claude-opus-4-2025', { input: 15, output: 75, cacheWrite: 30, cacheRead: 1.5 }], // Opus 4 by date
  ['claude-opus', { input: 5, output: 25, cacheWrite: 10, cacheRead: 0.5 }], // Opus 4.5 to 5
  ['claude-sonnet-5-5', { input: 2, output: 10, cacheWrite: 4, cacheRead: 0.1 }],
  ['claude-sonnet-5', { input: 2, output: 10, cacheWrite: 4, cacheRead: 0.2 }],
  ['claude-sonnet', { input: 3, output: 15, cacheWrite: 6, cacheRead: 0.3 }], // Sonnet 4 to 4.6
  ['claude-haiku-5-5', { input: 0.1, output: 0.5, cacheWrite: 0.2, cacheRead: 0.01 }], // prompts up to 100K
  ['claude-haiku-4-5', { input: 1, output: 5, cacheWrite: 2, cacheRead: 0.1 }],
]
// Claude Haiku 5.5 costs five times as much once a prompt passes 100,000 tokens.
const HAIKU_5_5_LONG: Rate = { input: 0.5, output: 2.5, cacheWrite: 1, cacheRead: 0.05 }
// A model with no row is priced at the highest rate of each kind, never at zero.
const UNKNOWN: Rate = {
  input: Math.max(...RATES.map(([, r]) => r.input)),
  output: Math.max(...RATES.map(([, r]) => r.output)),
  cacheWrite: Math.max(...RATES.map(([, r]) => r.cacheWrite)),
  cacheRead: Math.max(...RATES.map(([, r]) => r.cacheRead)),
}
const WINDOW_MS = 5 * 60 * 1000
const OVERRIDE_MS = 10 * 60 * 1000
const COMMAND = /^\s*breaker\s+(status|override|reset)\s*$/i

const DEFAULT_CAP_USD = 0.1
const SPEND_PREFIX = 'spend:'

type Entry = [number, number] // [epoch ms, USD] per model request

// Prompt size in tokens (input + cache write + cache read) of the last finished
// request, per conversation (main, or a subagent's id). A request cut mid-stream
// returns no usage, so its input side is estimated from that: the next request
// resends the same conversation, mostly as cache reads.
const lastPromptTokens = new Map<string, number>()
let capWarned = false

function rateFor(model: string, promptTokens = 0): Rate {
  const row = RATES.find(([prefix]) => model.startsWith(prefix))
  if (!row) return UNKNOWN
  return row[0] === 'claude-haiku-5-5' && promptTokens > 100_000 ? HAIKU_5_5_LONG : row[1]
}

// Spend lives in $.store, so it outlasts the session. Every session shares the
// store and a get-then-set is not atomic, so each request is its own key,
// `spend:<epoch ms>:<request>`: concurrent writers never overwrite each other.
async function load($: EngineInterface): Promise<Entry[]> {
  const now = Date.now()
  const entries: Entry[] = []
  for (const key of await $.store.keys()) {
    if (!key.startsWith(SPEND_PREFIX)) continue
    const at = Number(key.split(':')[1])
    if (!(now - at <= WINDOW_MS)) {
      await $.store.delete(key) // out of the window: it can't count again
      continue
    }
    entries.push([at, Number((await $.store.get(key)) ?? 0)])
  }
  return entries
}

async function clearSpend($: EngineInterface): Promise<void> {
  for (const key of await $.store.keys()) {
    if (key.startsWith(SPEND_PREFIX)) await $.store.delete(key)
  }
}

// A cap that is not a positive number would disable the breaker (NaN compares
// false) or pause everything (zero), so it falls back to the default instead.
async function cap($: EngineInterface): Promise<number> {
  const raw = await $.env.get('ARTHUR_BREAKER_CAP_USD')
  const value = raw === undefined ? DEFAULT_CAP_USD : Number(raw)
  if (Number.isFinite(value) && value > 0) return value
  if (!capWarned) {
    capWarned = true
    $.ui.log(`arthur-spend-breaker: ARTHUR_BREAKER_CAP_USD=${JSON.stringify(raw)} is not a positive number; using $${DEFAULT_CAP_USD}`)
  }
  return DEFAULT_CAP_USD
}

function windowSpend(spend: Entry[], now: number): number {
  return spend.filter(([t]) => now - t <= WINDOW_MS).reduce((sum, [, usd]) => sum + usd, 0)
}

async function overridden($: EngineInterface, now: number): Promise<boolean> {
  return Number((await $.store.get('overrideUntil')) ?? 0) > now
}

async function record($: EngineInterface, usd: number, request: string): Promise<number> {
  const now = Date.now()
  await $.store.set(`${SPEND_PREFIX}${now}:${request}`, usd)
  const total = windowSpend(await load($), now)
  $.ui.status(`spend breaker: $${total.toFixed(4)} / $${await cap($)} in 5 min`)
  return total
}

async function tripped($: EngineInterface): Promise<string | undefined> {
  const now = Date.now()
  if (await overridden($, now)) return undefined
  const spent = windowSpend(await load($), now)
  const c = await cap($)
  return spent >= c
    ? `Arthur spend breaker: $${spent.toFixed(4)} spent in the last 5 min (cap $${c}). Paused. Type "breaker override" to lift it for 10 min.`
    : undefined
}

export const register: Register = on => {
  // Every model request of every turn, subagents included, passes through here.
  on('turn.step', async function* ($, e, next) {
    const stop = await tripped($)
    if (stop) {
      // Answer in the model's place: no request is sent, so nothing is spent.
      $.ui.log(`arthur-breaker: blocked step ${e.index} of turn ${e.turnId}`)
      yield { kind: 'text', index: 0, text: stop }
      return { turnId: e.turnId, index: e.index, answer: stop, toolUses: [], stopReason: 'end_turn', usage: null }
    }

    // Watch the answer as it streams: if this request's cost would cross the
    // cap, stop reading, which ends the request mid-answer.
    const c = await cap($)
    const before = windowSpend(await load($), Date.now())
    const override = await overridden($, Date.now())
    const conversation = e.agentId ?? 'main'
    const request = `${conversation}:${e.turnId}:${e.index}`
    const promptGuess = lastPromptTokens.get(conversation) ?? 0
    const out = rateFor(e.model ?? '', promptGuess).output
    const inputGuess = (promptGuess * rateFor(e.model ?? '', promptGuess).cacheRead) / 1_000_000
    const stream = next(e)
    let text = ''
    let lastIndex = 0
    // Spend is written once per request, however it ends: finished, cut here,
    // interrupted by the user (Esc returns this generator at a yield), or failed
    // partway. The last two have no usage, so they record the running estimate.
    let recorded = false
    try {
      for (let r = await stream.next(); ; r = await stream.next()) {
        if (r.done) {
          const result = r.value
          if (result?.usage) {
            const u = result.usage
            const promptTokens = u.input_tokens + u.cache_creation_input_tokens + u.cache_read_input_tokens
            const rate = rateFor(u.model, promptTokens)
            const usd =
              (u.input_tokens * rate.input +
                u.output_tokens * rate.output +
                u.cache_creation_input_tokens * rate.cacheWrite +
                u.cache_read_input_tokens * rate.cacheRead) /
              1_000_000
            lastPromptTokens.set(conversation, promptTokens)
            recorded = true
            const total = await record($, usd, request)
            $.ui.log(`arthur-breaker: step ${e.index} ${u.model} $${usd.toFixed(4)}; window $${total.toFixed(4)}`)
          }
          return result
        }
        const chunk = r.value
        if (chunk.kind === 'text') {
          text += chunk.text
          lastIndex = chunk.index
        }
        yield chunk
        // This request's cost so far: its input side (the previous prompt's size,
        // at the cache-read price) plus the answer so far (about four characters a token).
        const estimate = inputGuess + ((text.length / 4) * out) / 1_000_000
        if (!override && before + estimate >= c) {
          await stream.return?.(undefined as any)
          recorded = true
          await record($, estimate, request)
          const note = `\n\n[Arthur spend breaker: stopped this answer mid-stream at ~$${(before + estimate).toFixed(4)} (cap $${c}).]`
          $.ui.log(`arthur-breaker: cut step ${e.index} mid-stream after ${text.length} chars`)
          yield { kind: 'text', index: lastIndex, text: note }
          return { turnId: e.turnId, index: e.index, answer: text + note, toolUses: [], stopReason: 'end_turn', usage: null }
        }
      }
    } finally {
      const estimate = inputGuess + ((text.length / 4) * out) / 1_000_000
      if (!recorded && estimate > 0) await record($, estimate, request)
    }
  })

  // Commands, and while tripped a new prompt never starts a turn.
  on('prompt.submit', async ($, e, next) => {
    const m = COMMAND.exec(e.text)
    if (m) {
      const now = Date.now()
      const verb = m[1].toLowerCase()
      if (verb === 'override') await $.store.set('overrideUntil', now + OVERRIDE_MS)
      if (verb === 'reset') {
        await clearSpend($)
        await $.store.set('overrideUntil', 0)
      }
      const spent = windowSpend(await load($), now)
      const until = Number((await $.store.get('overrideUntil')) ?? 0)
      const lifted = until > now ? `; lifted until ${new Date(until).toISOString().slice(11, 19)} UTC` : ''
      // The command itself never reaches the model, so it costs nothing.
      return { drop: `Arthur spend breaker ${verb}: $${spent.toFixed(4)} in the last 5 min (cap $${await cap($)})${lifted}.` }
    }
    const stop = await tripped($)
    return stop ? { drop: stop } : next(e)
  }).catch(($, e, next) =>
    next.called ? next(e) : { drop: 'Arthur spend breaker could not check spend, so the prompt was held.' },
  )
}
