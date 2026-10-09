const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const postcss = require('postcss');
const { parse } = require('vue/compiler-sfc');

const source = path.resolve(__dirname, '../src');
const files = [];
function walk(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const file = path.join(directory, entry.name);
    if (entry.isDirectory()) walk(file);
    else if (/\.(vue|css)$/.test(file)) files.push(file);
  }
}
walk(source);
let declarations = 0;
for (const file of files) {
  const text = fs.readFileSync(file, 'utf8');
  const descriptor = file.endsWith('.vue') ? parse(text).descriptor : null;
  const styles = descriptor ? descriptor.styles : [{ content: text }];
  if (descriptor?.template) {
    const surfaces = new Set(['insights-panel', 'getting-started-panel', 'account-health-panel', 'create-panel', 'management-panel', 'action-panel', 'transfer-result-panel', 'records-section', 'entry-form-section', 'status-card', 'chart-card', 'source-card', 'preview-card', 'success-panel', 'trip-card']);
    for (const match of descriptor.template.content.matchAll(/(?<![:\w-])class="([^"]*)"/g)) {
      const classes = match[1].split(/\s+/);
      if (classes.some(name => surfaces.has(name))) assert(classes.includes('app-surface'), `${file}: migrated surface requires app-surface`);
      if (classes.some(name => ['primary-action', 'page-add-button'].includes(name))) assert(classes.includes('app-primary-action'), `${file}: primary action requires app-primary-action`);
    }
  }
  for (const style of styles) {
    // Only inspect repository CSS; never follow sourceMappingURL file references.
    const root = postcss.parse(style.content, { from: file, map: false });
    root.walkDecls(() => declarations++);
    // These consolidated components must not accumulate another override layer.
    if (/\/(HomeView|Navbar)\.vue$/.test(file)) {
      assert.equal(styles.length, 1, `${file}: keep one style block`);
      const selectors = new Set();
      function inspect(parent, scope = 'root') {
        for (const node of parent.nodes || []) {
          if (node.type === 'rule') {
            const key = `${scope}|${node.selector.replace(/\s+/g, ' ').trim()}`;
            assert(!selectors.has(key), `${file}: duplicate ${node.selector} in ${scope}`);
            selectors.add(key);
            const props = new Set();
            node.walkDecls(decl => {
              assert(!props.has(decl.prop), `${file}: duplicate ${node.selector} ${decl.prop}`);
              props.add(decl.prop);
            });
          } else if (node.nodes) inspect(node, `${scope}/@${node.name} ${node.params || ''}`);
        }
      }
      inspect(root);
    }
  }
}
const globalStyles = fs.readFileSync(path.join(source, 'assets/style.css'), 'utf8');
assert(!/#app\s+:is\(\.page-add-button,\s*\.primary-action\)/.test(globalStyles), 'Do not restore legacy primary-button overrides');
assert(!/#app\s+:is\(\.insights-panel,/.test(globalStyles), 'Do not restore page-name surface overrides');
const primitives = postcss.parse(fs.readFileSync(path.join(source, 'assets/ui.css'), 'utf8'), { map: false });
primitives.walkRules(rule => assert(!rule.selector.includes('#app'), 'Shared UI classes must not use ID specificity'));
console.log(`CSS checks passed: ${files.length} files, ${declarations} declarations; consolidated selectors and opt-in primitives guarded.`);
