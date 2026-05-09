import { Suspense } from "react";
import { MainWorkspace } from "./main-workspace";

export default function MainPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen flex-1 items-center justify-center bg-slate-50 text-sm text-slate-500">
          Loading workspace…
        </div>
      }
    >
      <MainWorkspace />
    </Suspense>
  );
}
