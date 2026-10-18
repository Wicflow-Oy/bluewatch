import { Suspense, use } from "react";
import { load } from "./data";
import { useLang } from "./i18n/lang";
import type { Mode } from "./api";
import { getPreset } from "./lib/preset";
import { isStandalone, useRoute, type Route } from "./lib/router";
import { useWorkspace, WorkspaceProvider } from "./lib/workspace";
import { preloadRoute, StandalonePage } from "./screens/pages";
import { AppShell } from "./shell/AppShell";
import { BootScreen } from "./shell/BootScreen";
import { Shockwave } from "./shell/Shockwave";
import { ToastProvider } from "./ui/Toast";

// The boot screen shows at least this long, so a fast answer does not flash it. It only holds the
// shell: the landing page's chunk and data load alongside /api/meta.
const MIN_BOOT_MS = 150;
let boot: Promise<unknown> | null = null;

function bootOnce(route: Route, mode: Mode) {
  if (!boot) {
    preloadRoute(route, mode, getPreset());
    boot = Promise.all([load.meta(), new Promise((resolve) => setTimeout(resolve, MIN_BOOT_MS))]);
  }
  return boot;
}

function Booted({ route }: { route: Route }) {
  const { mode } = useWorkspace();
  use(bootOnce(route, mode));
  return <AppShell />;
}

export function App() {
  const route = useRoute();
  // Subscribing here re-renders the whole tree in the new language without remounting it, so open
  // drawers and half-filled forms survive a switch.
  useLang();
  // The student form (what an invitation opens) and the guide: no workspace, no shell, no boot wait.
  if (isStandalone(route)) {
    return (
      <ToastProvider>
        <Shockwave />
        <StandalonePage route={route} />
      </ToastProvider>
    );
  }
  return (
    <WorkspaceProvider>
      <ToastProvider>
        <Shockwave />
        <Suspense fallback={<BootScreen />}>
          <Booted route={route} />
        </Suspense>
      </ToastProvider>
    </WorkspaceProvider>
  );
}
