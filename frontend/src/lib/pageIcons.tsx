import type { LucideIcon } from "lucide-react";
import {
  Bot,
  BookOpen,
  Briefcase,
  Brain,
  Camera,
  Code,
  Dumbbell,
  FileText,
  Film,
  FlaskConical,
  Gamepad2,
  Globe,
  GraduationCap,
  HeartPulse,
  Home,
  Landmark,
  Music,
  Newspaper,
  Palette,
  Plane,
  Rocket,
  Sparkles,
  TrendingUp,
  Trophy,
  Utensils,
} from "lucide-react";

/** Page icons are stored by name; unknown values render as emoji (legacy). */
export const PAGE_ICONS: Record<string, LucideIcon> = {
  "file-text": FileText,
  home: Home,
  newspaper: Newspaper,
  bot: Bot,
  brain: Brain,
  flask: FlaskConical,
  "trending-up": TrendingUp,
  landmark: Landmark,
  trophy: Trophy,
  dumbbell: Dumbbell,
  gamepad: Gamepad2,
  palette: Palette,
  film: Film,
  music: Music,
  camera: Camera,
  "book-open": BookOpen,
  "graduation-cap": GraduationCap,
  briefcase: Briefcase,
  code: Code,
  rocket: Rocket,
  globe: Globe,
  plane: Plane,
  utensils: Utensils,
  "heart-pulse": HeartPulse,
  sparkles: Sparkles,
};

export function PageIcon({ icon, size = 16 }: { icon: string; size?: number }) {
  const Icon = PAGE_ICONS[icon];
  if (Icon) return <Icon size={size} className="shrink-0" />;
  // Legacy pages stored an emoji — render it as-is.
  return <span className="shrink-0 leading-none" style={{ fontSize: size }}>{icon}</span>;
}
