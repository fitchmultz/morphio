/* eslint-env jest */
// Import React Testing Library and Jest DOM extensions
import "@testing-library/jest-dom";

// Mock Next.js router
jest.mock("next/navigation", () => ({
	useRouter: () => ({
		push: jest.fn(),
		replace: jest.fn(),
		prefetch: jest.fn(),
		back: jest.fn(),
		forward: jest.fn(),
		refresh: jest.fn(),
	}),
	usePathname: () => "",
	useSearchParams: () => ({ get: () => null }),
}));

// Mock localStorage
const localStorageMock = (() => {
	let store = {};
	return {
		getItem: jest.fn((key) => store[key] || null),
		setItem: jest.fn((key, value) => {
			store[key] = value.toString();
		}),
		removeItem: jest.fn((key) => {
			delete store[key];
		}),
		clear: jest.fn(() => {
			store = {};
		}),
	};
})();

Object.defineProperty(window, "localStorage", {
	value: localStorageMock,
});

// Suppress console errors during tests
const originalConsoleError = console.error;
console.error = (...args) => {
	if (
		/Warning: ReactDOM.render is no longer supported in React 18./.test(
			args[0],
		) ||
		/Warning: useLayoutEffect does nothing on the server/.test(args[0])
	) {
		return;
	}
	originalConsoleError(...args);
};
