from pathlib import Path
import json
from playwright.sync_api import sync_playwright
R=Path.home()/'cern/notes/acts/notebook/2026-10-10_gx2f-energy-loss-validation'
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1440,'height':1080},device_scale_factor=1)
 errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
 page.goto((R/'index.html').as_uri());page.wait_for_selector('#results tr')
 assert page.locator('#results tr').count()==4
 assert page.locator('#verdict > p').count()==1
 assert page.locator('main > section').count()==5
 page.screenshot(path=str(R/'report-top.png'))
 assert page.locator('#results').inner_text().find('11.213')>=0
 checked=0
 for truth in ['vacuum','bethe_deterministic','mean_gaussian','mean_gaussian_scattering']:
  page.select_option('#truth',truth)
  for thickness in ([0] if truth=='vacuum' else [5,50]):
   if thickness:page.select_option('#thickness',str(thickness))
   for momentum in [1,2,5,10]:
    page.select_option('#momentum',str(momentum))
    for charge in [0,-1,1]:
     page.select_option('#charge',str(charge))
     result=page.evaluate('''() => ({rows:window.reportState.rows.length,failures:window.reportState.rows.map(r=>r.failures),state:window.reportState,invalid: /NaN|undefined|Infinity/.test(document.querySelector('#results').textContent+document.querySelector('#biaschart').innerHTML+document.querySelector('#pullchart').innerHTML)})''')
     assert result['rows']==4 and not result['invalid'],result
     assert result['state']['p']==momentum and result['state']['charge']==charge
     checked+=1
 page.select_option('#truth','mean_gaussian_scattering');page.select_option('#thickness','50');page.select_option('#momentum','1');page.select_option('#charge','0')
 page.uncheck('#showoff');assert page.locator('#biaschart circle').count()==12
 page.check('#showoff');assert page.locator('#biaschart circle').count()==16
 with page.expect_download() as event:page.click('#download')
 download=event.value;download.save_as(R/'browser-selected-results.csv')
 assert len((R/'browser-selected-results.csv').read_text().splitlines())==5
 page.screenshot(path=str(R/'report-desktop.png'),full_page=True)
 page.click('#theme');assert page.locator('html').get_attribute('data-theme')=='dark'
 page.screenshot(path=str(R/'report-dark.png'),full_page=True)
 page.click('#theme');page.set_viewport_size({'width':390,'height':844})
 assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Mobile horizontal overflow'
 page.screenshot(path=str(R/'report-mobile.png'),full_page=True)
 assert not errors,errors
 browser.close()
 print(json.dumps({'selector_combinations_checked':checked,'rows_per_selection':4,'csv_export':'passed','baseline_toggle':'passed','theme_toggle':'passed','mobile_overflow':'none','javascript_errors':errors},indent=2))
