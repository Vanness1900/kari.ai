"use client";

import dynamic from "next/dynamic";

const MainScreen = dynamic(
  () =>
    import("@/components/main-screen").then((mod) => ({
      default: mod.MainScreen,
    })),
  {
    ssr: false,
    loading: () => (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 text-sm text-slate-500">
        Loading workspace…
      </div>
    ),
  },
);

export function MainWorkspace() {
  return <MainScreen />;
}
