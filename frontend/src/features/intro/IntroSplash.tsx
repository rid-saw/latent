import { useEffect, useState } from "react";

/** First-run splash: the word "latent" slides out of the l logo, then fades. */
export function IntroSplash({ onDone }: { onDone: () => void }) {
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    const t1 = setTimeout(() => setLeaving(true), 2600);
    const t2 = setTimeout(onDone, 3150);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [onDone]);

  return (
    <div
      onClick={onDone}
      className={
        "fixed inset-0 z-50 flex cursor-pointer flex-col items-center justify-center bg-bg transition-opacity duration-500 " +
        (leaving ? "opacity-0" : "opacity-100")
      }
    >
      <div className="flex items-center">
        <div className="intro-logo z-10 flex h-16 w-16 items-center justify-center rounded-2xl bg-ink text-4xl font-bold text-bg">
          l
        </div>
        <div className="ml-2 flex overflow-hidden text-5xl font-bold tracking-tight">
          {"atent".split("").map((ch, i) => (
            <span
              key={i}
              className="intro-letter"
              style={{ animationDelay: `${420 + i * 90}ms` }}
            >
              {ch}
            </span>
          ))}
        </div>
      </div>
      <p className="intro-tag mt-5 text-sm text-faint">
        everything you follow, in one view
      </p>
    </div>
  );
}
