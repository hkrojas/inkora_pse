import { test as setup } from '@playwright/test';
import { loginTenantByUi, saveTenantStorageState } from './helpers/auth';

setup('login tenant por UI', async ({ page }) => {
  await loginTenantByUi(page);
  await saveTenantStorageState(page);
});
