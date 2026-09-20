import { test as setup } from '@playwright/test';
import { loginTenantByUi, saveTenantStorageState } from './helpers/auth';

// A clean npm install can make Vite pre-optimize the router on the first page.
// Keep the product assertions strict while allowing that one-time local startup.
setup.setTimeout(60_000);

setup('login tenant por UI', async ({ page }) => {
  await loginTenantByUi(page);
  await saveTenantStorageState(page);
});
