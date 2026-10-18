// The workspace is the mode: A'Pelago (accelerator) or Redstone (VC). It swaps the accent tokens on
// <html> and the content rules (labels, tiers, which rows are listed).
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { Mode } from "../api";

const STORAGE_KEY = "bluewatch.workspace";

interface WorkspaceValue {
  mode: Mode;
  setMode: (mode: Mode) => void;
}

const WorkspaceContext = createContext<WorkspaceValue | null>(null);

function initialMode(): Mode {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "redstone" ? "redstone" : "apelago";
  } catch {
    return "apelago"; // storage can be blocked (private windows); the default is fine
  }
}

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<Mode>(initialMode);

  useEffect(() => {
    document.documentElement.dataset.workspace = mode;
  }, [mode]);

  const setMode = useCallback((next: Mode) => {
    setModeState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Remembering the workspace is a convenience only.
    }
  }, []);

  const value = useMemo(() => ({ mode, setMode }), [mode, setMode]);
  return <WorkspaceContext value={value}>{children}</WorkspaceContext>;
}

export function useWorkspace(): WorkspaceValue {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("useWorkspace needs a WorkspaceProvider");
  return value;
}
