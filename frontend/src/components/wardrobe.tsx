"use client";
import { useState, useEffect, type ChangeEvent, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Search,
  SlidersHorizontal,
  Pencil,
  Trash2,
  Upload,
  ArrowLeft,
  ArrowRight,
  Camera,
} from "lucide-react";
import { api } from "@/lib/api";
import type { Clothing, Category, Color, Page } from "@/lib/types";
import {
  Heading,
  AddLink,
  useData,
  Notice,
  Loading,
  Empty,
  PhotoImage,
  Modal,
  errorText,
} from "./core";
export const seasons: Record<string, string> = {
  all: "Все сезоны",
  summer: "Лето",
  winter: "Зима",
  spring: "Весна",
  autumn: "Осень",
};
export const fits: Record<string, string> = {
  unknown: "Не указан",
  regular: "Обычный",
  slim: "Приталенный",
  relaxed: "Свободный",
  oversized: "Оверсайз",
};
export function ColorChoices({
  colors,
  selected,
  onChange,
  label,
}: {
  colors: Color[];
  selected: number[];
  onChange: (ids: number[]) => void;
  label: string;
}) {
  return (
    <fieldset className="color-field">
      <legend>{label}</legend>
      <div className="color-options">
        {colors.map((color) => (
          <label
            key={color.id}
            className={selected.includes(color.id) ? "chosen" : ""}
          >
            <input
              type="checkbox"
              checked={selected.includes(color.id)}
              onChange={(e) =>
                onChange(
                  e.target.checked
                    ? [...selected, color.id]
                    : selected.filter((id) => id !== color.id),
                )
              }
            />
            <i style={{ background: color.hex_code }} />
            {color.name}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
export function ClothingEditor({
  item,
  onSaved,
  onCancel,
}: {
  item?: Clothing;
  onSaved: (item: Clothing) => void;
  onCancel: () => void;
}) {
  const categories = useData<Category[]>("/api/categories/", true);
  const colors = useData<Color[]>("/api/colors/", true);
  const [selected, setSelected] = useState(item?.colors || []);
  const [image, setImage] = useState<File>();
  const [preview, setPreview] = useState<string>();
  const [removedPhoto, setRemovedPhoto] = useState(false);
  useEffect(() => {
    if (!image) {
      setPreview(undefined);
      return;
    }
    const url = URL.createObjectURL(image);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [image]);
  function chooseFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file && file.size > 5 * 1024 * 1024) {
      setError("Файл должен быть не больше 5 МБ.");
      e.target.value = "";
      setImage(undefined);
      return;
    }
    setImage(file);
    setError("");
    setPhotoResult("");
  }
  const [draft, setDraft] = useState<number | undefined>(item?.id);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [photoResult, setPhotoResult] = useState("");
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setBusy(true);
    const fd = new FormData(e.currentTarget);
    const payload = {
      name: fd.get("name"),
      category: Number(fd.get("category")),
      colors: selected,
      description: fd.get("description"),
      season: fd.get("season"),
      brand: fd.get("brand"),
      material: fd.get("material"),
      fit: fd.get("fit"),
      styles: String(fd.get("styles"))
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      comfort: fd.get("comfort") ? Number(fd.get("comfort")) : null,
      warmth: fd.get("warmth") ? Number(fd.get("warmth")) : null,
      is_available: fd.has("is_available"),
    };
    let id = draft;
    try {
      const saved = await api<Clothing>(
        id ? `/api/clothing/${id}/` : "/api/clothing/",
        id ? "PATCH" : "POST",
        payload,
      );
      id = saved.id;
      setDraft(id);
      if (image) {
        const photo = new FormData();
        photo.set("image", image);
        await api(`/api/clothing/${id}/photo/`, "POST", photo);
      }
      onSaved(await api<Clothing>(`/api/clothing/${id}/`));
    } catch (err) {
      setError(
        (id && !item
          ? "Карточка сохранена. Проверьте данные или повторите загрузку фото. "
          : "") + errorText(err),
      );
    } finally {
      setBusy(false);
    }
  }
  if (categories.loading || colors.loading) return <Loading />;
  if (categories.error || colors.error)
    return <Notice>{categories.error || colors.error}</Notice>;
  return (
    <form className="editor-form" onSubmit={submit}>
      <Notice>{error}</Notice>
      <Notice kind="info">
        {photoResult || item?.photo?.analysis.recognition?.message}
      </Notice>
      {item?.photo?.analysis.warnings?.map((warning) => (
        <Notice key={warning} kind="info">
          {warning}
        </Notice>
      ))}
      <div className="upload-box">
        <PhotoImage
          url={preview || (removedPhoto ? null : item?.photo?.url)}
          alt={item?.name || "Новая вещь"}
        />
        <div>
          <Camera size={24} />
          <h3>{image ? image.name : "Добавьте фотографию"}</h3>
          <p>JPEG, PNG или WebP · до 5 МБ · до 16 Мп</p>
          <div className="row upload-actions">
            <label className="button secondary file-label">
              Выбрать фото
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={chooseFile}
              />
            </label>
            <label className="button secondary file-label">
              <Camera size={16} />
              Камера
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                capture="environment"
                onChange={chooseFile}
              />
            </label>
          </div>
          {item?.photo && !removedPhoto && (
            <button
              type="button"
              className="text-link danger"
              onClick={async () => {
                if (!confirm("Удалить фотографию этой вещи?")) return;
                try {
                  await api(`/api/clothing/${item.id}/photo/`, "DELETE");
                  setRemovedPhoto(true);
                  setPhotoResult(
                    "Фото удалено. После сохранения карточка обновится.",
                  );
                } catch (err) {
                  setError(errorText(err));
                }
              }}
            >
              Удалить фото
            </button>
          )}
        </div>
      </div>
      <div className="form-grid">
        <label>
          Название
          <input
            name="name"
            required
            maxLength={150}
            defaultValue={item?.name}
            placeholder="Например, любимый свитер"
          />
        </label>
        <label>
          Категория
          <select name="category" required defaultValue={item?.category || ""}>
            <option value="" disabled>
              Выберите категорию
            </option>
            {categories.data?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Сезон
          <select name="season" defaultValue={item?.season || "all"}>
            {Object.entries(seasons).map(([v, t]) => (
              <option key={v} value={v}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label>
          Крой
          <select name="fit" defaultValue={item?.fit || "unknown"}>
            {Object.entries(fits).map(([v, t]) => (
              <option key={v} value={v}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label>
          Бренд
          <input
            name="brand"
            maxLength={100}
            defaultValue={item?.brand}
            placeholder="Необязательно"
          />
        </label>
        <label>
          Материал
          <input
            name="material"
            maxLength={100}
            defaultValue={item?.material}
            placeholder="Если известен"
          />
        </label>
        <label>
          Комфорт
          <select name="comfort" defaultValue={item?.comfort || ""}>
            <option value="">Не оценён</option>
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>
                {n} / 5
              </option>
            ))}
          </select>
        </label>
        <label>
          Теплота
          <select name="warmth" defaultValue={item?.warmth || ""}>
            <option value="">Не оценена</option>
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>
                {n} / 5
              </option>
            ))}
          </select>
        </label>
      </div>
      <label>
        Стили через запятую
        <input
          name="styles"
          defaultValue={item?.styles.join(", ")}
          placeholder="casual, minimalism"
        />
      </label>
      <ColorChoices
        label="Цвета вещи"
        colors={colors.data || []}
        selected={selected}
        onChange={setSelected}
      />
      <label>
        Заметки
        <textarea
          name="description"
          maxLength={2000}
          defaultValue={item?.description}
          rows={3}
          placeholder="Что вы любите в этой вещи?"
        />
      </label>
      <label className="check-row">
        <input
          type="checkbox"
          name="is_available"
          defaultChecked={item?.is_available ?? true}
        />{" "}
        Вещь доступна для подбора
      </label>
      <div className="form-actions">
        <button
          type="button"
          className="button secondary"
          onClick={onCancel}
          disabled={busy}
        >
          Отмена
        </button>
        <button className="button" disabled={busy}>
          {busy ? "Сохраняем и обрабатываем фото…" : "Сохранить вещь"}
        </button>
      </div>
    </form>
  );
}
export function AddClothing() {
  const router = useRouter();
  return (
    <>
      <Link className="text-link back-link" href="/wardrobe">
        <ArrowLeft size={16} /> В гардероб
      </Link>
      <Heading
        eyebrow="КАЖДАЯ ВЕЩЬ — ЧАСТЬ ВАШЕЙ ИСТОРИИ"
        title="Знакомьтесь, ваша вещь"
        subtitle="Добавьте фото и немного деталей. Неизвестные характеристики можно оставить пустыми."
      />
      <section className="panel editor-panel">
        <ClothingEditor
          onSaved={() => router.push("/wardrobe")}
          onCancel={() => router.push("/wardrobe")}
        />
      </section>
    </>
  );
}
export function Wardrobe() {
  const [filters, setFilters] = useState({
    search: "",
    category: "",
    season: "",
    color: "",
    is_available: "",
    ordering: "-created_at",
  });
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<Clothing>();
  const [error, setError] = useState("");
  const query = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v) query.set(k, v);
  });
  query.set("page", String(page));
  const list = useData<Page<Clothing>>("/api/clothing/?" + query.toString());
  const categories = useData<Category[]>("/api/categories/", true);
  const colors = useData<Color[]>("/api/colors/", true);
  const update = (key: string, value: string) => {
    setFilters((f) => ({ ...f, [key]: value }));
    setPage(1);
  };
  return (
    <>
      <Heading
        eyebrow="МЕСТО ДЛЯ ЛЮБИМЫХ ВЕЩЕЙ"
        title="Мой гардероб"
        subtitle="Всё, что делает ваш стиль вашим. В одном месте."
        action={<AddLink />}
      />
      <section className="wardrobe-tools">
        <label className="search-box">
          <Search size={19} />
          <input
            aria-label="Поиск вещей"
            placeholder="Найти ту самую вещь…"
            value={filters.search}
            onChange={(e) => update("search", e.target.value)}
          />
        </label>
        <span className="result-count">{list.data?.count ?? "…"} вещей</span>
      </section>
      <div className="filter-bar">
        <SlidersHorizontal size={18} />
        <select
          aria-label="Категория"
          value={filters.category}
          onChange={(e) => update("category", e.target.value)}
        >
          <option value="">Все категории</option>
          {categories.data?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <select
          aria-label="Сезон"
          value={filters.season}
          onChange={(e) => update("season", e.target.value)}
        >
          <option value="">Любой сезон</option>
          {Object.entries(seasons).map(([v, t]) => (
            <option key={v} value={v}>
              {t}
            </option>
          ))}
        </select>
        <select
          aria-label="Цвет"
          value={filters.color}
          onChange={(e) => update("color", e.target.value)}
        >
          <option value="">Любой цвет</option>
          {colors.data?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <select
          aria-label="Доступность"
          value={filters.is_available}
          onChange={(e) => update("is_available", e.target.value)}
        >
          <option value="">Все вещи</option>
          <option value="true">Доступные</option>
          <option value="false">В стирке / недоступные</option>
        </select>
        <select
          aria-label="Сортировка"
          value={filters.ordering}
          onChange={(e) => update("ordering", e.target.value)}
        >
          <option value="-created_at">Сначала новые</option>
          <option value="name">По названию</option>
        </select>
      </div>
      <Notice>{error || list.error || categories.error || colors.error}</Notice>
      {list.loading ? (
        <Loading />
      ) : !list.data?.results.length ? (
        <Empty title="Здесь будет ваш гардероб" action={<AddLink />}>
          Добавьте первую вещь или измените фильтры. Мы не подставляем чужие
          фотографии вместо ваших.
        </Empty>
      ) : (
        <div className="clothing-grid">
          {list.data.results.map((item) => (
            <article className="clothing-card" key={item.id}>
              <button
                className="clothing-image"
                aria-label={`Открыть ${item.name}`}
                onClick={() => setEditing(item)}
              >
                <PhotoImage url={item.photo?.url} alt={item.name} />
                <span
                  className={`availability ${item.is_available ? "" : "unavailable"}`}
                >
                  {item.is_available ? "В гардеробе" : "Недоступно"}
                </span>
              </button>
              <div className="card-body">
                <span className="eyebrow tiny">
                  {categories.data?.find((c) => c.id === item.category)?.name}
                </span>
                <h3>{item.name}</h3>
                <div className="row between">
                  <div className="color-dots">
                    {item.colors.map((id) => (
                      <i
                        key={id}
                        title={colors.data?.find((c) => c.id === id)?.name}
                        style={{
                          background:
                            colors.data?.find((c) => c.id === id)?.hex_code ||
                            "transparent",
                        }}
                      />
                    ))}
                  </div>
                  <div className="row">
                    <button
                      className="icon-button"
                      aria-label={`Редактировать ${item.name}`}
                      onClick={() => setEditing(item)}
                    >
                      <Pencil size={16} />
                    </button>
                    <button
                      className="icon-button danger"
                      aria-label={`Удалить ${item.name}`}
                      onClick={async () => {
                        if (!confirm(`Удалить «${item.name}» и её фотографии?`))
                          return;
                        try {
                          await api(`/api/clothing/${item.id}/`, "DELETE");
                          list.reload();
                        } catch (err) {
                          setError(errorText(err));
                        }
                      }}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
      <div className="pagination">
        <button
          className="button secondary small"
          disabled={page === 1 || list.loading}
          onClick={() => setPage((p) => p - 1)}
        >
          <ArrowLeft size={15} /> Назад
        </button>
        <span>Страница {page}</span>
        <button
          className="button secondary small"
          disabled={!list.data?.next || list.loading}
          onClick={() => setPage((p) => p + 1)}
        >
          Далее <ArrowRight size={15} />
        </button>
      </div>
      {editing && (
        <Modal title="Детали вещи" onClose={() => setEditing(undefined)}>
          <ClothingEditor
            item={editing}
            onSaved={() => {
              setEditing(undefined);
              list.reload();
            }}
            onCancel={() => setEditing(undefined)}
          />
        </Modal>
      )}
    </>
  );
}
