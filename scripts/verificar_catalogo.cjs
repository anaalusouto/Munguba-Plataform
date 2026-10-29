// node scripts/verificar_catalogo.cjs <caminho-do-playwright-core>
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { chromium } = require(process.argv[2] || 'playwright-core');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  const erros = [];
  page.on('pageerror', e => erros.push(e.message));
  const inicio = Date.now();
  const response = await page.goto('http://127.0.0.1:5000/?lang=pt', { waitUntil: 'domcontentloaded' });
  assert.equal(response.status(), 200);
  assert.equal(await page.locator('.card-planta').count(), 0);
  const abrir = Date.now();
  await page.getByRole('button', { name: 'Acessar Catálogo', exact: true }).click();
  await page.locator('.card-planta').nth(23).waitFor();
  const tempoAbrir = Date.now() - abrir;
  assert.equal(await page.locator('.card-planta').count(), 24);
  await page.getByRole('button', { name: 'Mostrar mais espécies', exact: true }).click();
  assert.equal(await page.locator('.card-planta').count(), 48);
  const busca = page.getByRole('textbox', { name: 'Pesquisar espécies', exact: true });
  const tempoBuscaInicio = Date.now();
  await busca.fill('Anacardium occidentale');
  await page.waitForFunction(() => document.querySelectorAll('.card-planta').length === 1);
  const tempoBusca = Date.now() - tempoBuscaInicio;
  assert.match(await page.locator('.card-planta').innerText(), /Anacardium occidentale/);
  await page.locator('.card-planta').click();
  await page.locator('#detalhe-conteudo h2').waitFor();
  assert.match(await page.locator('#detalhe-conteudo').innerText(), /Anacardium occidentale/);
  const imagem = page.locator('#detalhe-conteudo img').first();
  await imagem.evaluate(img => img.decode());
  assert.equal(await imagem.evaluate(img => img.naturalWidth > 0), true);
  await page.getByRole('button', { name: 'Fechar ficha', exact: true }).click();
  await busca.fill('Werauhia gigantea');
  await page.waitForFunction(() => document.querySelectorAll('.card-planta').length === 1 &&
    document.querySelector('.card-planta').textContent.includes('Werauhia gigantea'));
  assert.ok(Number(await page.locator('.card-planta').getAttribute('data-taxon-id')) > 24);
  await busca.fill('zzzzzzsemresultado');
  await page.locator('#catalogo-vazio').waitFor({ state: 'visible' });
  assert.equal(await page.locator('.card-planta').count(), 0);
  await page.getByRole('button', { name: 'Limpar', exact: true }).click();
  assert.equal(await page.locator('.card-planta').count(), 24);
  const categoria = page.locator('.btn-categoria').first();
  await categoria.click();
  const categoriaAtiva = await page.evaluate(() => filtrosAtivos.categoria);
  assert.equal(await page.evaluate(cat => Array.from(document.querySelectorAll('.card-planta'))
    .every(c => plantasCatalogo.find(p => p.id === Number(c.dataset.taxonId)).tags.includes(cat)), categoriaAtiva), true);
  await page.locator('.checkbox-parte:visible').first().check();
  assert.equal(await page.evaluate(() => Array.from(document.querySelectorAll('.card-planta')).every(c => {
    const p = plantasCatalogo.find(p => p.id === Number(c.dataset.taxonId));
    return filtrosAtivos.partes.every(parte => p.partes.includes(parte));
  })), true);
  await page.getByRole('button', { name: 'Fechar catálogo', exact: true }).last().click();
  await page.evaluate(() => { abrirCatalogo(); limparTodosFiltros(); });
  await page.evaluate(() => Promise.all(document.getAnimations().map(a => a.finished.catch(() => {}))));
  assert.equal(await page.locator('#modal-catalogo').evaluate(e => getComputedStyle(e).opacity), '1');
  assert.equal(await page.locator('#grid-plantas').evaluate(e => getComputedStyle(e).display), 'grid');
  await page.screenshot({ path: 'artifacts/catalogo-otimizado-desktop.png' });
  await page.evaluate(() => fecharCatalogo());
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => abrirCatalogo());
  await page.evaluate(() => Promise.all(document.getAnimations().map(a => a.finished.catch(() => {}))));
  await page.screenshot({ path: 'artifacts/catalogo-otimizado-mobile.png' });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
  await page.goto('http://127.0.0.1:5000/?lang=en', { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => abrirCatalogo());
  assert.equal(await page.locator('.card-planta').count(), 24);
  assert.match(await page.locator('#catalogo-contagem').innerText(), /Showing 24 of 523/);
  assert.deepEqual(erros, []);
  const resultado = { homeMs: abrir - inicio, abrirCatalogoMs: tempoAbrir, buscaComDebounceMs: tempoBusca,
    cartoesIniciais: 24, especiesPesquisaveis: 523, errosJavascript: erros, pt: 'ok', en: 'ok', mobile: 'ok' };
  fs.writeFileSync('artifacts/catalogo-verificacao.json', JSON.stringify(resultado, null, 2));
  console.log(JSON.stringify(resultado));
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
