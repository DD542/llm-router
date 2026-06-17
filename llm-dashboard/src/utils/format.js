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

const RAMP = ['#EE8A3F', '#6E7F92', '#4BBE8A', '#5B9BD6', '#C98AE0', '#E5687B']
const _assigned = {}
let _i = 0
export function modelColor(name) {
  if (!_assigned[name]) { _assigned[name] = RAMP[_i % RAMP.length]; _i++ }
  return _assigned[name]
}