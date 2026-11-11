import { test, expect, type Page } from "@playwright/test";
import path from "node:path";
const baseURL = process.env.WEB_URL || "http://127.0.0.1:3000";
const password = "Looksy-Browser!72816";
async function createClothing(
  page: Page,
  name: string,
  category: string,
  photo = false,
) {
  await page.goto("/add");
  await page.locator('[name="name"]').fill(name);
  await page.locator('[name="category"]').selectOption({ label: category });
  await page.locator('[name="comfort"]').selectOption("4");
  await page.locator('[name="warmth"]').selectOption("3");
  await page.locator('[name="styles"]').fill("casual");
  if (photo)
    await page
      .locator('input[type="file"]')
      .first()
      .setInputFiles(path.join(__dirname, "fixtures/shirt.png"));
  await page
    .getByRole("button", { name: "Сохранить вещь", exact: true })
    .click();
  await expect(page).toHaveURL(/\/wardrobe$/, { timeout: 60000 });
  await expect(page.getByRole("heading", { name })).toBeVisible();
}
test("реальный гардероб: регистрация, фото, подбор, избранное, календарь, стилист, настройки и удаление", async ({
  page,
  browser,
}) => {
  const username = "web_" + Date.now();
  let registered = false;
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  try {
    await page.goto("/register");
    await page.locator('[name="display_name"]').fill("Анна");
    await page.locator('[name="username"]').fill(username);
    await page.locator('[name="email"]').fill("test@example.com");
    await page.locator('[name="password"]').fill(password);
    await page
      .getByRole("button", { name: "Создать аккаунт", exact: true })
      .click();
    await expect(page).toHaveURL(/\/dashboard$/);
    registered = true;
    await expect(
      page.getByRole("heading", { name: "Привет, Анна!" }),
    ).toBeVisible();
    expect(
      (await page.context().cookies()).find((c) => c.name === "sessionid")
        ?.httpOnly,
    ).toBeTruthy();
    await page.goto("/wardrobe");
    await expect(page.getByText("Здесь будет ваш гардероб")).toBeVisible();
    await createClothing(page, "Тестовая футболка", "Футболки", true);
    let items = (await (await page.request.get("/api/clothing/")).json())
      .results;
    const photo = await page.request.get(items[0].photo.url);
    expect(photo.status()).toBe(200);
    expect(photo.headers()["cache-control"]).toContain("no-store");
    const stranger = await browser.newContext();
    expect(
      (
        await stranger.request.get(new URL(items[0].photo.url, baseURL).href)
      ).status(),
    ).toBe(403);
    await stranger.close();
    await createClothing(page, "Тестовые брюки", "Брюки");
    await createClothing(page, "Тестовая обувь", "Обувь");
    await page
      .getByRole("button", { name: "Редактировать Тестовая футболка" })
      .click();
    const modal = page.getByRole("dialog");
    await modal.locator('[name="name"]').fill("Любимая футболка");
    await modal
      .getByRole("button", { name: "Сохранить вещь", exact: true })
      .click();
    await expect(modal).not.toBeVisible();
    await page.getByRole("textbox", { name: "Поиск вещей" }).fill("Любимая");
    await expect(
      page.getByRole("heading", { name: "Любимая футболка" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Тестовые брюки" }),
    ).not.toBeVisible();
    await page.goto("/create");
    await page.locator('[name="style"]').fill("casual");
    await page
      .getByRole("button", { name: "Создать мой образ", exact: true })
      .click();
    await expect(page).toHaveURL(/\/results\//);
    await page.getByRole("link", { name: "Рассмотреть образ" }).first().click();
    await expect(
      page.getByRole("heading", { name: "Почему этот образ?" }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Сохранить в избранное", exact: true })
      .click();
    await expect(
      page.getByRole("button", { name: "Убрать из избранного", exact: true }),
    ).toBeVisible();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: "test-results/outfit-desktop.png",
      fullPage: true,
    });
    await page
      .getByRole("button", { name: "Оценить на 5", exact: true })
      .click();
    await expect(page.getByText("Спасибо! Оценка сохранена.")).toBeVisible();
    await page.goto("/saved");
    await expect(
      page.getByRole("link", { name: "Рассмотреть образ" }),
    ).toHaveCount(1);
    await page.goto("/calendar");
    await page.locator('[name="outfit"]').selectOption({ index: 1 });
    await page.locator('[name="note"]').fill("Встреча");
    await page
      .getByRole("button", { name: "Запланировать", exact: true })
      .click();
    await expect(page.getByText("Образ запланирован.")).toBeVisible();
    await page.reload();
    await expect(
      page.getByRole("button", { name: "Обновить план", exact: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Выйти", exact: true }).click();
    await expect(page).toHaveURL(/\/$/);
    await page.goto("/login");
    await page.locator('[name="username"]').fill(username);
    await page.locator('[name="password"]').fill(password);
    await page.getByRole("button", { name: "Войти", exact: true }).click();
    await expect(page).toHaveURL(/\/dashboard$/);
    await page.goto("/stylist");
    await page.getByLabel("Использовать локальную AI-модель").uncheck();
    await page
      .getByRole("textbox", { name: "Сообщение стилисту" })
      .fill("Что надеть?");
    await page.getByRole("button", { name: "Отправить сообщение" }).click();
    await expect(page.getByText("LOOKSY · АЛГОРИТМ ПРАВИЛ")).toBeVisible();
    await page.goto("/settings");
    await page
      .getByRole("textbox", { name: "Ваше имя", exact: true })
      .fill("Анна Looksy");
    await page
      .getByRole("button", { name: "Сохранить профиль", exact: true })
      .click();
    await expect(page.getByText("Профиль сохранён.")).toBeVisible();
    await page.locator('input[name="styles"]').fill("casual, minimalism");
    await page
      .getByRole("group", { name: "Любимые цвета", exact: true })
      .getByLabel("Чёрный", { exact: true })
      .check();
    await page
      .getByRole("button", { name: "Сохранить предпочтения", exact: true })
      .click();
    await expect(
      page.getByText(
        "Предпочтения сохранены. Они будут учтены в новых образах.",
      ),
    ).toBeVisible();
    const avatarInput = page.locator('input[type="file"]');
    await avatarInput.setInputFiles(path.join(__dirname, "fixtures/shirt.png"));
    const avatar = page.locator('img[alt="Ваш аватар"]');
    await expect(avatar).toHaveAttribute("src", /\?v=\d+/);
    const oldAvatar = await avatar.getAttribute("src");
    await expect(page.getByText("Аватар обновлён.")).toBeVisible();
    await avatarInput.setInputFiles(path.join(__dirname, "fixtures/shirt.png"));
    await expect(avatar).not.toHaveAttribute("src", oldAvatar!);
    await page.getByRole("button", { name: "Тёмная тема" }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await page.setViewportSize({ width: 390, height: 844 });
    await expect(
      page.getByRole("heading", { name: "Профиль и предпочтения" }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
    await page
      .getByRole("button", { name: "Открыть меню", exact: true })
      .click();
    await expect(
      page.getByRole("button", { name: "Закрыть меню", exact: true }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Закрыть меню", exact: true })
      .click();
    await expect(page.locator("aside.sidebar")).not.toBeInViewport();
    await page.screenshot({
      path: "test-results/settings-mobile-dark.png",
      fullPage: true,
    });
    await page.getByLabel("Текущий пароль", { exact: true }).fill(password);
    page.once("dialog", (d) => d.accept());
    await page
      .getByRole("button", { name: "Удалить аккаунт и данные", exact: true })
      .click();
    await expect(page).toHaveURL(/\/$/);
    registered = false;
    expect((await page.request.get("/api/account/")).status()).toBe(403);
    expect(errors).toEqual([]);
  } finally {
    if (registered) {
      const origin = new URL(baseURL).origin;
      let session = await (await page.request.get("/api/auth/session/")).json();
      await page.request.post("/api/auth/session/", {
        data: { username, password },
        headers: { "X-CSRFToken": session.csrfToken, Origin: origin },
      });
      session = await (await page.request.get("/api/auth/session/")).json();
      const account = await page.request.get("/api/account/");
      if (account.ok() && (await account.json()).username === username) {
        await page.request.delete("/api/account/", {
          data: { password },
          headers: { "X-CSRFToken": session.csrfToken, Origin: origin },
        });
      }
    }
  }
});
test("публичная страница адаптивна, защищённая страница требует входа", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Ваши вещи/ })).toBeVisible();
  await page.screenshot({
    path: "test-results/landing-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "test-results/landing-mobile.png",
    fullPage: true,
  });
  await page.goto("/wardrobe");
  await expect(page).toHaveURL(/\/login$/);
});

test("формы входа не отправляют пароль в URL до загрузки JavaScript", async ({
  browser,
}) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  try {
    const page = await context.newPage();
    for (const route of ["/register", "/login"]) {
      await page.goto(new URL(route, baseURL).href);
      await page.locator('[name="username"]').fill("nojs-test");
      await page.locator('[name="password"]').fill("Synthetic-NoJS!882");
      await expect(page.locator("form")).toHaveAttribute("method", "post");
      await expect(
        page.getByRole("button", {
          name: route === "/register" ? "Создать аккаунт" : "Войти",
          exact: true,
        }),
      ).toBeDisabled();
      await page.locator('[name="password"]').press("Enter");
      expect(new URL(page.url()).search).toBe("");
    }
  } finally {
    await context.close();
  }
});
