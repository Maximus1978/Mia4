import { useContext } from 'react';
import { ThemeContext } from '../context/ThemeContext';

const useAccentColor = () => {
    const { accentColor } = useContext(ThemeContext);

    const applyAccentColor = (element) => {
        if (element) {
            element.style.color = accentColor;
        }
    };

    return { accentColor, applyAccentColor };
};

export default useAccentColor;