export function usd(v) {
  if (!v) return '$0'
  const s = v.toFixed(4).replace(/0+$/, '').replace(/\.$/, '')
  return '$' + s
}
export function pct(v, digits = 0) {
  return (v * 100).toFixed(digits) + '%'
}
export function shortModel(name) {
  if (!name) return '—'
  return name.replace('local/', '').replace('groq/', '').replace('anthropic/', '')
}

const RAMP = ['#46C7B6', '#C98A4B', '#6C8FD6', '#B86BD0', '#7CC36B', '#D6A14F']
const _assigned = {}
let _i = 0
export function modelColor(name) {
  if (!_assigned[name]) { _assigned[name] = RAMP[_i % RAMP.length]; _i++ }
  return _assigned[name]
}
