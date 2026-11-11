"use client";
import { useState, type FormEvent } from "react";
import Link from "next/link";
import {
  Shirt,
  Heart,
  Sparkles,
  CloudSun,
  ArrowUpRight,
  Send,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Trash2,
  Camera,
} from "lucide-react";
import { api } from "@/lib/api";
import type {
  Outfit,
  Saved,
  Profile,
  Forecast,
  StylistReply,
  CalendarEntry,
} from "@/lib/types";
import {
  Heading,
  useData,
  useSession,
  Notice,
  Loading,
  Empty,
  AddLink,
  OutfitCard,
  OutfitPreview,
  PhotoImage,
  errorText,
} from "./core";
export function WeatherWidget() {
  const profile = useData<Profile>("/api/profile/");
  const [forecast, setForecast] = useState<Forecast>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return (
    <section className="weather-card">
      <div className="row between">
        <div className="weather-icon">
          <CloudSun size={27} />
        </div>
        <span className="eyebrow tiny">ПОГОДА ДЛЯ ВАШЕГО ОБРАЗА</span>
      </div>
      <h2>
        {forecast ? `${forecast.apparent_temperature_c}°` : "В вашем ритме"}
      </h2>
      <p>
        {forecast
          ? `Ощущаемая температура · ${profile.data?.city || "Выбранное место"}`
          : "Пусть образ подходит не только настроению, но и погоде."}
      </p>
      {forecast && (
        <p className="form-hint">
          Осадки {forecast.precipitation_probability}% · ветер{" "}
          {forecast.wind_speed_kmh} км/ч
          <br />
          Open-Meteo · {new Date(forecast.forecast_for).toLocaleString("ru-RU")}
        </p>
      )}
      <Notice>{error || profile.error}</Notice>
      {profile.data?.latitude && profile.data?.longitude ? (
        <button
          className="text-link"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            setError("");
            try {
              setForecast(
                await api<Forecast>("/api/weather/forecast/", "POST", {
                  latitude: profile.data?.latitude,
                  longitude: profile.data?.longitude,
                }),
              );
            } catch (err) {
              setError(errorText(err));
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy
            ? "Получаем прогноз…"
            : forecast
              ? "Обновить прогноз"
              : "Узнать погоду"}{" "}
          <ArrowUpRight size={15} />
        </button>
      ) : (
        <Link className="text-link" href="/settings">
          Выбрать город <ArrowUpRight size={15} />
        </Link>
      )}
    </section>
  );
}
export function Dashboard() {
  const { user } = useSession();
  const summary = useData<{
    total: number;
    available: number;
    unavailable: number;
  }>("/api/clothing/summary/");
  const outfits = useData<Outfit[]>("/api/outfits/", true);
  const saved = useData<Saved[]>("/api/saved-outfits/", true);
  const profile = useData<Profile>("/api/profile/");
  return (
    <>
      <Heading
        eyebrow="МАЛЕНЬКОЕ ВДОХНОВЕНИЕ ДЛЯ ВАШЕГО ДНЯ"
        title={`Привет, ${profile.data?.display_name || user?.username || "это вы"}!`}
        subtitle="Сегодня — хороший день для нового сочетания."
        action={<AddLink />}
      />
      <Notice>
        {summary.error || outfits.error || saved.error || profile.error}
      </Notice>
      <div className="dashboard-top">
        <section className="dashboard-hero">
          <div>
            <span className="eyebrow">ВАШ СТИЛЬ, НОВАЯ ГЛАВА</span>
            <h2>
              А что, если любимый
              <br />
              образ уже <em>у вас?</em>
            </h2>
            <p>
              Давайте найдём свежие сочетания в знакомых вещах. Без лишних
              покупок и долгих раздумий.
            </p>
            <Link className="button" href="/create">
              <Sparkles size={17} /> Создать мой образ
            </Link>
          </div>
          <div className="hero-motif">
            <Shirt size={104} strokeWidth={0.8} />
            <Sparkles size={31} />
            <span>made for you</span>
          </div>
        </section>
        <WeatherWidget />
      </div>
      <div className="stats-grid">
        {[
          [Shirt, "Вещей в гардеробе", summary.data?.total, "/wardrobe"],
          [Sparkles, "Созданных образов", outfits.data?.length, "/outfits"],
          [Heart, "Любимых сочетаний", saved.data?.length, "/saved"],
        ].map(([Icon, label, value, href]) => {
          const I = Icon as typeof Shirt;
          return (
            <Link className="stat-card" href={String(href)} key={String(label)}>
              <span className="stat-icon">
                <I size={23} />
              </span>
              <div>
                <strong>{value === undefined ? "—" : String(value)}</strong>
                <p>{String(label)}</p>
              </div>
              <ArrowUpRight size={18} />
            </Link>
          );
        })}
      </div>
      <div className="section-row">
        <div>
          <span className="eyebrow">СВОЁ, ЛЮБИМОЕ</span>
          <h2>Последние образы</h2>
        </div>
        <Link href="/outfits" className="text-link">
          Вся история <ArrowUpRight size={16} />
        </Link>
      </div>
      {outfits.loading ? (
        <Loading />
      ) : outfits.data?.length ? (
        <div className="outfit-grid">
          {outfits.data.slice(0, 3).map((o) => (
            <OutfitCard key={o.id} outfit={o} />
          ))}
        </div>
      ) : (
        <Empty
          title="Здесь начнётся ваша история"
          action={
            <Link className="button secondary" href="/create">
              Создать первый образ
            </Link>
          }
        >
          Добавьте вещи, которые любите, и попробуйте первое сочетание.
        </Empty>
      )}
      <div className="bottom-note">
        <Sparkles size={20} />
        <p>
          Необязательно иметь больше вещей, чтобы видеть больше возможностей.
        </p>
        <Link href="/wardrobe" className="text-link">
          В мой гардероб <ArrowUpRight size={16} />
        </Link>
      </div>
    </>
  );
}
export function Stylist() {
  const [messages, setMessages] = useState<
    { question: string; reply: StylistReply }[]
  >([]);
  const [text, setText] = useState("");
  const [useAI, setUseAI] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function send(e: FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    setError("");
    const question = text.trim();
    try {
      const reply = await api<StylistReply>("/api/stylist/", "POST", {
        message: question,
        use_ai: useAI,
      });
      setMessages((m) => [...m, { question, reply }]);
      setText("");
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }
  const missingLabels: Record<string, string> = {
    top: "Верх",
    bottom: "Брюки или юбка",
    dress: "Платье",
    shoes: "Обувь",
    outerwear: "Внешний слой",
    accessory: "Аксессуар",
    other: "Другие вещи",
  };
  return (
    <>
      <Heading
        eyebrow="ДАВАЙТЕ ПОГОВОРИМ О ВАШЕМ СТИЛЕ"
        title="Ваш Looksy-стилист"
        subtitle="Немного вдохновения, конкретные вещи и советы без лишних покупок."
      />
      <section className="chat-panel panel">
        {!messages.length && (
          <div className="chat-welcome">
            <span className="empty-icon">
              <Sparkles size={30} />
            </span>
            <h2>На что настроимся сегодня?</h2>
            <p>
              Спросите про свои вещи или недостающие категории. Если AI
              недоступен, предложим базовый комплект по правилам.
            </p>
            <div className="prompt-chips">
              {[
                "Что надеть сегодня?",
                "Чего не хватает в моём гардеробе?",
                "Хочу минималистичный образ",
              ].map((t) => (
                <button
                  className="button secondary small"
                  key={t}
                  onClick={() => setText(t)}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
        )}
        <div className="messages" aria-live="polite">
          {messages.map((m, i) => (
            <div key={i}>
              <div className="user-message">{m.question}</div>
              <div className="assistant-message">
                <span className="eyebrow">
                  <Sparkles size={14} />{" "}
                  {m.reply.source === "ollama"
                    ? "LOOKSY AI"
                    : "LOOKSY · АЛГОРИТМ ПРАВИЛ"}
                </span>
                <p>{m.reply.message}</p>
                {m.reply.items.length > 0 && (
                  <div className="chat-items">
                    {m.reply.items.map((item) => (
                      <div key={item.id}>
                        <PhotoImage url={item.photo?.url} alt={item.name} />
                        <span>{item.name}</span>
                      </div>
                    ))}
                  </div>
                )}
                {m.reply.missing_slots.length > 0 && (
                  <p>
                    <strong>Можно дополнить гардероб: </strong>
                    {m.reply.missing_slots
                      .map((s) => missingLabels[s] || s)
                      .join(", ")}
                    . Ничего не добавлено автоматически.
                  </p>
                )}
                {m.reply.warnings.map((w) => (
                  <Notice key={w} kind="info">
                    {w}
                  </Notice>
                ))}
                <Link href="/create" className="text-link">
                  Настроить и сохранить образ <ArrowUpRight size={15} />
                </Link>
              </div>
            </div>
          ))}
        </div>
        <Notice>{error}</Notice>
        <form className="chat-form" onSubmit={send}>
          <label className="check-row">
            <input
              type="checkbox"
              checked={useAI}
              onChange={(e) => setUseAI(e.target.checked)}
            />{" "}
            Использовать локальную AI-модель, если доступна
          </label>
          <div className="chat-input">
            <label className="sr-only" htmlFor="chat-message">
              Сообщение стилисту
            </label>
            <textarea
              id="chat-message"
              maxLength={1000}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Расскажите, что хочется надеть…"
              rows={2}
              required
            />
            <button
              className="button"
              disabled={busy || !text.trim()}
              aria-label="Отправить сообщение"
            >
              <Send size={19} />
              {busy ? "Думаем…" : "Отправить"}
            </button>
          </div>
          <p className="form-hint">
            Переписка хранится только до перезагрузки страницы. Новый запрос не
            учитывает прошлые сообщения.
          </p>
        </form>
      </section>
    </>
  );
}
function dayString() {
  return new Intl.DateTimeFormat("en-CA").format(new Date());
}
export function Calendar() {
  const entries = useData<CalendarEntry[]>("/api/calendar/", true);
  const outfits = useData<Outfit[]>("/api/outfits/", true);
  const [date, setDate] = useState(dayString());
  const [month, setMonth] = useState(() => dayString().slice(0, 7));
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [success, setSuccess] = useState("");
  const entry = entries.data?.find((e) => e.date === date);
  const [year, m] = month.split("-").map(Number);
  const count = new Date(year, m, 0).getDate();
  const offset = (new Date(year, m - 1, 1).getDay() + 6) % 7;
  function changeMonth(delta: number) {
    const d = new Date(year, m - 1 + delta, 1);
    setMonth(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`);
  }
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const f = new FormData(e.currentTarget);
    try {
      await api(
        entry ? `/api/calendar/${entry.id}/` : "/api/calendar/",
        entry ? "PATCH" : "POST",
        { date, outfit: Number(f.get("outfit")), note: f.get("note") },
      );
      entries.reload();
      setSuccess("Образ запланирован.");
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Heading
        eyebrow="НЕМНОГО ПЛАНОВ, МНОГО ВДОХНОВЕНИЯ"
        title="Календарь образов"
        subtitle="Спланируйте любимое сочетание — и освободите утро для себя."
      />
      <Notice>{error || entries.error || outfits.error}</Notice>
      <Notice kind="success">{success}</Notice>
      <div className="calendar-layout">
        <section className="panel calendar-panel">
          <div className="section-row">
            <h2>
              {new Date(year, m - 1, 1).toLocaleDateString("ru-RU", {
                month: "long",
                year: "numeric",
              })}
            </h2>
            <div className="row">
              <button
                aria-label="Предыдущий месяц"
                className="icon-button"
                onClick={() => changeMonth(-1)}
              >
                <ChevronLeft />
              </button>
              <button
                aria-label="Следующий месяц"
                className="icon-button"
                onClick={() => changeMonth(1)}
              >
                <ChevronRight />
              </button>
            </div>
          </div>
          <div className="calendar-grid">
            {["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"].map((d) => (
              <div key={d} className="weekday">
                {d}
              </div>
            ))}
            {Array.from({ length: offset }, (_, i) => (
              <div key={"blank" + i} />
            ))}
            {Array.from({ length: count }, (_, i) => {
              const stamp = `${month}-${String(i + 1).padStart(2, "0")}`;
              const record = entries.data?.find((e) => e.date === stamp);
              return (
                <button
                  className={`calendar-day ${date === stamp ? "selected" : ""} ${record ? "planned" : ""}`}
                  key={stamp}
                  onClick={() => {
                    setDate(stamp);
                    setSuccess("");
                  }}
                  aria-label={`Выбрать ${stamp}`}
                >
                  <span>{i + 1}</span>
                  {record && (
                    <>
                      <span className="calendar-dot" />
                      <small>{record.outfit_details.name}</small>
                    </>
                  )}
                </button>
              );
            })}
          </div>
        </section>
        <section className="panel form-panel">
          <span className="eyebrow">
            <CalendarDays size={16} /> ПЛАН НА ДЕНЬ
          </span>
          <h2>
            {new Date(date + "T12:00:00").toLocaleDateString("ru-RU", {
              day: "numeric",
              month: "long",
            })}
          </h2>
          {entries.loading || outfits.loading ? (
            <Loading />
          ) : !outfits.data?.length ? (
            <p>
              Сначала <Link href="/create">создайте образ</Link>, чтобы добавить
              его в календарь.
            </p>
          ) : (
            <form onSubmit={submit} key={date + ":" + (entry?.id || 0)}>
              <label>
                Дата
                <input
                  type="date"
                  required
                  value={date}
                  onChange={(e) => {
                    if (e.target.value) {
                      setDate(e.target.value);
                      setMonth(e.target.value.slice(0, 7));
                    }
                  }}
                />
              </label>
              <label>
                Выберите образ
                <select
                  name="outfit"
                  required
                  defaultValue={entry?.outfit || ""}
                >
                  <option value="" disabled>
                    Образ из истории
                  </option>
                  {outfits.data.map((o) => (
                    <option value={o.id} key={o.id}>
                      {o.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Заметка
                <textarea
                  name="note"
                  maxLength={300}
                  defaultValue={entry?.note}
                  rows={3}
                  placeholder="Например, встреча с друзьями"
                />
              </label>
              <button className="button full" disabled={busy}>
                {busy
                  ? "Сохраняем…"
                  : entry
                    ? "Обновить план"
                    : "Запланировать"}
              </button>
              {entry && (
                <>
                  <div className="calendar-preview">
                    <OutfitPreview outfit={entry.outfit_details} />
                  </div>
                  <Link className="text-link" href={`/outfits/${entry.outfit}`}>
                    Посмотреть образ ↗
                  </Link>
                  <button
                    type="button"
                    className="text-link danger"
                    onClick={async () => {
                      try {
                        await api(`/api/calendar/${entry.id}/`, "DELETE");
                        entries.reload();
                        setSuccess("План удалён.");
                      } catch (err) {
                        setError(errorText(err));
                      }
                    }}
                  >
                    <Trash2 size={15} /> Удалить из календаря
                  </button>
                </>
              )}
            </form>
          )}
        </section>
      </div>
    </>
  );
}
