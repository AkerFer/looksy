import Link from "next/link";
export default function NotFound() {
  return (
    <main className="main-content">
      <h1>Эта страница не найдена</h1>
      <p>Вернёмся к вашим вещам?</p>
      <Link className="button" href="/dashboard">
        В мой Looksy
      </Link>
    </main>
  );
}
