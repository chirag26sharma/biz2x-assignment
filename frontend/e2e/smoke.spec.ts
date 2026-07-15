import { expect, test } from "@playwright/test";

async function waitForLoginPage(page: import("@playwright/test").Page) {
  await page.goto("/");
  await expect(page.getByText("Select a demo role")).toBeVisible();
  await expect(page.getByTestId("login-A001")).toBeVisible({ timeout: 30_000 });
}

test.describe("Biz2X Early Warning smoke tests", () => {
  test("analyst can login and see alerts dashboard", async ({ page }) => {
    await waitForLoginPage(page);
    await page.getByTestId("login-A001").click();
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.getByText("Borrowers by risk severity")).toBeVisible();
    await expect(page.getByTestId("alerts-table")).toBeVisible();
  });

  test("analyst can open assigned borrower detail", async ({ page }) => {
    await waitForLoginPage(page);
    await page.getByTestId("login-A001").click();
    await expect(page).toHaveURL(/\/dashboard/);
    await page.getByText("Vikram Patel").first().click();
    await expect(page).toHaveURL(/\/borrowers\/B101/);
    await expect(page.getByTestId("borrower-assessment")).toBeVisible();
    await expect(page.getByTestId("payment-history-table")).toBeVisible();
  });

  test("borrower lands on self-service view", async ({ page }) => {
    await waitForLoginPage(page);
    await page.getByTestId("login-U_B101").click();
    await expect(page).toHaveURL(/\/borrower/);
    await expect(page.getByTestId("borrower-self-view")).toBeVisible();
  });

  test("critical borrower shows DPD trend chart for analyst", async ({ page }) => {
    await waitForLoginPage(page);
    await page.getByTestId("login-A002").click();
    await expect(page).toHaveURL(/\/dashboard/);
    await page.goto("/borrowers/B110");
    await expect(page).toHaveURL(/\/borrowers\/B110/);
    await expect(page.getByTestId("borrower-assessment")).toBeVisible();
    await expect(page.getByTestId("dpd-trend-chart")).toBeVisible();
  });
});
