"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/personas", label: "Personas" },
  { href: "/generate", label: "Generate" },
  { href: "/review", label: "Review queue" },
  { href: "/products", label: "Products" },
];

export function Nav() {
  const path = usePathname();
  return (
    <nav className="w-56 shrink-0 border-r border-surface-800 bg-surface-900 px-4 py-6">
      <div className="px-2 pb-6 text-sm font-semibold tracking-tight text-neutral-100">
        Creator Studio
        <span className="ml-2 rounded bg-surface-800 px-1.5 py-0.5 text-[10px] font-medium text-ok">
          SFW
        </span>
      </div>
      <ul className="space-y-1">
        {LINKS.map((l) => {
          const active = path === l.href;
          return (
            <li key={l.href}>
              <Link
                href={l.href}
                aria-current={active ? "page" : undefined}
                className={`block rounded-md px-3 py-2 text-sm transition-colors ${
                  active
                    ? "bg-accent text-white"
                    : "text-neutral-400 hover:bg-surface-800 hover:text-neutral-100"
                }`}
              >
                {l.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
