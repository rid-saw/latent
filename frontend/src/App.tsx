import { useEffect, useState } from "react";
import { ChevronLeft, Plus, Settings, Trash2 } from "lucide-react";
import type { Page } from "@/types";
import { PAGE_ICONS, PageIcon } from "@/lib/pageIcons";
import { Dashboard } from "@/features/dashboard/Dashboard";
import { IntroSplash } from "@/features/intro/IntroSplash";
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
  const [newEmoji, setNewEmoji] = useState("file-text");
  const [pendingDelete, setPendingDelete] = useState<Page | null>(null);
  // First run (or after a reset): nothing in localStorage yet -> play the intro.
  const [showIntro, setShowIntro] = useState(
    () => !localStorage.getItem("latent-intro-seen"),
  );

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  async function submitNewPage() {
    const name = newName.trim();
    if (!name) return;
    setAdding(false);
    setNewName("");
    if (name) await add(name, newEmoji);
    setNewEmoji("file-text");
    setView("page");
  }

  if (showIntro) {
    return (
      <IntroSplash
        onDone={() => {
          localStorage.setItem("latent-intro-seen", "1");
          setShowIntro(false);
        }}
      />
    );
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
          {sidebarOpen && (
            <span className="whitespace-nowrap text-lg font-bold tracking-tight">latent</span>
          )}
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
                <PageIcon icon={p.emoji} size={16} />
                {sidebarOpen && <span className="truncate whitespace-nowrap">{p.name}</span>}
              </button>
              {sidebarOpen && pages.length > 1 && (
                <button
                  onClick={() => setPendingDelete(p)}
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
              <div className="rounded-lg border border-line bg-bg p-2">
                <div className="flex items-center gap-2">
                  <PageIcon icon={newEmoji} size={16} />
                  <input
                    autoFocus
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") submitNewPage();
                      if (e.key === "Escape") {
                        setAdding(false);
                        setNewName("");
                        setNewEmoji("file-text");
                      }
                    }}
                    placeholder="Page name…"
                    className="w-full bg-transparent text-sm outline-none"
                  />
                </div>
                <div className="mt-2 grid grid-cols-8 gap-0.5">
                  {Object.entries(PAGE_ICONS).map(([name, Icon]) => (
                    <button
                      key={name}
                      onMouseDown={(ev) => ev.preventDefault()} // keep input focus
                      onClick={() => setNewEmoji(name)}
                      title={name}
                      className={
                        "flex items-center justify-center rounded p-1 text-soft hover:bg-surface hover:text-ink " +
                        (newEmoji === name ? "bg-surface text-ink ring-1 ring-accent" : "")
                      }
                    >
                      <Icon size={14} />
                    </button>
                  ))}
                </div>
                <p className="mt-1.5 text-[10px] text-faint">Enter to create · Esc to cancel</p>
              </div>
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

      {pendingDelete && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          onClick={() => setPendingDelete(null)}
        >
          <div
            className="w-full max-w-sm rounded-2xl border border-line bg-card p-5"
            onClick={(e) => e.stopPropagation()}
          >
            <p className="flex items-center gap-1.5 text-sm font-medium">
              Delete "<PageIcon icon={pendingDelete.emoji} size={14} /> {pendingDelete.name}"?
            </p>
            <p className="mt-1 text-xs text-faint">
              This deletes the page and all of its blocks. It can't be undone.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={() => setPendingDelete(null)}
                className="rounded-lg border border-line px-3 py-1.5 text-xs text-soft hover:text-ink"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  remove(pendingDelete.id);
                  setPendingDelete(null);
                }}
                className="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700"
              >
                Delete page
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
