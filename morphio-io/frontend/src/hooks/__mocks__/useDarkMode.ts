// Mock implementation of the useDarkMode hook
const mockToggleDarkMode = jest.fn();
let mockIsDarkMode = false;

export const useDarkMode = () => {
	const toggleDarkMode = () => {
		mockIsDarkMode = !mockIsDarkMode;
		mockToggleDarkMode();
	};

	return {
		isDarkMode: mockIsDarkMode,
		toggleDarkMode,
	};
};

// Helper functions for tests to control the mock
export const __setDarkMode = (value: boolean) => {
	mockIsDarkMode = value;
};

export const __resetMock = () => {
	mockIsDarkMode = false;
	mockToggleDarkMode.mockClear();
};
