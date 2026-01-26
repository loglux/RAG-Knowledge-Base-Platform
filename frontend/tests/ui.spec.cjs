const { test, expect } = require('@playwright/test');

test.describe('Knowledge Base Platform UI', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:5174/');
  });

  test('should display KB cards with embedding model badges', async ({ page }) => {
    // Wait for KB cards to load
    await page.waitForSelector('.card', { timeout: 5000 });

    const kbCards = await page.locator('.card').count();
    console.log(`Found ${kbCards} KB cards`);
    expect(kbCards).toBeGreaterThan(0);

    // Check if embedding model badge is visible
    const badge = page.locator('.card').first().locator('text=/OPENAI|VOYAGE|OLLAMA/');
    await expect(badge).toBeVisible();
    console.log('✓ Embedding model badge visible');
  });

  test('should show embedding model selector in Create KB modal', async ({ page }) => {
    // Click Create KB button
    await page.click('button:has-text("New KB"), button:has-text("Create Knowledge Base")');

    // Wait for modal to appear
    await page.waitForSelector('#embedding-model', { timeout: 3000 });
    console.log('✓ Create KB modal opened');

    // Check dropdown has models
    const options = await page.locator('#embedding-model option').count();
    console.log(`Found ${options} embedding models in dropdown`);
    expect(options).toBeGreaterThan(0);

    // Get model names
    const optionTexts = await page.locator('#embedding-model option').allTextContents();
    console.log('Available models:', optionTexts.slice(0, 3));

    // Check model info card is visible
    const modelInfo = page.locator('.bg-gray-800').filter({ hasText: '/M tokens' }).first();
    await expect(modelInfo).toBeVisible();
    console.log('✓ Model information card visible');
  });

  test('should navigate to chat page when clicking Chat button', async ({ page }) => {
    // Wait for KB cards
    await page.waitForSelector('.card', { timeout: 5000 });

    // Click Chat button on first KB card
    const chatButton = page.locator('.card').first().locator('button:has-text("Chat")');
    await chatButton.click();

    // Check URL changed
    await page.waitForURL(/\/kb\/.*\/chat/, { timeout: 3000 });
    console.log('✓ Navigated to chat page');
    expect(page.url()).toContain('/kb/');
    expect(page.url()).toContain('/chat');
  });

  test('should navigate to documents page when clicking Documents button', async ({ page }) => {
    // Wait for KB cards
    await page.waitForSelector('.card', { timeout: 5000 });

    // Click Documents button on first KB card
    const docsButton = page.locator('.card').first().locator('button:has-text("Documents")');
    await docsButton.click();

    // Check URL changed
    await page.waitForURL(/\/kb\/[^/]+$/, { timeout: 3000 });
    console.log('✓ Navigated to documents page');
    expect(page.url()).toContain('/kb/');
    expect(page.url()).not.toContain('/chat');
  });

  test('should load 11 embedding models from API', async ({ page }) => {
    const response = await page.request.get('http://localhost:5174/api/v1/embeddings/models');
    expect(response.ok()).toBeTruthy();

    const models = await response.json();
    console.log(`API returned ${models.length} models`);
    expect(models.length).toBe(11);

    // Check model structure
    expect(models[0]).toHaveProperty('model');
    expect(models[0]).toHaveProperty('provider');
    expect(models[0]).toHaveProperty('dimension');
    expect(models[0]).toHaveProperty('cost_per_million_tokens');
    console.log('✓ Model structure correct');
  });
});
