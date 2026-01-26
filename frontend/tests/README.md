# UI Tests

Автоматические UI тесты на Playwright для проверки интерфейса.

## Быстрый старт

```bash
npm run test:ui
```

## Файлы

- **ui.spec.cjs** - Основные UI тесты (5 тестов)
  - KB cards с embedding badges
  - Create KB modal с выбором модели
  - Навигация Chat/Documents
  - API endpoints

## Документация

Полная документация: [TESTING.md](../TESTING.md)

## Запуск

```bash
# Все тесты
npm run test:ui

# С подробным выводом
npm run test:ui:line

# HTML отчет
npm run test:ui:html
```

## Добавление тестов

Откройте `ui.spec.cjs` и добавьте новый `test()` блок в `test.describe()`.

Пример:
```javascript
test('название теста', async ({ page }) => {
  await page.click('button');
  await expect(page.locator('.element')).toBeVisible();
});
```
