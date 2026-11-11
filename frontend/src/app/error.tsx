"use client";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <main className="main-content">
      <h1>Не удалось открыть страницу</h1>
      <p>Попробуйте ещё раз. Сохранённые вещи остаются в вашем гардеробе.</p>
      <button className="button" onClick={reset}>
        Повторить
      </button>
    </main>
  );
}
