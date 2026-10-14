// Run with playwright-cli run-code --filename frontend/scripts/browser-smoke.js.
// Controlled HTTP fixtures make this repeatable without books, secrets or AI calls.
async (page) => {
  const base = 'http://127.0.0.1:5173';
  const failures = [];
  page.on('pageerror', error => failures.push(error.message));
  page.on('console', message => {
    if (message.type() === 'error' && /Content Security Policy|Monaco initialization/.test(message.text())) {
      failures.push(message.text());
    }
  });
  let libraryFail = true;
  let askCalls = 0;
  await page.route('http://127.0.0.1:8000/**', async route => {
    const path = new URL(route.request().url()).pathname;
    let data;
    let status = 200;
    if (path === '/textbooks') {
      status = libraryFail ? 503 : 200;
      data = libraryFail ? { detail: 'Library unavailable' } : [{
        id: 999, filename: 'Smoke test textbook.pdf', page_count: 10,
      }];
    } else if (path === '/study-dashboard') {
      data = { resume: null, books: [], missed: [], quiz_score: 0, quiz_total: 0, attempts: 0 };
    } else if (path.endsWith('/cover')) {
      status = 404; data = {};
    } else if (path === '/textbooks/999/chats') {
      data = [{ id: 999, textbook_id: 999, title: 'Saved study' }];
    } else if (path === '/chats/999/messages') {
      data = [];
    } else if (path === '/chats/999/ask') {
      askCalls++;
      status = 429; data = { detail: 'Check your API quota and try later.' };
      await new Promise(resolve => setTimeout(resolve, 100));
    } else if (path === '/run-code') {
      data = { status: 'success', output: 'Hello from Java!\n' };
    } else {
      throw new Error(`Unexpected backend request: ${path}`);
    }
    await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(data) });
  });
  await page.goto(base);
  await page.getByRole('button', { name: 'Retry Library' }).waitFor();
  libraryFail = false;
  await page.getByRole('button', { name: 'Retry Library' }).click();
  await page.getByRole('button', { name: 'Continue Studying' }).click();
  await page.getByRole('button', { name: '</> Code Playground' }).click();
  await page.locator('.monaco-editor .view-lines').waitFor({ state: 'visible' });
  await page.waitForFunction(() => /public\s+class\s+Main/.test(document.querySelector('.monaco-editor')?.textContent || ''));
  await page.screenshot({ path: 'output/playwright/code-editor.png', fullPage: true });
  await page.getByRole('button', { name: '▶ Run' }).click();
  await page.getByText('Hello from Java!', { exact: true }).waitFor();
  const question = page.getByRole('textbox', { name: 'Textbook question', exact: true });
  await question.fill('Explain constructors');
  await question.press('Enter');
  await page.getByRole('alert').filter({ hasText: 'Check your API quota' }).waitFor();
  if (await question.inputValue() !== 'Explain constructors') throw new Error('Failed question was lost');
  if (askCalls !== 1) throw new Error('One send issued multiple tutor requests');
  await page.getByRole('button', { name: '← Library' }).click();
  if (await page.getByText('Constructors Review', { exact: true }).count()) throw new Error('Demo chat is still visible');
  await page.setViewportSize({ width: 390, height: 844 });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  if (overflow) throw new Error('Library overflows the mobile viewport');
  await page.screenshot({ path: 'output/playwright/mobile-library.png', fullPage: true });
  await page.setViewportSize({ width: 1360, height: 900 });
  await page.screenshot({ path: 'output/playwright/library.png', fullPage: true });
  await page.unrouteAll();
  if (failures.length) throw new Error(failures.join('\n'));
  console.log('PASS: library retry, local Monaco, run button, visible tutor error, draft preservation, single send, mobile layout. No OpenAI calls.');
}
