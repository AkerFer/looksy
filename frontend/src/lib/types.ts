export type Page<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};
export type Category = { id: number; name: string; slot: string };
export type Color = { id: number; name: string; hex_code: string };
export type Photo = {
  version?: number;
  url: string;
  original_url: string;
  analysis: {
    recognition?: { status: string; message?: string };
    warnings?: string[];
    background?: string;
    colors?: { hex: string; share: number }[];
  };
};
export type Clothing = {
  id: number;
  name: string;
  category: number;
  category_slot?: string;
  colors: number[];
  description: string;
  season: string;
  is_available: boolean;
  brand: string;
  material: string;
  fit: string;
  styles: string[];
  comfort: number | null;
  warmth: number | null;
  photo: Photo | null;
};
export type Generation = {
  messages?: string[];
  score?: number;
  criteria?: Record<string, number | null>;
  explanation?: string[];
  warnings?: string[];
};
export type Outfit = {
  id: number;
  name: string;
  items: number[];
  item_details: Clothing[];
  generation: Generation;
  generation_is_stale: boolean;
  created_at: string;
};
export type Saved = { id: number; outfit: number };
export type CalendarEntry = {
  id: number;
  outfit: number;
  outfit_details: Outfit;
  date: string;
  note: string;
};
export type Profile = {
  id: number;
  display_name: string;
  city: string;
  latitude: string | null;
  longitude: string | null;
  cold_sensitivity: number;
  heat_sensitivity: number;
  avatar: Photo | null;
};
export type Preference = {
  id: number;
  styles: string[];
  preferred_colors: number[];
  disliked_colors: number[];
  preferred_fit: string;
  comfort_priority: number;
  excluded_categories: number[];
};
export type Forecast = {
  temperature_c: number;
  apparent_temperature_c: number;
  wind_speed_kmh: number;
  precipitation_probability: number;
  forecast_for: string;
  id: number;
};
export type Location = {
  id: number;
  name: string;
  region: string;
  country: string;
  latitude: number;
  longitude: number;
};
export type StylistReply = {
  source: "rules" | "ollama";
  message: string;
  items: Clothing[];
  missing_slots: string[];
  warnings: string[];
};
