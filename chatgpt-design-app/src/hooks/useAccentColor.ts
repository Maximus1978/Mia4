import { useContext } from 'react';
import { ThemeContext } from '../context/ThemeContext';

const useAccentColor = () => {
    const ctx = useContext(ThemeContext);
    const accentColor = (ctx as any)?.accentColor ?? (ctx as any)?.theme ?? 'inherit';

    const applyAccentColor = (element: HTMLElement | null) => {
        if (element) {
            element.style.color = accentColor;
        }
    };

    return { accentColor, applyAccentColor };
};

export default useAccentColor;