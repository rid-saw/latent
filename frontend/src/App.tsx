import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Layers, Settings } from "lucide-react";
import { Dashboard } from "@/features/dashboard/Dashboard";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { GoogleConnectCard } from "@/features/sources/GoogleConnectCard";
import { useSettings } from "@/stores/settings";

type View = "dashboard" | "settings";

export default function App() {
  const { theme, sidebarOpen, setSidebarOpen } = useSettings();
  const [view, setView] = useState<View>("dashboard");

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  const nav = [
    { key: "dashboard" as const, icon: <Layers size={16} />, label: "Dashboard" },
    { key: "settings" as const, icon: <Settings size={16} />, label: "Settings" },
  ];

  return (
    <div className="flex h-full">
      {sidebarOpen ? (
        <aside className="flex w-56 flex-col border-r border-line bg-surface/60 p-4">
          <div className="mb-6 flex items-center gap-2 px-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-ink text-sm font-bold text-bg">
              l
            </div>
            <span className="font-semibold">latent</span>
            <button
              onClick={() => setSidebarOpen(false)}
              className="ml-auto rounded-md p-1 text-faint hover:bg-surface hover:text-ink"
              title="Collapse sidebar"
            >
              <ChevronLeft size={16} />
            </button>
          </div>

          <nav className="space-y-1 text-sm">
            {nav.map((n) => (
              <button
                key={n.key}
                onClick={() => setView(n.key)}
                className={
                  "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left " +
                  (view === n.key
                    ? "bg-surface text-ink"
                    : "text-soft hover:bg-surface/70 hover:text-ink")
                }
              >
                {n.icon}
                {n.label}
              </button>
            ))}
          </nav>

          <GoogleConnectCard />
        </aside>
      ) : (
        <aside className="flex w-12 flex-col items-center border-r border-line bg-surface/60 py-4">
          <button
            onClick={() => setSidebarOpen(true)}
            className="mb-6 flex h-7 w-7 items-center justify-center rounded-lg bg-ink text-sm font-bold text-bg"
            title="Expand sidebar"
          >
            l
          </button>
          <nav className="flex flex-col items-center gap-1">
            {nav.map((n) => (
              <button
                key={n.key}
                onClick={() => setView(n.key)}
                title={n.label}
                className={
                  "rounded-lg p-2 " +
                  (view === n.key
                    ? "bg-surface text-ink"
                    : "text-soft hover:bg-surface/70 hover:text-ink")
                }
              >
                {n.icon}
              </button>
            ))}
          </nav>
          <button
            onClick={() => setSidebarOpen(true)}
            className="mt-auto rounded-md p-1.5 text-faint hover:bg-surface hover:text-ink"
            title="Expand sidebar"
          >
            <ChevronRight size={16} />
          </button>
        </aside>
      )}

      <main className="flex flex-1 flex-col overflow-hidden">
        {view === "dashboard" ? <Dashboard /> : <SettingsPage />}
      </main>
    </div>
  );
}
