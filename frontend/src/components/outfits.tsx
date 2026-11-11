"use client";
import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Sparkles,
  Heart,
  ArrowLeft,
  RefreshCw,
  Trash2,
  CalendarPlus,
  Star,
} from "lucide-react";
import { api } from "@/lib/api";
import type { Clothing, Color, Outfit, Saved, Category } from "@/lib/types";
import {
  useData,
  Heading,
  Loading,
  Notice,
  Empty,
  OutfitCard,
  OutfitPreview,
  errorText,
} from "./core";
import { ColorChoices, seasons } from "./wardrobe";
const criteria: Record<string, string> = {
  comfort: "Комфорт",
  weather: "Погода",
  style: "Стиль",
  colors: "Цвета",
  preferences: "Предпочтения",
};
export function CreateLook() {
  const wardrobe = useData<Clothing[]>("/api/clothing/", true);
  const colors = useData<Color[]>("/api/colors/", true);
  const [required, setRequired] = useState<number[]>([]);
  const [excluded, setExcluded] = useState<number[]>([]);
  const [preferred, setPreferred] = useState<number[]>([]);
  const [overrideColors, setOverrideColors] = useState(false);
  const [weather, setWeather] = useState(false);
  const [priority, setPriority] = useState(50);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [messages, setMessages] = useState<string[]>([]);
  const router = useRouter();
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setMessages([]);
    const f = new FormData(e.currentTarget);
    const body: Record<string, unknown> = {
      count: Number(f.get("count")),
      occasion: f.get("occasion"),
      style: f.get("style"),
      season: f.get("season"),
      comfort_priority: priority,
      required_items: required,
      excluded_items: excluded,
      notes: f.get("notes"),
      use_weather: weather,
      weather_failure: f.get("weather_failure") || "continue",
    };
    if (overrideColors) body.preferred_colors = preferred;
    if (weather && f.get("forecast_at"))
      body.forecast_at = new Date(String(f.get("forecast_at"))).toISOString();
    if (!weather && f.get("temperature_c"))
      body.temperature_c = Number(f.get("temperature_c"));
    try {
      const result = await api<{ results: Outfit[]; messages: string[] }>(
        "/api/outfits/generate/",
        "POST",
        body,
      );
      setMessages(result.messages);
      if (result.results.length)
        router.push("/results/" + result.results.map((r) => r.id).join(","));
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Heading
        eyebrow="ВАШ НОВЫЙ ЛЮБИМЫЙ ОБРАЗ"
        title="Что наденем сегодня?"
        subtitle="Несколько пожеланий — и новые сочетания из ваших настоящих вещей."
      />
      <div className="create-layout">
        <form className="panel form-panel" onSubmit={submit}>
          <Notice>{error || wardrobe.error || colors.error}</Notice>
          {messages.map((m) => (
            <Notice key={m} kind="info">
              {m}
            </Notice>
          ))}
          <div className="step-heading">
            <span>01</span>
            <h2>Планы и настроение</h2>
          </div>
          <div className="form-grid">
            <label>
              Куда собираетесь?
              <select name="occasion">
                <option value="everyday">На каждый день</option>
                <option value="university">В университет</option>
                <option value="work">На работу</option>
                <option value="sport">На тренировку</option>
                <option value="party">На вечеринку</option>
                <option value="formal">На официальное мероприятие</option>
              </select>
            </label>
            <label>
              Желаемый стиль
              <input
                name="style"
                maxLength={80}
                placeholder="Например, casual или minimalism"
              />
            </label>
            <label>
              Сезон
              <select name="season">
                {Object.entries(seasons).map(([v, t]) => (
                  <option key={v} value={v}>
                    {t}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Количество вариантов
              <select name="count">
                {[3, 4, 5].map((n) => (
                  <option key={n}>{n}</option>
                ))}
              </select>
            </label>
          </div>
          <label>
            Приоритет комфорта <span className="muted">{priority}%</span>
            <input
              type="range"
              min="0"
              max="100"
              value={priority}
              onChange={(e) => setPriority(Number(e.target.value))}
            />
            <span className="range-labels">
              <span>Внешний вид</span>
              <span>Комфорт</span>
            </span>
          </label>
          <div className="step-heading">
            <span>02</span>
            <h2>Погода и цвета</h2>
          </div>
          <label className="check-row">
            <input
              type="checkbox"
              checked={weather}
              onChange={(e) => setWeather(e.target.checked)}
            />{" "}
            Использовать Open-Meteo для выбранного города
          </label>
          {weather ? (
            <>
              <p className="form-hint">
                Сначала выберите город и координаты в{" "}
                <Link href="/settings">настройках</Link>. При сбое сервис не
                подставляет фиктивную погоду.
              </p>
              <div className="form-grid">
                <label>
                  Когда? (время вашего браузера)
                  <input type="datetime-local" name="forecast_at" />
                </label>
                <label>
                  Если прогноз недоступен
                  <select name="weather_failure">
                    <option value="continue">Продолжить без погоды</option>
                    <option value="abort">Остановить подбор</option>
                  </select>
                </label>
              </div>
            </>
          ) : (
            <label>
              Температура вручную, °C
              <input
                type="number"
                name="temperature_c"
                min="-60"
                max="60"
                step="0.1"
                placeholder="Необязательно — иначе погода не оценивается"
              />
            </label>
          )}
          <label className="check-row">
            <input
              type="checkbox"
              checked={overrideColors}
              onChange={(e) => setOverrideColors(e.target.checked)}
            />{" "}
            Задать цвета для этого запроса
          </label>
          {overrideColors && (
            <ColorChoices
              label="Предпочитаемые цвета"
              colors={colors.data || []}
              selected={preferred}
              onChange={setPreferred}
            />
          )}
          <div className="step-heading">
            <span>03</span>
            <h2>Вещи, на которые рассчитываем</h2>
          </div>
          {wardrobe.loading ? (
            <Loading />
          ) : (
            <div className="selection-list">
              {wardrobe.data?.length ? (
                wardrobe.data.map((item) => (
                  <div className="selection-row" key={item.id}>
                    <span>
                      {item.name}
                      {!item.is_available && <small> · недоступна</small>}
                    </span>
                    <label>
                      <input
                        type="checkbox"
                        aria-label={`Обязательно: ${item.name}`}
                        disabled={
                          !item.is_available || excluded.includes(item.id)
                        }
                        checked={required.includes(item.id)}
                        onChange={(e) =>
                          setRequired(
                            e.target.checked
                              ? [...required, item.id]
                              : required.filter((id) => id !== item.id),
                          )
                        }
                      />{" "}
                      Включить
                    </label>
                    <label>
                      <input
                        type="checkbox"
                        aria-label={`Исключить: ${item.name}`}
                        disabled={required.includes(item.id)}
                        checked={excluded.includes(item.id)}
                        onChange={(e) =>
                          setExcluded(
                            e.target.checked
                              ? [...excluded, item.id]
                              : excluded.filter((id) => id !== item.id),
                          )
                        }
                      />{" "}
                      Исключить
                    </label>
                  </div>
                ))
              ) : (
                <p>
                  Гардероб пока пуст. <Link href="/add">Добавить вещи</Link>
                </p>
              )}
            </div>
          )}
          <label>
            Дополнительные пожелания
            <textarea
              name="notes"
              maxLength={1000}
              rows={3}
              placeholder="Сохраняются с запросом; строгие условия задавайте полями выше."
            />
          </label>
          <p className="form-hint">
            Генератор пока не интерпретирует свободный текст. Для обсуждения
            пожеланий есть отдельный AI-стилист.
          </p>
          <button
            className="button full large"
            disabled={busy || wardrobe.loading || !wardrobe.data?.length}
          >
            <Sparkles size={19} />
            {busy ? "Ищем ваши сочетания…" : "Создать мой образ"}
          </button>
        </form>
        <aside className="create-aside">
          <div className="lavender-card">
            <Sparkles size={30} />
            <h2>
              Вдохновение уже
              <br />в вашем гардеробе.
            </h2>
            <p>
              Мы проверяем категории, слои, цвета и ваши предпочтения. Каждая
              вещь в результате — ваша настоящая вещь.
            </p>
          </div>
          <div className="panel note-card">
            <h3>Небольшая подсказка</h3>
            <p>
              Для полного образа нужны обувь и либо платье, либо верх с низом. В
              холодную погоду понадобится внешний слой.
            </p>
            <p>
              Оценка — ориентир алгоритма, а не объективная мера вашего стиля.
            </p>
          </div>
        </aside>
      </div>
    </>
  );
}
export function OutfitResults({ ids }: { ids: string }) {
  const [outfits, setOutfits] = useState<Outfit[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    const list = ids.split(",");
    if (list.length > 5 || !list.every((id) => /^\d+$/.test(id))) {
      setError("Некорректный список образов.");
      setLoading(false);
      return;
    }
    Promise.all(list.map((id) => api<Outfit>(`/api/outfits/${id}/`)))
      .then((rows) => {
        if (active) setOutfits(rows);
      })
      .catch((err) => {
        if (active) setError(errorText(err));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [ids]);
  return (
    <>
      <Heading
        eyebrow="НОВЫЙ ВЗГЛЯД НА ВАШИ ВЕЩИ"
        title="Нашли ваши сочетания"
        subtitle="Образы сохранены в истории. Рассмотрите детали и выберите любимый."
        action={
          <Link className="button secondary" href="/create">
            <RefreshCw size={17} /> Ещё один запрос
          </Link>
        }
      />
      <Notice>{error}</Notice>
      {Array.from(
        new Set(outfits.flatMap((o) => o.generation.messages || [])),
      ).map((m) => (
        <Notice key={m} kind="info">
          {m}
        </Notice>
      ))}
      {loading ? (
        <Loading />
      ) : (
        <div className="outfit-grid">
          {outfits.map((outfit) => (
            <OutfitCard key={outfit.id} outfit={outfit} />
          ))}
        </div>
      )}
      <Notice kind="info">
        Если вариантов меньше, чем вы просили, значит, совместимых комплектов
        недостаточно. Новые вещи и дубликаты не выдумываются.
      </Notice>
    </>
  );
}
export function OutfitsPage({ savedOnly = false }: { savedOnly?: boolean }) {
  const outfits = useData<Outfit[]>("/api/outfits/", true);
  const saved = useData<Saved[]>("/api/saved-outfits/", true);
  const [error, setError] = useState("");
  const rows =
    outfits.data?.filter(
      (o) => !savedOnly || saved.data?.some((s) => s.outfit === o.id),
    ) || [];
  async function toggle(outfit: Outfit) {
    try {
      const entry = saved.data?.find((s) => s.outfit === outfit.id);
      await api(
        entry ? `/api/saved-outfits/${entry.id}/` : "/api/saved-outfits/",
        entry ? "DELETE" : "POST",
        entry ? undefined : { outfit: outfit.id },
      );
      saved.reload();
    } catch (err) {
      setError(errorText(err));
    }
  }
  return (
    <>
      <Heading
        eyebrow={
          savedOnly ? "ТОЛЬКО ТО, ЧТО В САМОЕ СЕРДЦЕ" : "ВАШ СТИЛЬ В ИСТОРИЯХ"
        }
        title={savedOnly ? "Любимые образы" : "История образов"}
        subtitle={
          savedOnly
            ? "Сочетания, к которым хочется вернуться."
            : "Все созданные вами образы. Новый взгляд на привычные вещи."
        }
        action={
          <Link className="button" href="/create">
            <Sparkles size={18} /> Создать образ
          </Link>
        }
      />
      <Notice>{error || outfits.error || saved.error}</Notice>
      {outfits.loading || saved.loading ? (
        <Loading />
      ) : !rows.length ? (
        <Empty
          title={
            savedOnly
              ? "Здесь будут любимые образы"
              : "Первый образ ещё впереди"
          }
          action={
            <Link className="button" href="/create">
              Создать образ
            </Link>
          }
        >
          Создайте комплект и добавьте понравившийся вариант в избранное.
        </Empty>
      ) : (
        <div className="outfit-grid">
          {rows.map((outfit) => (
            <OutfitCard key={outfit.id} outfit={outfit}>
              <button
                className="button secondary small full"
                onClick={() => void toggle(outfit)}
              >
                <Heart
                  size={16}
                  fill={
                    saved.data?.some((s) => s.outfit === outfit.id)
                      ? "currentColor"
                      : "none"
                  }
                />
                {saved.data?.some((s) => s.outfit === outfit.id)
                  ? "Убрать из избранного"
                  : "В избранное"}
              </button>
            </OutfitCard>
          ))}
        </div>
      )}
    </>
  );
}
export function OutfitDetail({ id }: { id: string }) {
  const outfit = useData<Outfit>(
    /^\d+$/.test(id) ? `/api/outfits/${id}/` : null,
  );
  const categories = useData<Category[]>("/api/categories/", true);
  const saved = useData<Saved[]>("/api/saved-outfits/", true);
  const feedback = useData<{ id: number; outfit: number; rating: number }[]>(
    "/api/feedback/",
    true,
  );
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const router = useRouter();
  if (outfit.loading) return <Loading />;
  if (outfit.error || !outfit.data)
    return <Notice>{outfit.error || "Образ не найден."}</Notice>;
  const o = outfit.data;
  const entry = saved.data?.find((s) => s.outfit === o.id);
  const rating = feedback.data?.find((f) => f.outfit === o.id);
  return (
    <>
      <Link href="/outfits" className="text-link back-link">
        <ArrowLeft size={16} /> Все образы
      </Link>
      <Heading
        eyebrow="СОЗДАНО ИЗ ВАШЕГО ГАРДЕРОБА"
        title={o.name}
        subtitle={new Date(o.created_at).toLocaleDateString("ru-RU")}
      />
      <Notice>{error || saved.error || feedback.error}</Notice>
      <Notice kind="success">{success}</Notice>
      <div className="detail-layout">
        <div>
          <div className="detail-preview">
            <OutfitPreview outfit={o} />
          </div>
          <div className="detail-items">
            {o.item_details.map((item) => (
              <div className="panel" key={item.id}>
                <h3>{item.name}</h3>
                <p>
                  {categories.data?.find((c) => c.id === item.category)?.name}
                </p>
                {!item.is_available && (
                  <span className="pill">Сейчас недоступна</span>
                )}
              </div>
            ))}
          </div>
        </div>
        <section className="panel detail-info">
          <h2>Почему этот образ?</h2>
          {o.generation_is_stale && (
            <Notice kind="info">
              Вещи изменились. Прежняя оценка устарела — создайте новый образ.
            </Notice>
          )}
          {o.generation.score !== undefined && !o.generation_is_stale && (
            <div className="score">
              <strong>{o.generation.score}</strong>
              <span>
                / 100
                <br />
                ориентир совместимости
              </span>
            </div>
          )}
          {o.generation.criteria &&
            Object.entries(o.generation.criteria).map(([key, value]) => (
              <div className="criterion" key={key}>
                <span>{criteria[key] || key}</span>
                <span>{value === null ? "Не оценено" : `${value} / 100`}</span>
              </div>
            ))}
          {o.generation.explanation?.map((text) => (
            <p key={text}>{text}</p>
          ))}
          {o.generation.warnings?.map((text) => (
            <Notice key={text} kind="info">
              {text}
            </Notice>
          ))}
          {o.generation.score === undefined && (
            <p>
              Образ сохранён вручную или его состав изменён. Автоматической
              оценки нет.
            </p>
          )}
          <button
            className="button full"
            onClick={async () => {
              try {
                await api(
                  entry
                    ? `/api/saved-outfits/${entry.id}/`
                    : "/api/saved-outfits/",
                  entry ? "DELETE" : "POST",
                  entry ? undefined : { outfit: o.id },
                );
                saved.reload();
              } catch (err) {
                setError(errorText(err));
              }
            }}
          >
            <Heart size={17} fill={entry ? "currentColor" : "none"} />
            {entry ? "Убрать из избранного" : "Сохранить в избранное"}
          </button>
          <Link className="button secondary full" href="/calendar">
            <CalendarPlus size={17} /> Запланировать в календаре
          </Link>
          <Link className="text-link" href="/create">
            <RefreshCw size={16} /> Изменить пожелания и создать новый
          </Link>
          <fieldset className="rating">
            <legend>Насколько вам нравится образ?</legend>
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                aria-label={`Оценить на ${n}`}
                className="icon-button"
                onClick={async () => {
                  try {
                    await api(
                      rating ? `/api/feedback/${rating.id}/` : "/api/feedback/",
                      rating ? "PATCH" : "POST",
                      { outfit: o.id, rating: n },
                    );
                    feedback.reload();
                    setSuccess("Спасибо! Оценка сохранена.");
                  } catch (err) {
                    setError(errorText(err));
                  }
                }}
              >
                <Star
                  size={22}
                  fill={n <= (rating?.rating || 0) ? "currentColor" : "none"}
                />
              </button>
            ))}
          </fieldset>
          <button
            className="text-link danger"
            onClick={async () => {
              if (!confirm("Удалить этот образ из истории?")) return;
              try {
                await api(`/api/outfits/${o.id}/`, "DELETE");
                router.push("/outfits");
              } catch (err) {
                setError(errorText(err));
              }
            }}
          >
            <Trash2 size={16} /> Удалить образ
          </button>
        </section>
      </div>
    </>
  );
}
