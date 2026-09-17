/**
 * Light/dark theme hook.
 *
 * WHAT IT DOES: reads the saved preference from localStorage (default: light),
 * applies/removes the `dark` class on <html>, and exposes a toggle.
 * Storage access happens inside effects so server rendering stays consistent.
 */
import { useCallback, useEffect, useState } from "react";
const STORAGE_KEY = "fedretina-theme";
export function useTheme() {
    const [theme, setTheme] = useState("light");
    // On mount, restore the stored preference (browser-only).
    useEffect(() => {
        const stored = window.localStorage.getItem(STORAGE_KEY);
        if (stored === "dark" || stored === "light")
            setTheme(stored);
    }, []);
    // Keep <html class="dark"> and localStorage in sync with state.
    useEffect(() => {
        document.documentElement.classList.toggle("dark", theme === "dark");
        window.localStorage.setItem(STORAGE_KEY, theme);
    }, [theme]);
    const toggleTheme = useCallback(() => {
        setTheme((current) => (current === "dark" ? "light" : "dark"));
    }, []);
    return { theme, setTheme, toggleTheme };
}
