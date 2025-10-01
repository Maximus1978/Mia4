import '@testing-library/jest-dom';

// Older @vitejs/plugin-react expects its dev preamble flag to be present.
// Vitest does not execute the browser preamble, so stub it here to avoid runtime errors.
if (!(globalThis as any).__vite_plugin_react_preamble_installed__) {
	(globalThis as any).__vite_plugin_react_preamble_installed__ = true;
}

