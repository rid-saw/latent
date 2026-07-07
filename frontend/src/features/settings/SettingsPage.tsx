import { Moon, Sparkles, Sun } from "lucide-react";
import { useSettings } from "@/stores/settings";

const REFRESH_OPTIONS = [
  { label: "Off", value: 0 },
  { label: "5m", value: 5 },
  { label: "15m", value: 15 },
  { label: "30m", value: 30 },
];

export function SettingsPage() {
  const {
    theme,
    setTheme,
    rundownEnabled,
    setRundownEnabled,
    autoRefreshMins,
    setAutoRefreshMins,
  } = useSettings();

  return (
    <div className="flex-1 overflow-auto p-6">
      <h1 className="text-lg font-semibold">Settings</h1>
      <p className="mb-6 text-sm text-faint">Appearance and behavior.</p>

      <div className="max-w-lg space-y-3">
        <Row
          title="Theme"
          description="Eggshell light or deep-brown dark."
          control={
            <div className="flex rounded-lg border border-line p-0.5">
              <ModeButton
                active={theme === "light"}
                onClick={() => setTheme("light")}
                icon={<Sun size={14} />}
                label="Light"
              />
              <ModeButton
                active={theme === "dark"}
                onClick={() => setTheme("dark")}
                icon={<Moon size={14} />}
                label="Dark"
              />
            </div>
          }
        />
        <Row
          title="Auto-refresh"
          description="Quietly refetch every block's content on an interval."
          control={
            <div className="flex rounded-lg border border-line p-0.5">
              {REFRESH_OPTIONS.map((o) => (
                <button
                  key={o.value}
                  onClick={() => setAutoRefreshMins(o.value)}
                  className={
                    "rounded-md px-2.5 py-1.5 text-xs " +
                    (autoRefreshMins === o.value
                      ? "bg-ink text-bg"
                      : "text-soft hover:text-ink")
                  }
                >
                  {o.label}
                </button>
              ))}
            </div>
          }
        />
        <Row
          title="The Rundown"
          description="Auto-generate the briefing when the dashboard loads."
          control={<Switch checked={rundownEnabled} onChange={setRundownEnabled} />}
          icon={<Sparkles size={15} className="text-accent" />}
        />
      </div>
    </div>
  );
}

function Row({
  title,
  description,
  control,
  icon,
}: {
  title: string;
  description: string;
  control: React.ReactNode;
  icon?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-6 rounded-xl border border-line bg-card p-4">
      <div>
        <p className="flex items-center gap-2 text-sm font-medium">
          {icon}
          {title}
        </p>
        <p className="mt-0.5 text-xs text-faint">{description}</p>
      </div>
      {control}
    </div>
  );
}

function ModeButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={
        "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs " +
        (active ? "bg-ink text-bg" : "text-soft hover:text-ink")
      }
    >
      {icon}
      {label}
    </button>
  );
}

export function Switch({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={
        "relative inline-block h-6 w-11 shrink-0 rounded-full transition-colors " +
        (checked ? "bg-accent" : "bg-line")
      }
    >
      <span
        className={
          "absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-card shadow transition-transform " +
          (checked ? "translate-x-0" : "translate-x-5")
        }
      />
    </button>
  );
}
