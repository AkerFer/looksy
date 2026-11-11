"use client";
import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowUpRight,
  Sparkles,
  Shirt,
  Camera,
  Heart,
  Check,
  WandSparkles,
} from "lucide-react";
import {
  Brand,
  ThemeButton,
  Reveal,
  Notice,
  useSession,
  errorText,
} from "./core";
import { api } from "@/lib/api";
export function Landing() {
  return (
    <div className="landing">
      <header className="public-nav">
        <Brand />
        <nav>
          <a href="#how">Как это работает</a>
          <a href="#features">Возможности</a>
        </nav>
        <div className="row">
          <ThemeButton />
          <Link className="text-link" href="/login">
            Войти
          </Link>
          <Link className="button small" href="/register">
            Начать бесплатно <ArrowUpRight size={16} />
          </Link>
        </div>
      </header>
      <Reveal>
        <section className="hero">
          <div className="hero-copy">
            <span className="eyebrow">
              <Sparkles size={15} /> ВАШ ЛИЧНЫЙ ГАРДЕРОБ, ПЕРЕОСМЫСЛЕННЫЙ
            </span>
            <h1>
              Ваши вещи.
              <br />
              Новые <em>истории.</em>
            </h1>
            <p>
              Влюбитесь в свой гардероб заново. Сохраняйте любимые вещи,
              находите свежие сочетания и встречайте каждый день в своём стиле.
            </p>
            <Link href="/register" className="button large">
              Создать мой гардероб <ArrowUpRight size={19} />
            </Link>
            <div className="hero-foot">
              <Check size={16} /> Ваши фотографии приватны <span>·</span>{" "}
              Никаких обязательных платных AI
            </div>
          </div>
          <div
            className="hero-art"
            aria-label="Декоративная иллюстрация гардероба"
          >
            <span className="art-orbit" />
            <div className="art-title">
              THE EVERYDAY EDIT <Sparkles size={16} />
            </div>
            <div className="art-frame">
              <div className="css-shirt" />
              <div className="css-pants" />
              <div className="css-bag" />
              <span className="art-note">a little more you.</span>
            </div>
            <div className="float-tag">
              <Heart size={17} /> Стиль уже в вашем шкафу
            </div>
            <span className="art-star">✳</span>
          </div>
        </section>
      </Reveal>
      <section id="how" className="public-section">
        <div className="section-title">
          <span className="eyebrow">ПРОСТО КАК РАЗ, ДВА, ТРИ</span>
          <h2>Утро без лишних сомнений.</h2>
        </div>
        <div className="feature-grid">
          {[
            [
              Camera,
              "01",
              "Сфотографируйте вещь",
              "Загрузите реальные фотографии одежды — Looksy удалит фон и сохранит их только для вас.",
            ],
            [
              Shirt,
              "02",
              "Соберите свой гардероб",
              "Добавьте категории, цвета и предпочтения. Исправляйте характеристики в любой момент.",
            ],
            [
              WandSparkles,
              "03",
              "Найдите новый образ",
              "Выберите стиль, планы и нужные вещи. Получите варианты из того, что у вас уже есть.",
            ],
          ].map(([Icon, n, title, text]) => {
            const I = Icon as typeof Camera;
            return (
              <article key={String(n)} className="feature">
                <div className="row">
                  <I size={25} />
                  <span>{String(n)}</span>
                </div>
                <h3>{String(title)}</h3>
                <p>{String(text)}</p>
              </article>
            );
          })}
        </div>
      </section>
      <section id="features" className="landing-banner">
        <div>
          <span className="eyebrow">МЕНЬШЕ ПОКУПОК НАУГАД</span>
          <h2>
            Больше возможностей
            <br />в каждой любимой вещи.
          </h2>
          <p>
            История образов, избранное, календарь и рекомендации — в одном
            месте. При недоступности AI работает локальный алгоритм.
          </p>
        </div>
        <Link href="/register" className="button light">
          Попробовать Looksy <ArrowUpRight size={18} />
        </Link>
      </section>
      <footer className="public-footer">
        <Brand />
        <span>Ваш стиль. Ваш ритм. Ваш Looksy.</span>
        <Link href="/login">Войти в гардероб ↗</Link>
      </footer>
    </div>
  );
}
export function AuthPage({ register = false }: { register?: boolean }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const router = useRouter();
  const { refresh } = useSession();
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const form = new FormData(event.currentTarget);
    const username = String(form.get("username"));
    const password = String(form.get("password"));
    try {
      if (register)
        await api("/api/auth/register/", "POST", {
          username,
          password,
          email: form.get("email"),
          display_name: form.get("display_name"),
        });
      await api("/api/auth/session/", "POST", { username, password });
      await refresh();
      router.push("/dashboard");
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="auth-page">
      <header className="public-nav">
        <Brand />
        <ThemeButton />
      </header>
      <div className="auth-grid">
        <div className="auth-story">
          <span className="eyebrow">A WARDROBE THAT FEELS LIKE YOU</span>
          <h1>
            Стиль — это
            <br />
            быть <em>собой.</em>
          </h1>
          <div className="auth-art">
            <Shirt size={150} strokeWidth={0.7} />
            <Sparkles size={40} />
            <Heart size={34} />
          </div>
          <p>
            Ваш любимый свитер, идеальные джинсы и десятки сочетаний, которые
            ещё предстоит открыть.
          </p>
        </div>
        <section className="auth-form">
          <span className="eyebrow">ДОБРО ПОЖАЛОВАТЬ В LOOKSY</span>
          <h1>{register ? "Начнём вашу историю" : "Рады видеть вас снова"}</h1>
          <p>
            {register
              ? "Создайте аккаунт и соберите свой первый гардероб."
              : "Ваш гардероб и любимые образы уже ждут."}
          </p>
          <Notice>{error}</Notice>
          <form onSubmit={submit}>
            {register && (
              <label>
                Как вас зовут
                <input
                  name="display_name"
                  autoComplete="given-name"
                  maxLength={100}
                  placeholder="Ваше имя"
                />
              </label>
            )}
            <label>
              Имя пользователя
              <input
                name="username"
                required
                maxLength={150}
                autoComplete="username"
                placeholder="Например, anna"
              />
            </label>
            {register && (
              <label>
                Email
                <input
                  name="email"
                  type="email"
                  autoComplete="email"
                  placeholder="anna@example.com"
                />
              </label>
            )}
            <label>
              Пароль
              <input
                name="password"
                type="password"
                required
                autoComplete={register ? "new-password" : "current-password"}
                minLength={register ? 8 : 1}
                placeholder={register ? "Не менее 8 символов" : "Ваш пароль"}
              />
            </label>
            {register && (
              <p className="form-hint">
                Используйте сложный пароль, отличный от имени пользователя и
                распространённых слов.
              </p>
            )}
            <button className="button full" disabled={busy}>
              {busy ? "Подождите…" : register ? "Создать аккаунт" : "Войти"}{" "}
              <ArrowUpRight size={18} />
            </button>
          </form>
          <p className="auth-switch">
            {register ? "Уже есть аккаунт?" : "Ещё нет аккаунта?"}{" "}
            <Link href={register ? "/login" : "/register"}>
              {register ? "Войти" : "Зарегистрироваться"}
            </Link>
          </p>
        </section>
      </div>
    </div>
  );
}
