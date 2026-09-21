const CODE_DUMP_RE = /Traceback \(most recent call last\)|AssertionError:|File "\/.+?\.py"|app\.framework\.|build_test_case|<locals>|unittest\b|at [\w.$]+ \(.+:\d+:\d+\)/i
const HTML_RE = /<!DOCTYPE|<html[\s>]/i
const PATH_RE = /(?:\/Users\/|\/home\/|[A-Za-z]:\\)[^\s"']+/g

export function looksLikeCodeDump(text) {
  const value = String(text || '')
  if (!value) return false
  return CODE_DUMP_RE.test(value) || HTML_RE.test(value)
}

export function humanizeUserMessage(text, fallback = '操作失败，请稍后重试') {
  let value = String(text || '').replace(PATH_RE, '').trim()
  if (!value) return fallback
  if (HTML_RE.test(value)) return fallback

  const assertHit = value.match(/断言失败[^\n]*/)
  if (assertHit) return assertHit[0].replace(/^AssertionError:[^\n]*:\s*/, '').trim()

  const wrapped = value.match(/AssertionError:[^\n]*:\s*(.+)$/m)
  if (wrapped && wrapped[1] && /[\u4e00-\u9fff]/.test(wrapped[1])) {
    return wrapped[1].trim()
  }

  if (looksLikeCodeDump(value)) {
    const chinese = value.split('\n').map(line => line.trim()).find(line => /[\u4e00-\u9fff]/.test(line) && !looksLikeCodeDump(line))
    return chinese || fallback
  }

  if (value.length > 180) {
    return `${value.slice(0, 180)}…`
  }
  return value
}

export function humanizeEvent(event, outcome) {
  const map = {
    startTest: '开始执行',
    addSuccess: '执行通过',
    addFailure: '执行失败',
    addError: '执行异常',
    addSkip: '已跳过',
    stopTest: '执行结束'
  }
  return map[event] || ({
    success: '成功',
    failure: '失败',
    error: '异常',
    skip: '跳过',
    running: '进行中',
    stopped: '已结束'
  }[outcome] || '执行记录')
}

export function humanizeAssertion(item) {
  return humanizeUserMessage(item, '断言未通过')
}

export function userFacingLogs(lines) {
  return (lines || [])
    .map(line => humanizeUserMessage(line, ''))
    .filter(line => line && !looksLikeCodeDump(line) && !/^TestResult\./.test(line))
}

export function userFacingFailures(list) {
  const rows = (list || []).map(item => humanizeUserMessage(item, '')).filter(Boolean)
  return rows.length ? rows : []
}
