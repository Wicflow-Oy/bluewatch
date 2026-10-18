// Light / Graphite: a two-segment pill in the top bar and the standalone headers, labelled in the More sheet.
import { Moon, Sun } from "lucide-react";
import { useT } from "../i18n/messages";
import { setTheme, useTheme, type Theme } from "../lib/theme";
import { Segmented } from "../ui/Segmented";
import { shellMessages } from "./messages";

export function ThemeToggle({ variant = "icons" }: { variant?: "icons" | "labels" }) {
  const { t } = useT(shellMessages);
  const theme = useTheme();
  const icons = variant === "icons";
  const options = (["light", "graphite"] as const).map((value) => {
    const word = t(value === "light" ? "themeLight" : "themeGraphite");
    return {
      value,
      icon: value === "light" ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />,
      label: icons ? undefined : word,
      ariaLabel: icons ? word : undefined,
      title: icons ? word : undefined,
    };
  });
  return (
    <Segmented<Theme>
      className="theme-toggle"
      options={options}
      value={theme}
      onChange={setTheme}
      label={t("theme")}
      size={icons ? "sm" : "md"}
      block={!icons}
    />
  );
}
