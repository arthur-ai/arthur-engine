import type { EngineInterface, Register } from 'claude-code'

// USD per million tokens by model id prefix (list prices; edit for your contract). Cache
// writes are priced at the 1-hour rate (2x input): the usage a mod sees does
// not say which cache was written, so this errs high rather than low.
const RATES: Record<string, { input: number; output: number; cacheWrite: number; cacheRead: number }> = {
  'claude-haiku-4-5': { input: 1, output: 5, cacheWrite: 2, cacheRead: 0.1 },
  'claude-sonnet': { input: 3, output: 15, cacheWrite: 6, cacheRead: 0.3 },
  'claude-opus': { input: 5, output: 25, cacheWrite: 10, cacheRead: 0.5 },
}
const WINDOW_MS = 5 * 60 * 1000
const OVERRIDE_MS = 10 * 60 * 1000
const COMMAND = /^\s*breaker\s+(status|override|reset)\s*$/i

type Entry = [number, number] // [epoch ms, USD] per model request

function rateFor(model: string) {
  const key = Object.keys(RATES).find(prefix => model.startsWith(prefix))
  return key ? RATES[key] : RATES['claude-opus'] // unknown model: price high, not at zero
}

// Spend and the override live in $.store, so they outlast the session.
async function load($: EngineInterface): Promise<Entry[]> {
  return ((await $.store.get('spend')) as Entry[] | undefined) ?? []
}

async function cap($: EngineInterface): Promise<number> {
  return Number((await $.env.get('ARTHUR_BREAKER_CAP_USD')) ?? '0.10')
}

function windowSpend(spend: Entry[], now: number): number {
  return spend.filter(([t]) => now - t <= WINDOW_MS).reduce((sum, [, usd]) => sum + usd, 0)
}

async function overridden($: EngineInterface, now: number): Promise<boolean> {
  return Number((await $.store.get('overrideUntil')) ?? 0) > now
}

async function record($: EngineInterface, usd: number): Promise<number> {
  const now = Date.now()
  const spend = (await load($)).filter(([t]) => now - t <= WINDOW_MS)
  spend.push([now, usd])
  await $.store.set('spend', spend)
  $.ui.status(`spend breaker: $${windowSpend(spend, now).toFixed(4)} / $${await cap($)} in 5 min`)
  return windowSpend(spend, now)
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

    // Watch the answer as it streams: if its output alone would cross the cap,
    // stop reading, which ends the request mid-answer.
    const c = await cap($)
    const before = windowSpend(await load($), Date.now())
    const override = await overridden($, Date.now())
    const out = rateFor(e.model ?? '').output
    const stream = next(e)
    let text = ''
    let lastIndex = 0
    for (let r = await stream.next(); ; r = await stream.next()) {
      if (r.done) {
        const result = r.value
        if (result?.usage) {
          const u = result.usage
          const rate = rateFor(u.model)
          const usd =
            (u.input_tokens * rate.input +
              u.output_tokens * rate.output +
              u.cache_creation_input_tokens * rate.cacheWrite +
              u.cache_read_input_tokens * rate.cacheRead) /
            1_000_000
          const total = await record($, usd)
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
      const estimate = ((text.length / 4) * out) / 1_000_000
      if (!override && before + estimate >= c) {
        await stream.return?.(undefined as any)
        await record($, estimate)
        const note = `\n\n[Arthur spend breaker: stopped this answer mid-stream at ~$${(before + estimate).toFixed(4)} (cap $${c}).]`
        $.ui.log(`arthur-breaker: cut step ${e.index} mid-stream after ${text.length} chars`)
        yield { kind: 'text', index: lastIndex, text: note }
        return { turnId: e.turnId, index: e.index, answer: text + note, toolUses: [], stopReason: 'end_turn', usage: null }
      }
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
        await $.store.set('spend', [])
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
