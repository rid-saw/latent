import { Github } from "lucide-react";

const REPO = "https://github.com/rid-saw/latent";

/** Header plaque for the public demo: says the content is sample data, and
 *  links back to the repo. Only rendered on the deployed demo build. */
export function DemoBadge() {
  if (!import.meta.env.VITE_DEMO) return null;

  return (
    <a
      href={REPO}
      target="_blank"
      rel="noreferrer"
      title="Sample content. View the source on GitHub"
      className="flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full border border-line px-2.5 py-1 text-xs text-soft hover:border-faint hover:text-ink"
    >
      <Github size={13} />
      Demo
    </a>
  );
}
