import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import test from 'node:test';
import vm from 'node:vm';

const read = (path) => readFileSync(new URL('../' + path, import.meta.url), 'utf8');
const source = read('public/us-wizard-engine.js');
const data = JSON.parse(read('public/wizard_cities.json'));
const helpers = source.slice(source.indexOf('  function esc('), source.indexOf('  // ---- 单实例挂载'));
const results = source.slice(source.indexOf('    function results()'), source.indexOf('    function submitLead()'));

function render(city, preferences = {}) {
  const view = { innerHTML: '', querySelector: () => ({ addEventListener() {} }) };
  const context = { S: { destCity: city, dest: 'A university', notes: '', ...preferences }, view,
    IMG: 'https://img.unistay.cn/', submitLead() { throw Error('must not submit'); } };
  vm.createContext(context);
  vm.runInContext(helpers + results + '\nresults();', context);
  return view.innerHTML;
}
const links = (html) => [...html.matchAll(/href="(\/fangyuan\/[^\"]+)"/g)].map(m => m[1]);

test('preferences do not change city references and their limitation is explicit', () => {
  const city = data.cities[0];
  const low = render(city, { budget: 'Under $1,400', room: '整套公寓', movein: '9月 2026' });
  const high = render(city, { budget: '$2,400+', room: '独卫单间', movein: '12月 2026' });
  assert.deepEqual(links(low), links(high));
  assert.deepEqual(links(low), city.props.slice(0, 3).map(p => '/fangyuan/' + p.s + '/'));
  assert.match(low, /不按预算、房型、入住时间或备注筛选/);
  assert.match(low, /不代表距离学校最近/);
  assert.doesNotMatch(low, /AI|已核实匹配|77 万/);
});

test('university still resolves to its city, unknown input resolves to null', () => {
  const context = { WZ: data, unis: data.unis,
    cityByName: Object.fromEntries(data.cities.map(c => [c.name.toLowerCase(), c])) };
  vm.createContext(context); vm.runInContext(helpers, context);
  const university = data.unis[0];
  assert.equal(context.resolveCity(university.n).slug, university.c);
  assert.equal(context.resolveCity('__unknown_university__'), null);
  assert.equal(context.resolveCity(''), null);
});

test('missing and invalid price is unknown, not zero or an exception', () => {
  for (const price of [null, undefined, 0, NaN, Infinity, -10]) {
    const city = { ...data.cities[0], props: [{ ...data.cities[0].props[0], p: price }] };
    assert.match(render(city), /价格待核实/);
  }
});

test('empty inventory does not manufacture references; notes remain escaped', () => {
  assert.match(render({ ...data.cities[0], props: [] }), /暂无房源参考/);
  const html = render(data.cities[0], { notes: '<img src=x onerror=alert(1)>' });
  assert.match(html, /待核实事项/);
  assert.match(html, /&lt;img/);
  assert.doesNotMatch(html, /<img src=x/);
});

test('inline, modal, header, home and disclaimer share truthful claims', () => {
  for (const path of ['src/components/UsAiWizard.astro', 'src/components/AiWizardModal.astro',
    'src/components/Header.astro', 'src/pages/index.astro', 'src/pages/disclaimer.astro']) {
    const text = read(path).replace(/\/\/[^\n]*/g, '');
    assert.doesNotMatch(text, /AI 帮我找房|AI 找房匹配|77 万条真实评价|匹配你条件的已核实房源/);
  }
  assert.match(read('src/components/AiWizardModal.astro'), /aria-label="城市找房向导"/);
  assert.match(source, /填写联系方式并提交后，顾问才会收到/);
});

test('lead submission and completion handlers remain byte-for-byte unchanged', () => {
  const handlers = source.slice(source.indexOf('    function submitLead()'), source.indexOf('    function bindBack(fn)'));
  assert.equal(createHash('sha256').update(handlers).digest('hex'),
    '2d8ed1f8a95ac2a0ace565191fee51c9a0e6643588702af56c8f8deccc427f93');
});
