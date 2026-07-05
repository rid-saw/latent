import { useEffect, useState } from "react";
import { ChevronLeft, FileText, Plus, Settings, Trash2 } from "lucide-react";
import { Dashboard } from "@/features/dashboard/Dashboard";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { GoogleConnectCard } from "@/features/sources/GoogleConnectCard";
import { usePages } from "@/stores/pages";
import { useSettings } from "@/stores/settings";

type View = "page" | "settings";

export default function App() {
  const { theme, sidebarOpen, setSidebarOpen } = useSettings();
  const { pages, activePageId, load, add, remove, setActive } = usePages();
  const [view, setView] = useState<View>("page");
  const [adding, setAdding] = useState(false);
  const [newName, setNewName] = useState("");

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  async function submitNewPage() {
    const name = newName.trim();
    setAdding(false);
    setNewName("");
    if (name) await add(name);
    setView("page");
  }

  return (
    <div className="flex h-full">
      <aside
        className={
          "flex shrink-0 flex-col overflow-hidden border-r border-line bg-surface/60 transition-all duration-300 ease-in-out " +
          (sidebarOpen ? "w-56 p-4" : "w-14 p-2")
        }
      >
        <div className={"mb-4 flex items-center gap-2 " + (sidebarOpen ? "px-2" : "flex-col gap-3")}>
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
              className={"transition-transform duration-300 " + (sidebarOpen ? "" : "rotate-180")}
            />
          </button>
        </div>

        {sidebarOpen && (
          <p className="mb-1 px-2 text-[11px] font-medium uppercase tracking-wide text-faint">
            Pages
          </p>
        )}
        <nav
          className={
            "min-h-0 flex-1 space-y-1 overflow-y-auto text-sm " +
            (sidebarOpen ? "" : "flex flex-col items-center")
          }
        >
          {pages.map((p) => (
            <div key={p.id} className={sidebarOpen ? "group relative" : ""}>
              <button
                onClick={() => {
                  setActive(p.id);
                  setView("page");
                }}
                title={sidebarOpen ? undefined : p.name}
                className={
                  "flex items-center gap-3 rounded-lg py-2 " +
                  (sidebarOpen ? "w-full px-3 pr-8 text-left " : "justify-center p-2 ") +
                  (view === "page" && activePageId === p.id
                    ? "bg-surface text-ink"
                    : "text-soft hover:bg-surface/70 hover:text-ink")
                }
              >
                <FileText size={16} className="shrink-0" />
                {sidebarOpen && <span className="truncate whitespace-nowrap">{p.name}</span>}
              </button>
              {sidebarOpen && pages.length > 1 && (
                <button
                  onClick={() => {
                    if (confirm(`Delete "${p.name}" and its blocks?`)) remove(p.id);
                  }}
                  className="absolute right-2 top-1/2 hidden -translate-y-1/2 rounded p-1 text-faint hover:text-red-500 group-hover:block"
                  title="Delete page"
                >
                  <Trash2 size={13} />
                </button>
              )}
            </div>
          ))}

          {sidebarOpen &&
            (adding ? (
              <input
                autoFocus
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") submitNewPage();
                  if (e.key === "Escape") {
                    setAdding(false);
                    setNewName("");
                  }
                }}
                onBlur={submitNewPage}
                placeholder="Page name…"
                className="w-full rounded-lg border border-line bg-bg px-3 py-2 text-sm outline-none focus:border-accent"
              />
            ) : (
              <button
                onClick={() => setAdding(true)}
                className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-faint hover:bg-surface/70 hover:text-ink"
              >
                <Plus size={16} /> New page
              </button>
            ))}
        </nav>

        <div className={sidebarOpen ? "mt-2 space-y-1 text-sm" : "mt-2 flex flex-col items-center"}>
          <button
            onClick={() => setView("settings")}
            title={sidebarOpen ? undefined : "Settings"}
            className={
              "flex items-center gap-3 rounded-lg py-2 " +
              (sidebarOpen ? "w-full px-3 text-left " : "justify-center p-2 ") +
              (view === "settings"
                ? "bg-surface text-ink"
                : "text-soft hover:bg-surface/70 hover:text-ink")
            }
          >
            <Settings size={16} />
            {sidebarOpen && "Settings"}
          </button>
        </div>

        {sidebarOpen && <GoogleConnectCard />}
      </aside>

      <main className="flex flex-1 flex-col overflow-hidden">
        {view === "page" ? <Dashboard /> : <SettingsPage />}
      </main>
    </div>
  );
}
