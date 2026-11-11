"use client";
import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useRef,
  type ReactNode,
} from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Sparkles,
  LayoutDashboard,
  Shirt,
  WandSparkles,
  Heart,
  MessageCircle,
  CalendarDays,
  Settings,
  LogOut,
  Moon,
  Sun,
  Plus,
  ArrowUpRight,
  Menu,
  ImageOff,
  X,
} from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { api, all } from "@/lib/api";
import type { Outfit } from "@/lib/types";

type Account = { id: number; username: string; email: string };
const SessionContext = createContext<{
  user: Account | null;
  loading: boolean;
  refresh: () => Promise<void>;
}>({ user: null, loading: true, refresh: async () => {} });
export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Account | null>(null);
  const [loading, setLoading] = useState(true);
  const refresh = useCallback(async () => {
    try {
      const session = await api<{ authenticated: boolean }>(
        "/api/auth/session/",
      );
      setUser(
        session.authenticated ? await api<Account>("/api/account/") : null,
      );
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    void refresh();
    const theme = localStorage.getItem("looksy-theme");
    if (theme) document.documentElement.dataset.theme = theme;
  }, [refresh]);
  return (
    <SessionContext.Provider value={{ user, loading, refresh }}>
      {children}
    </SessionContext.Provider>
  );
}
export const useSession = () => useContext(SessionContext);
export function useData<T>(path: string | null, collection = false) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [version, setVersion] = useState(0);
  useEffect(() => {
    let active = true;
    if (!path) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    (collection ? all(path) : api(path))
      .then((value) => {
        if (active) setData(value as T);
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
  }, [path, collection, version]);
  return { data, error, loading, reload: () => setVersion((v) => v + 1) };
}
export function errorText(error: unknown) {
  return error instanceof Error
    ? error.message
    : "Не удалось выполнить действие.";
}
export function Notice({
  children,
  kind = "error",
}: {
  children: ReactNode;
  kind?: "error" | "info" | "success";
}) {
  return children ? (
    <div
      className={`notice ${kind}`}
      role={kind === "error" ? "alert" : "status"}
    >
      {children}
    </div>
  ) : null;
}
export function Loading() {
  return (
    <div className="loading" role="status">
      <span className="spinner" /> Загружаем ваш Looksy…
    </div>
  );
}
export function Empty({
  title,
  children,
  action,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <div className="empty-icon">
        <Shirt size={32} />
      </div>
      <h3>{title}</h3>
      <p>{children}</p>
      {action}
    </div>
  );
}
export function Heading({
  eyebrow,
  title,
  subtitle,
  action,
}: {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <header className="page-heading">
      <div>
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {action}
    </header>
  );
}
export function Reveal({ children }: { children: ReactNode }) {
  const reduced = useReducedMotion();
  return (
    <motion.div
      initial={reduced ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
    >
      {children}
    </motion.div>
  );
}
export function PhotoImage({
  url,
  version,
  alt,
  className = "",
}: {
  url?: string | null;
  version?: number;
  alt: string;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [url]);
  return url && !failed ? (
    <img
      className={className}
      src={
        version && !url.startsWith("blob:")
          ? `${url}${url.includes("?") ? "&" : "?"}v=${version}`
          : url
      }
      alt={alt}
      loading="lazy"
      onError={() => setFailed(true)}
    />
  ) : (
    <div className={`no-photo ${className}`}>
      <ImageOff size={25} />
      <span>{failed ? "Фото недоступно" : "Без фото"}</span>
    </div>
  );
}
export function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    dialog?.showModal();
    return () => dialog?.close();
  }, []);
  return (
    <dialog
      className="modal"
      ref={ref}
      aria-label={title}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <header>
        <h2>{title}</h2>
        <button className="icon-button" onClick={onClose} aria-label="Закрыть">
          <X />
        </button>
      </header>
      {children}
    </dialog>
  );
}
export function OutfitPreview({ outfit }: { outfit: Outfit }) {
  return (
    <div className="flatlay">
      {[...outfit.item_details]
        .sort((a, b) => {
          const order: Record<string, number> = {
            top: 0,
            dress: 0,
            bottom: 1,
            outerwear: 2,
            shoes: 3,
            accessory: 4,
          };
          return (
            (order[a.category_slot || "other"] ?? 5) -
            (order[b.category_slot || "other"] ?? 5)
          );
        })
        .map((item) => (
          <PhotoImage key={item.id} url={item.photo?.url} alt={item.name} />
        ))}
    </div>
  );
}
export function OutfitCard({
  outfit,
  children,
}: {
  outfit: Outfit;
  children?: ReactNode;
}) {
  return (
    <article className="outfit-card">
      <OutfitPreview outfit={outfit} />
      <div className="card-body">
        <div className="row">
          <h3>{outfit.name}</h3>
          {outfit.generation.score !== undefined && (
            <span className="pill">
              {outfit.generation_is_stale
                ? "Оценка устарела"
                : `${outfit.generation.score} / 100`}
            </span>
          )}
        </div>
        <p className="muted">
          {outfit.item_details.map((item) => item.name).join(" · ") ||
            "Вещи удалены"}
        </p>
        <Link className="text-link" href={`/outfits/${outfit.id}`}>
          Рассмотреть образ <ArrowUpRight size={15} />
        </Link>
        {children}
      </div>
    </article>
  );
}
const links = [
  ["/dashboard", "Обзор", LayoutDashboard],
  ["/wardrobe", "Мой гардероб", Shirt],
  ["/create", "Создать образ", WandSparkles],
  ["/outfits", "История образов", CalendarDays],
  ["/saved", "Избранное", Heart],
  ["/stylist", "AI-стилист", MessageCircle],
  ["/calendar", "Календарь", CalendarDays],
  ["/settings", "Настройки", Settings],
] as const;
export function Brand() {
  return (
    <Link href="/" className="brand">
      <span>
        <Sparkles size={22} />
      </span>
      looksy<span className="brand-dot">.</span>
    </Link>
  );
}
export function ThemeButton() {
  const [dark, setDark] = useState(false);
  useEffect(
    () =>
      setDark(
        localStorage.getItem("looksy-theme") === "dark" ||
          document.documentElement.dataset.theme === "dark",
      ),
    [],
  );
  return (
    <button
      className="icon-button"
      aria-label={dark ? "Светлая тема" : "Тёмная тема"}
      onClick={() => {
        const next = !dark;
        setDark(next);
        document.documentElement.dataset.theme = next ? "dark" : "light";
        localStorage.setItem("looksy-theme", next ? "dark" : "light");
      }}
    >
      {dark ? <Sun size={20} /> : <Moon size={20} />}
    </button>
  );
}
export function Shell({ children }: { children: ReactNode }) {
  const { user, loading, refresh } = useSession();
  const path = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!loading && !user && !leaving) router.replace("/login");
  }, [loading, user, router, leaving]);
  useEffect(() => setOpen(false), [path]);
  if (loading || !user) return <Loading />;
  return (
    <div className="workspace">
      {open && (
        <button
          className="sidebar-overlay"
          aria-label="Закрыть навигацию"
          onClick={() => setOpen(false)}
        />
      )}
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <button
          className="icon-button sidebar-close"
          aria-label="Закрыть меню"
          onClick={() => setOpen(false)}
        >
          <X size={20} />
        </button>
        <Brand />
        <p className="sidebar-caption">ВАШ ЛИЧНЫЙ СТИЛЬ</p>
        <nav>
          {links.map(([href, label, Icon]) => (
            <Link
              key={href}
              href={href}
              className={path.startsWith(href) ? "active" : ""}
              onClick={() => setOpen(false)}
            >
              <Icon size={20} />
              {label}
              {href === "/create" && <span className="nav-new">✦</span>}
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="mini-note">
            <Sparkles size={19} />
            <p>
              Хороший стиль начинается
              <br />с того, что у вас уже есть.
            </p>
          </div>
          <button
            className="logout"
            onClick={async () => {
              try {
                setLeaving(true);
                await api("/api/auth/session/", "DELETE");
                await refresh();
                router.push("/");
              } catch (err) {
                setLeaving(false);
                setError(errorText(err));
              }
            }}
          >
            <LogOut size={18} /> Выйти
          </button>
        </div>
      </aside>
      <div className="main-wrap">
        <div className="topbar">
          <div className="row">
            <button
              className="icon-button mobile-menu"
              aria-label="Открыть меню"
              aria-expanded={open}
              onClick={() => setOpen(!open)}
            >
              <Menu />
            </button>
            <span className="topbar-label">
              Меньше «нечего надеть». Больше вас.
            </span>
          </div>
          <div className="row">
            <ThemeButton />
            <Link className="user-chip" href="/settings">
              <span>{user.username.slice(0, 1).toUpperCase()}</span>
              {user.username}
            </Link>
          </div>
        </div>
        <main className="main-content">
          <Notice>{error}</Notice>
          <Reveal key={path}>{children}</Reveal>
        </main>
        <footer className="app-footer">
          Looksy · Ваш гардероб, новые возможности{" "}
          <span>С заботой о вашем стиле ✦</span>
        </footer>
      </div>
    </div>
  );
}
export function AddLink() {
  return (
    <Link className="button" href="/add">
      <Plus size={18} /> Добавить вещь
    </Link>
  );
}
