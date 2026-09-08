/* Read-only structural checks for the current monolithic HTML.
 * node tests/source_contracts.cjs --baseline /path/to/pre-edit-source.html
 * proves that a comment-only change leaves every executable JS AST identical.
 * AST equivalence does not prove browser/runtime behavior; run smoke tests too.
 */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const acorn = require('acorn');
const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'src/skystudee.html'), 'utf8');

function scripts(html) {
  return [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script\s*>/gi)].map(m => m[1]);
}
function parse(code) {
  const comments = [];
  const ast = acorn.parse(code, {ecmaVersion: 'latest', sourceType: 'script', onComment: comments});
  return {ast, comments};
}
function semanticAst(ast) {
  // Offsets/raw spelling necessarily move with comments. Preserve actual
  // literals, operators, structure, statements and template-string values.
  return JSON.stringify(ast, (key, value) =>
    ['start', 'end', 'loc', 'range', 'raw'].includes(key) ? undefined : value);
}
const parsed = scripts(source).map(parse);
assert.ok(parsed.length > 0, 'No executable script found');
let documented = 0;
for (const [index, {ast, comments}] of parsed.entries()) {
  const code = scripts(source)[index];
  for (const node of ast.body.filter(n => n.type === 'FunctionDeclaration')) {
    const comment = comments.filter(c => c.type === 'Block' && c.value.startsWith('*') && c.end <= node.start).at(-1);
    assert.ok(comment && !code.slice(comment.end, node.start).trim(), `Missing JSDoc immediately before ${node.id.name}`);
    documented++;
  }
}
const markup = source.replace(/<script\b[^>]*>[\s\S]*?<\/script\s*>/gi, '')
  .replace(/<style\b[^>]*>[\s\S]*?<\/style\s*>/gi, '').replace(/<!--[\s\S]*?-->/g, '');
const ids = [...markup.matchAll(/\bid="([^"]+)"/g)].map(m => m[1]);
assert.equal(new Set(ids).size, ids.length, 'Duplicate static DOM ID');
for (const match of scripts(source).join('\n').matchAll(/getElementById\("([^"]+)"\)/g)) {
  assert.ok(ids.includes(match[1]), `Missing DOM node for getElementById(${match[1]})`);
}
const idx = process.argv.indexOf('--baseline');
if (idx >= 0) {
  assert.ok(process.argv[idx + 1], '--baseline needs a file path');
  const baseline = fs.readFileSync(process.argv[idx + 1], 'utf8');
  assert.deepEqual(parsed.map(p => semanticAst(p.ast)), scripts(baseline).map(c => semanticAst(parse(c).ast)), 'Executable JavaScript changed');
  // Style declarations remain unchanged, not merely visually similar. CSS
  // comment removal is safe for these sources (no comment-like string values).
  const styles = html => [...html.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style\s*>/gi)]
    .map(m => m[1].replace(/\/\*[\s\S]*?\*\//g, '').replace(/\s+/g, ' ').trim());
  assert.deepEqual(styles(source), styles(baseline), 'Style declarations changed');
  console.log('PASS: JavaScript AST and stylesheet content equal baseline');
}
console.log(`PASS: ${documented} documented top-level functions; ${ids.length} static DOM IDs; script syntax`);
