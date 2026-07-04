import { useEffect, useState } from "react";
import { Layers, Settings } from "lucide-react";
import { Dashboard } from "@/features/dashboard/Dashboard";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { GoogleConnectCard } from "@/features/sources/GoogleConnectCard";
import { useSettings } from "@/stores/settings";

type View = "dashboard" | "settings";

export default function App() {
  const theme = useSettings((s) => s.theme);
  const [view, setView] = useState<View>("dashboard");

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  return (
    <div className="flex h-full">
      <aside className="flex w-56 flex-col border-r border-line bg-surface/60 p-4">
        <div className="mb-6 flex items-center gap-2 px-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-ink text-sm font-bold text-bg">
            l
          </div>
          <span className="font-semibold">latent</span>
        </div>

        <nav className="space-y-1 text-sm">
          <NavItem
            icon={<Layers size={16} />}
            label="Dashboard"
            active={view === "dashboard"}
            onClick={() => setView("dashboard")}
          />
          <NavItem
            icon={<Settings size={16} />}
            label="Settings"
            active={view === "settings"}
            onClick={() => setView("settings")}
          />
        </nav>

        <GoogleConnectCard />
      </aside>

      <main className="flex flex-1 flex-col overflow-hidden">
        {view === "dashboard" ? <Dashboard /> : <SettingsPage />}
      </main>
    </div>
  );
}

function NavItem({
  icon,
  label,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={
        "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left " +
        (active ? "bg-surface text-ink" : "text-soft hover:bg-surface/70 hover:text-ink")
      }
    >
      {icon}
      {label}
    </button>
  );
}
