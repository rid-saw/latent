import { useEffect, useState } from "react";
import { ChevronLeft, Layers, Settings } from "lucide-react";
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
      <aside
        className={
          "flex shrink-0 flex-col overflow-hidden border-r border-line bg-surface/60 transition-all duration-300 ease-in-out " +
          (sidebarOpen ? "w-56 p-4" : "w-14 p-2")
        }
      >
        <div className={"mb-6 flex items-center gap-2 " + (sidebarOpen ? "px-2" : "flex-col gap-3")}>
          <button
            onClick={() => !sidebarOpen && setSidebarOpen(true)}
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-ink text-sm font-bold text-bg"
            title={sidebarOpen ? undefined : "Expand sidebar"}
          >
            l
          </button>
          {sidebarOpen && <span className="whitespace-nowrap font-semibold">latent</span>}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className={
              "rounded-md p-1 text-faint hover:bg-surface hover:text-ink " +
              (sidebarOpen ? "ml-auto" : "")
            }
            title={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
          >
            <ChevronLeft
              size={16}
              className={
                "transition-transform duration-300 " + (sidebarOpen ? "" : "rotate-180")
              }
            />
          </button>
        </div>

        <nav className={"space-y-1 text-sm " + (sidebarOpen ? "" : "flex flex-col items-center")}>
          {nav.map((n) => (
            <button
              key={n.key}
              onClick={() => setView(n.key)}
              title={sidebarOpen ? undefined : n.label}
              className={
                "flex items-center gap-3 rounded-lg py-2 " +
                (sidebarOpen ? "w-full px-3 text-left " : "justify-center p-2 ") +
                (view === n.key
                  ? "bg-surface text-ink"
                  : "text-soft hover:bg-surface/70 hover:text-ink")
              }
            >
              {n.icon}
              {sidebarOpen && <span className="whitespace-nowrap">{n.label}</span>}
            </button>
          ))}
        </nav>

        {sidebarOpen && <GoogleConnectCard />}
      </aside>

      <main className="flex flex-1 flex-col overflow-hidden">
        {view === "dashboard" ? <Dashboard /> : <SettingsPage />}
      </main>
    </div>
  );
}
