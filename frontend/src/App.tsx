import { Layers, Link2, Settings } from "lucide-react";
import { Dashboard } from "@/features/dashboard/Dashboard";

export default function App() {
  return (
    <div className="flex h-full">
      <aside className="flex w-56 flex-col border-r border-neutral-800 bg-neutral-900/50 p-4">
        <div className="mb-6 flex items-center gap-2 px-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-neutral-100 text-sm font-bold text-neutral-900">
            l
          </div>
          <span className="font-semibold">latent</span>
        </div>

        <nav className="space-y-1 text-sm">
          <NavItem icon={<Layers size={16} />} label="Dashboard" active />
          <NavItem icon={<Link2 size={16} />} label="Sources" />
          <NavItem icon={<Settings size={16} />} label="Settings" />
        </nav>

        <div className="mt-auto rounded-lg border border-neutral-800 p-3 text-xs text-neutral-500">
          Connect YouTube + Gmail to pull real content.
        </div>
      </aside>

      <main className="flex flex-1 flex-col">
        <Dashboard />
      </main>
    </div>
  );
}

function NavItem({
  icon,
  label,
  active,
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
}) {
  return (
    <button
      className={
        "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left " +
        (active
          ? "bg-neutral-800 text-neutral-100"
          : "text-neutral-400 hover:bg-neutral-800/50 hover:text-neutral-200")
      }
    >
      {icon}
      {label}
    </button>
  );
}
