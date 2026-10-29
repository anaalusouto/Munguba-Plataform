// node scripts/verificar_referencias_mapa.cjs <caminho-do-playwright-core>
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { chromium } = require(process.argv[2] || 'playwright-core');

(async () => {
  const browser = await chromium.launch({headless: true});
  try {
    const page = await browser.newPage({viewport: {width: 1366, height: 1000}});
    const erros = [];
    page.on('pageerror', e => erros.push(e.message));
    await page.goto('http://127.0.0.1:5000/?lang=pt', {waitUntil: 'domcontentloaded'});
    await page.waitForFunction(() => typeof L !== 'undefined' && referenciasCarregadas, {timeout: 20000});
    assert.equal(await page.evaluate(() => markers.length), 260);
    assert.equal(await page.evaluate(() => areasReferencia.length), 1);
    assert.equal(await page.evaluate(() => map.hasLayer(areasReferencia[0].camada)), true);
    assert.match(await page.locator('#referencias-status').innerText(), /424/);
    assert.equal(await page.evaluate(() => areasReferencia[0].camada.getLayers()[0].getRadius()), 3416);
    await page.locator('#mapid').scrollIntoViewIfNeeded();
    const ponto = await page.evaluate(() => {
      const p = map.latLngToContainerPoint(markers[130].getLatLng());
      return {x: p.x, y: p.y};
    });
    await page.locator('#mapid').click({position: ponto});
    assert.match(await page.locator('.leaflet-popup-content').innerText(), /Ocorrência/);
    await page.evaluate(() => { areasReferencia[0].camada.openPopup([areasReferencia[0].lat, areasReferencia[0].lng]); });
    await page.locator('.referencia-popup').waitFor();
    assert.match(await page.locator('.referencia-popup').innerText(), /3\.416/);
    assert.equal(await page.locator('.lista-plantas > button').count(), 20);
    await page.locator('.referencia-popup > button').click();
    assert.equal(await page.locator('.lista-plantas > button').count(), 40);
    const buscar = page.getByRole('searchbox', {name: 'Buscar planta nesta área...'});
    await buscar.fill('Abarema cochliacarpos');
    assert.equal(await page.locator('.lista-plantas > button').count(), 1);
    await page.locator('.lista-plantas > button').click();
    await page.locator('#detalhe-conteudo h2').waitFor();
    assert.match(await page.locator('#detalhe-conteudo').innerText(), /Abarema cochliacarpos/);
    await page.getByRole('button', {name: 'Fechar ficha', exact: true}).click();
    await page.locator('#mostrar-referencias').uncheck();
    assert.equal(await page.evaluate(() => map.hasLayer(areasReferencia[0].camada)), false);
    await page.locator('#mostrar-referencias').check();
    assert.equal(await page.evaluate(() => map.hasLayer(areasReferencia[0].camada)), true);
    await page.evaluate(() => filtrarMapaUnico('Medicinal e farmacológico'));
    assert.equal(await page.evaluate(() => plantasDaArea(areasReferencia[0]).every(t => plantasMapa[t.id - 1].tags.includes(categoriaMapa))), true);
    await page.evaluate(() => resetarMapa());
    await page.locator('#mapid').scrollIntoViewIfNeeded();
    await page.evaluate(() => { areasReferencia[0].camada.openPopup([areasReferencia[0].lat, areasReferencia[0].lng]); });
    await page.waitForFunction(() => !map._animatingZoom && !map._panAnim?._inProgress);
    await page.locator('#mapid').screenshot({path: 'artifacts/mapa-referencias-desktop.png'});
    await page.setViewportSize({width: 390, height: 844});
    await page.evaluate(() => { map.invalidateSize(); map.closePopup(); resetarMapa(); });
    await page.waitForFunction(() => !map._animatingZoom && !map._panAnim?._inProgress);
    await page.locator('#mapid').scrollIntoViewIfNeeded();
    await page.screenshot({path: 'artifacts/mapa-referencias-mobile.png'});
    await page.route('**/referencias-mapa*', async route => {
      await route.fulfill({status: 503, contentType: 'application/json', body: '{"erro":"offline"}'});
    }, {times: 1});
    await page.goto('http://127.0.0.1:5000/?lang=en', {waitUntil: 'domcontentloaded'});
    await page.waitForFunction(() => document.getElementById('referencias-status').textContent.includes('could not be loaded'));
    await page.locator('#mostrar-referencias').uncheck();
    await page.locator('#mostrar-referencias').check();
    await page.waitForFunction(() => referenciasCarregadas);
    assert.match(await page.locator('#referencias-status').innerText(), /424 plants/);
    assert.deepEqual(erros, []);
    const resultado = {ocorrencias: 260, registrosReferencia: 923, plantasReferencia: 424,
      raioIncertezaMetros: 3416, pesquisa: 'ok', filtro: 'ok', ficha: 'ok',
      ocultarMostrar: 'ok', recuperarFalha: 'ok', ingles: 'ok', errosJavascript: erros};
    fs.writeFileSync('artifacts/mapa-referencias-verificacao.json', JSON.stringify(resultado, null, 2));
    console.log(JSON.stringify(resultado));
  } finally {
    await browser.close();
  }
})().catch(e => {console.error(e); process.exit(1);});
