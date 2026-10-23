from pathlib import Path
import json, tempfile, shutil
from playwright.sync_api import sync_playwright
R=Path.home()/'cern/notes/acts/notebook/2026-10-12_atlas-stepper-review'
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1080})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    standalone = Path(tempfile.mkdtemp(prefix='acts-atlas-standalone-')) / 'report.html'
    shutil.copyfile(R.parent / '2026-10-12_atlas-stepper-review.html', standalone)
    page.goto(standalone.as_uri());page.wait_for_selector('#results tr')
    assert page.locator('#results tr').count()==6
    checked=0
    for field in ['2','0']:
        page.select_option('#field',field)
        for cov in ['true','false']:
            page.select_option('#cov',cov)
            for basis in ['atlas','sympy']:
                page.select_option('#basis',basis)
                for modes in ['all','default']:
                    page.select_option('#modes',modes)
                    expected=(6 if cov=='true' else 4) if field=='2' else 3
                    if modes=='default':expected=3 if field=='2' else 2
                    assert page.locator('#results tr').count()==expected
                    content=page.locator('#results').inner_text()
                    assert not any(x in content for x in ['undefined','NaN','Infinity'])
                    assert page.locator('#trials > details').count()==expected
                    assert page.locator('#trials pre').count()==5*expected
                    checked+=1
    page.click('#reset');assert page.locator('#results tr').count()==6
    assert '7.375' in page.locator('#results').inner_text()
    assert page.locator('#basis').input_value()=='atlas'
    for link in page.locator('a').all():
        href=link.get_attribute('href')
        if href: assert href.startswith(('https:','#','data:')),href
    for filename in ['cpu-comparison.pdf','cpu-results.json','2026-10-12_atlas-stepper-review.md']:
        with page.expect_download() as download_info:
            page.locator(f'a[download="{filename}"]').first.click()
        downloaded=download_info.value
        assert downloaded.suggested_filename == filename
        assert Path(downloaded.path()).stat().st_size > 100
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Mobile overflow'
    assert not errors,errors
    browser.close()
    shutil.rmtree(standalone.parent)
    print(json.dumps({'selector_combinations_checked':checked,'reset':'passed','trial_output':'passed','standalone_attachments':'passed','mobile_overflow':'none','javascript_errors':errors},indent=2))
