"use client";
import { useState, type FormEvent } from "react";
import {
  MapPin,
  Search,
  UserRound,
  Heart,
  ShieldCheck,
  Upload,
} from "lucide-react";
import { api } from "@/lib/api";
import type {
  Profile,
  Preference,
  Color,
  Category,
  Location,
} from "@/lib/types";
import {
  Heading,
  useData,
  Notice,
  Loading,
  PhotoImage,
  errorText,
  useSession,
} from "./core";
import { ColorChoices, fits } from "./wardrobe";
function ProfileForm({
  profile,
  onSaved,
}: {
  profile: Profile;
  onSaved: () => void;
}) {
  const [city, setCity] = useState(profile.city);
  const [lat, setLat] = useState(profile.latitude || "");
  const [lon, setLon] = useState(profile.longitude || "");
  const [locations, setLocations] = useState<Location[]>([]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);
  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setSuccess("");
    const f = new FormData(e.currentTarget);
    try {
      await api("/api/profile/", "PATCH", {
        display_name: f.get("display_name"),
        city,
        latitude: lat || null,
        longitude: lon || null,
        cold_sensitivity: Number(f.get("cold_sensitivity")),
        heat_sensitivity: Number(f.get("heat_sensitivity")),
      });
      setSuccess("Профиль сохранён.");
      onSaved();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel form-panel">
      <div className="step-heading">
        <UserRound size={22} />
        <h2>Немного о вас</h2>
      </div>
      <Notice>{error}</Notice>
      <Notice kind="success">{success}</Notice>
      <div className="avatar-editor">
        <PhotoImage
          url={profile.avatar?.url}
          version={profile.avatar?.version}
          alt="Ваш аватар"
        />
        <div>
          <label className="button secondary small file-label">
            <Upload size={16} /> Загрузить аватар
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              capture="user"
              disabled={busy}
              onChange={async (e) => {
                const file = e.target.files?.[0];
                e.target.value = "";
                if (!file) return;
                if (file.size > 5 * 1024 * 1024) {
                  setError("Файл должен быть не больше 5 МБ.");
                  return;
                }
                setBusy(true);
                try {
                  const fd = new FormData();
                  fd.set("image", file);
                  await api("/api/profile/avatar/", "POST", fd);
                  onSaved();
                  setSuccess("Аватар обновлён.");
                } catch (err) {
                  setError(errorText(err));
                } finally {
                  setBusy(false);
                }
              }}
            />
          </label>
          <p className="form-hint">До 5 МБ. Изображение видно только вам.</p>
          {profile.avatar && (
            <button
              className="text-link danger"
              disabled={busy}
              onClick={async () => {
                try {
                  await api("/api/profile/avatar/", "DELETE");
                  onSaved();
                } catch (err) {
                  setError(errorText(err));
                }
              }}
            >
              Удалить аватар
            </button>
          )}
        </div>
      </div>
      <form onSubmit={save}>
        <label>
          Ваше имя
          <input
            name="display_name"
            maxLength={100}
            defaultValue={profile.display_name}
          />
        </label>
        <label>
          Город
          <input
            value={city}
            maxLength={150}
            onChange={(e) => {
              setCity(e.target.value);
              setLat("");
              setLon("");
            }}
            placeholder="Введите город"
          />
        </label>
        <button
          className="button secondary small"
          type="button"
          disabled={busy || city.trim().length < 2}
          onClick={async () => {
            setBusy(true);
            setError("");
            setLocations([]);
            try {
              const result = await api<{ results: Location[] }>(
                "/api/locations/?search=" + encodeURIComponent(city),
              );
              setLocations(result.results);
              if (!result.results.length)
                setError(
                  "Город не найден. Уточните название или укажите координаты вручную.",
                );
            } catch (err) {
              setError(errorText(err));
            } finally {
              setBusy(false);
            }
          }}
        >
          <Search size={16} /> Найти город
        </button>
        {locations.length > 0 && (
          <div className="location-results">
            {locations.map((l) => (
              <button
                type="button"
                key={l.id}
                onClick={() => {
                  setCity(l.name);
                  setLat(l.latitude.toFixed(5));
                  setLon(l.longitude.toFixed(5));
                  setLocations([]);
                }}
              >
                <MapPin size={16} />
                {l.name} · {l.region} · {l.country}
              </button>
            ))}
          </div>
        )}
        <div className="form-grid">
          <label>
            Широта
            <input
              type="number"
              min="-90"
              max="90"
              step="0.00001"
              value={lat}
              onChange={(e) => setLat(e.target.value)}
              placeholder="Можно указать вручную"
            />
          </label>
          <label>
            Долгота
            <input
              type="number"
              min="-180"
              max="180"
              step="0.00001"
              value={lon}
              onChange={(e) => setLon(e.target.value)}
              placeholder="Можно указать вручную"
            />
          </label>
          <label>
            Чувствительность к холоду
            <select
              name="cold_sensitivity"
              defaultValue={profile.cold_sensitivity}
            >
              {[1, 2, 3, 4, 5].map((n) => (
                <option value={n} key={n}>
                  {n} / 5
                </option>
              ))}
            </select>
          </label>
          <label>
            Чувствительность к жаре
            <select
              name="heat_sensitivity"
              defaultValue={profile.heat_sensitivity}
            >
              {[1, 2, 3, 4, 5].map((n) => (
                <option value={n} key={n}>
                  {n} / 5
                </option>
              ))}
            </select>
          </label>
        </div>
        <p className="form-hint">
          Чем выше чувствительность, тем сильнее ощущается холод или жара.
          Геолокация не требуется.
        </p>
        <button className="button" disabled={busy}>
          {busy ? "Подождите…" : "Сохранить профиль"}
        </button>
      </form>
    </section>
  );
}
function PreferenceForm({
  preference,
  colors,
  categories,
}: {
  preference: Preference;
  colors: Color[];
  categories: Category[];
}) {
  const [preferred, setPreferred] = useState(preference.preferred_colors);
  const [disliked, setDisliked] = useState(preference.disliked_colors);
  const [excluded, setExcluded] = useState(preference.excluded_categories);
  const [priority, setPriority] = useState(preference.comfort_priority);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setSuccess("");
    const f = new FormData(e.currentTarget);
    try {
      await api("/api/preferences/", "PATCH", {
        styles: String(f.get("styles"))
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        preferred_fit: f.get("preferred_fit"),
        comfort_priority: priority,
        preferred_colors: preferred,
        disliked_colors: disliked,
        excluded_categories: excluded,
      });
      setSuccess("Предпочтения сохранены. Они будут учтены в новых образах.");
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel form-panel">
      <div className="step-heading">
        <Heart size={22} />
        <h2>То, что вам близко</h2>
      </div>
      <Notice>{error}</Notice>
      <Notice kind="success">{success}</Notice>
      <form onSubmit={submit}>
        <label>
          Любимые стили через запятую
          <input
            name="styles"
            defaultValue={preference.styles.join(", ")}
            placeholder="casual, minimalism, business"
          />
        </label>
        <p className="form-hint">
          Используйте одинаковые метки здесь и в карточках вещей: разные языки
          не переводятся автоматически.
        </p>
        <label>
          Предпочтительный крой
          <select name="preferred_fit" defaultValue={preference.preferred_fit}>
            {Object.entries(fits).map(([v, t]) => (
              <option key={v} value={v}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label>
          Приоритет комфорта: {priority}%
          <input
            type="range"
            value={priority}
            min="0"
            max="100"
            onChange={(e) => setPriority(Number(e.target.value))}
          />
        </label>
        <ColorChoices
          label="Любимые цвета"
          colors={colors}
          selected={preferred}
          onChange={setPreferred}
        />
        <ColorChoices
          label="Нежелательные цвета"
          colors={colors}
          selected={disliked}
          onChange={setDisliked}
        />
        <fieldset>
          <legend>Не использовать эти категории</legend>
          <div className="category-checks">
            {categories.map((c) => (
              <label className="check-row" key={c.id}>
                <input
                  type="checkbox"
                  checked={excluded.includes(c.id)}
                  onChange={(e) =>
                    setExcluded(
                      e.target.checked
                        ? [...excluded, c.id]
                        : excluded.filter((id) => id !== c.id),
                    )
                  }
                />
                {c.name}
              </label>
            ))}
          </div>
        </fieldset>
        <button className="button" disabled={busy}>
          {busy ? "Сохраняем…" : "Сохранить предпочтения"}
        </button>
      </form>
    </section>
  );
}
export function Settings() {
  const profile = useData<Profile>("/api/profile/");
  const preferences = useData<Preference>("/api/preferences/");
  const colors = useData<Color[]>("/api/colors/", true);
  const categories = useData<Category[]>("/api/categories/", true);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(false);
  return (
    <>
      <Heading
        eyebrow="ПО ВАШИМ ПРАВИЛАМ"
        title="Профиль и предпочтения"
        subtitle="Расскажите о себе, чтобы новые сочетания были ближе к вам."
      />
      <Notice>
        {profile.error || preferences.error || colors.error || categories.error}
      </Notice>
      {(profile.loading && !profile.data) ||
      (preferences.loading && !preferences.data) ||
      (colors.loading && !colors.data) ||
      (categories.loading && !categories.data) ? (
        <Loading />
      ) : (
        <div className="settings-grid">
          {profile.data && (
            <ProfileForm profile={profile.data} onSaved={profile.reload} />
          )}{" "}
          {preferences.data && (
            <PreferenceForm
              preference={preferences.data}
              colors={colors.data || []}
              categories={categories.data || []}
            />
          )}
        </div>
      )}
      <section className="panel account-danger">
        <div>
          <span className="eyebrow">
            <ShieldCheck size={16} /> ВАШИ ДАННЫЕ ПОД ВАШИМ КОНТРОЛЕМ
          </span>
          <h2>Удаление аккаунта</h2>
          <p>
            Гардероб, фотографии, образы и связанные данные будут удалены без
            возможности восстановления.
          </p>
        </div>
        <Notice>{error}</Notice>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            if (
              !confirm(
                "Удалить аккаунт и все связанные данные? Это действие нельзя отменить.",
              )
            )
              return;
            setDeleting(true);
            const f = new FormData(e.currentTarget);
            try {
              await api("/api/account/", "DELETE", {
                password: f.get("password"),
              });
              window.location.href = "/";
            } catch (err) {
              setError(errorText(err));
              setDeleting(false);
            }
          }}
        >
          <label>
            Текущий пароль
            <input
              name="password"
              type="password"
              required
              autoComplete="current-password"
            />
          </label>
          <button className="button danger-button" disabled={deleting}>
            {deleting ? "Удаляем…" : "Удалить аккаунт и данные"}
          </button>
        </form>
      </section>
    </>
  );
}
