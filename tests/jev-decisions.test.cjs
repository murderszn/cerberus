const { test } = require('node:test');
const assert = require('node:assert/strict');
const { requestFor, queueFor } = require('../assets/jev-decisions.js');
const items = ['first', 'second', 'third'].map(id => ({ id, name: id, severity: 'high', observation: 'Observed catalog failure', risk: 'Potential exposure', action: 'Verify evidence', evidence: [{ snippet: 'MUST NOT SEND', path: 'private.js' }] }));
test('Request sends bounded finding summaries without source evidence', () => {
  const payload = requestFor(items);
  assert.equal(Object.keys(payload.questions).length, 3);
  assert.ok(!JSON.stringify(payload).includes('MUST NOT SEND'));
  assert.ok(!JSON.stringify(payload).includes('private.js'));
});
test('Jev decisions drive grouping, not scanner severity or input order', () => {
  const answers = Object.fromEntries(['maintain', 'contain', 'investigate'].map((choice, i) => ['check_' + i, { choice, probabilities: { [choice]: .9 } }]));
  const queue = queueFor(items, { answers });
  assert.deepEqual(queue.map(entry => entry.item.id), ['second', 'third', 'first']);
  assert.deepEqual(queue.map(entry => entry.action), ['contain', 'investigate', 'maintain']);
});
test('Missing or invalid probabilities cannot become a successful queue', () => {
  assert.throws(() => queueFor(items, { answers: {} }));
  assert.throws(() => queueFor(items.slice(0, 1), { answers: { check_0: { choice: 'contain', probabilities: { contain: 9 } } } }));
});
