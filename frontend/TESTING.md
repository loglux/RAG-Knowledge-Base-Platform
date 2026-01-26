# UI Testing with Playwright

Автоматические UI тесты для проверки интерфейса Knowledge Base Platform.

## Быстрый старт

```bash
# Запустить все тесты
npm run test:ui

# С отчетом в терминале
npm run test:ui:line

# С HTML отчетом
npm run test:ui:html

# Только один тест
npm run test:ui tests/ui.spec.cjs:8
```

## Структура

```
frontend/
├── tests/
│   └── ui.spec.cjs           # UI тесты
├── playwright.config.cjs      # Конфигурация Playwright
└── TESTING.md                 # Эта документация
```

## Тесты

### 1. KB Cards with Embedding Badges
Проверяет отображение карточек KB с цветными badges моделей эмбеддингов.

### 2. Create KB Modal
Проверяет открытие модального окна и загрузку 11 моделей эмбеддингов.

### 3. Model Info Card
Проверяет отображение информации о выбранной модели (провайдер, размерность, стоимость).

### 4. Chat Navigation
Проверяет переход на страницу чата при клике на кнопку Chat.

### 5. Documents Navigation
Проверяет переход на страницу документов при клике на кнопку Documents.

### 6. API Embeddings Models
Проверяет API endpoint `/api/v1/embeddings/models` на корректность структуры данных.

## Технические детали

### Docker образ
Используется официальный образ Microsoft Playwright:
- **Образ:** `mcr.microsoft.com/playwright:v1.58.0-jammy`
- **Размер:** ~2.23 GB
- **Браузер:** Chromium headless

### Сетевая конфигурация
- **Network mode:** `--network host` (для доступа к localhost:5174 и localhost:8004)
- **Frontend URL:** http://localhost:5174
- **API URL:** http://localhost:5174/api/v1 (через Vite proxy)

### Требования
- Docker должен быть запущен
- Frontend должен работать на порту 5174
- Backend API должен работать на порту 8004

## Добавление новых тестов

Откройте `tests/ui.spec.cjs` и добавьте новый тест:

```javascript
test('название теста', async ({ page }) => {
  // Ваш код теста
  await page.click('button:has-text("Кнопка")');
  await expect(page.locator('.element')).toBeVisible();
});
```

## Устранение проблем

### Тесты не находят элементы
Проверьте, что frontend запущен:
```bash
curl http://localhost:5174/
```

### Docker образ отсутствует
Образ загрузится автоматически при первом запуске (требует ~10 минут).

### Timeout ошибки
Увеличьте timeout в `playwright.config.cjs`:
```javascript
timeout: 60000, // 60 секунд
```

### Network errors
Убедитесь, что используется `--network host` для доступа к localhost.

## CI/CD

Для GitHub Actions добавьте в `.github/workflows/test.yml`:

```yaml
- name: Run Playwright tests
  run: |
    cd frontend
    npm run test:ui
```

## Отчеты

HTML отчеты сохраняются в `playwright-report/`:
```bash
npm run test:ui:html
npx playwright show-report  # Открыть отчет
```

Screenshots при ошибках: `test-results/*/test-failed-*.png`

## Производительность

Средняя скорость выполнения:
- **5 тестов:** ~9 секунд
- **Параллельность:** 2 воркера
- **Браузер:** Chromium headless

## Полезные команды

```bash
# Запустить с видео
docker run --rm --network host -v $(pwd):/work -w /work \
  mcr.microsoft.com/playwright:v1.58.0-jammy \
  npx playwright test --reporter=html

# Запустить в debug режиме
docker run --rm --network host -v $(pwd):/work -w /work \
  -e PWDEBUG=1 \
  mcr.microsoft.com/playwright:v1.58.0-jammy \
  npx playwright test

# Очистить кеш
docker run --rm --network host -v $(pwd):/work -w /work \
  mcr.microsoft.com/playwright:v1.58.0-jammy \
  npx playwright clean

# Обновить образ
docker pull mcr.microsoft.com/playwright:v1.58.0-jammy
```
