import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  timeout: 120000,
  expect: { timeout: 15000 },
  use: {
    baseURL: process.env.WEB_URL || "http://127.0.0.1:3000",
    locale: "ru-RU",
    timezoneId: "Asia/Tashkent",
    launchOptions: {
      executablePath: process.env.CHROMIUM_PATH || "/usr/bin/chromium",
      args: ["--no-sandbox", "--disable-dev-shm-usage"],
    },
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  reporter: "list",
});
