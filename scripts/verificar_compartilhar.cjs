// node scripts/verificar_compartilhar.cjs <caminho-do-playwright-core>
const assert = require('node:assert/strict');
const {chromium} = require(process.argv[2] || 'playwright-core');
(async () => {
  const browser = await chromium.launch({headless: true});
  try {
    const page = await browser.newPage();
    const erros = [];
    page.on('pageerror', e => erros.push(e.message));
    for (const [width, lang, nome] of [[1366, 'pt', 'Compartilhar'], [800, 'pt', 'Compartilhar'], [390, 'en', 'Share']]) {
      await page.setViewportSize({width, height: 900});
      await page.goto('http://127.0.0.1:5000/?lang=' + lang, {waitUntil: 'domcontentloaded'});
      await page.getByRole('button', {name: nome, exact: true}).click();
      const modal = page.locator('#modal-compartilhar');
      await modal.waitFor({state: 'visible'});
      await modal.locator('img').evaluate(img => img.decode());
      assert.equal(await modal.locator('img').evaluate(img => img.naturalWidth), 1024);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
      const download = page.waitForEvent('download');
      await modal.locator('a[download]').click();
      assert.equal((await download).suggestedFilename(), 'qrcode-munguba.png');
      await page.evaluate(() => Promise.all(document.getAnimations().map(a => a.finished.catch(() => {}))));
      await page.screenshot({path: `artifacts/compartilhar-${width}.png`});
      await page.keyboard.press('Escape');
      await page.waitForFunction(() => !document.body.classList.contains('no-scroll'));
      assert.equal(await modal.evaluate(d => d.open), false);
      assert.equal(await page.evaluate(() => document.body.classList.contains('no-scroll')), false);
    }
    assert.deepEqual(erros, []);
    console.log('Compartilhar: QR original, download, fechar, celular, tablet e PT/EN verificados.');
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exit(1); });
