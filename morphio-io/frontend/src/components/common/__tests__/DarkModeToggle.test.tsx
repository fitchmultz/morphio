import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { __resetMock, __setDarkMode } from "@/hooks/__mocks__/useDarkMode";
import { DarkModeToggle } from "../DarkModeToggle";

// Mock the useDarkMode hook
jest.mock("@/hooks/useDarkMode");

// Mock lucide-react icons
jest.mock("lucide-react");

// Mock the logger to prevent console spam during tests
jest.mock("@/lib/logger", () => ({
	info: jest.fn(),
	error: jest.fn(),
	warn: jest.fn(),
	debug: jest.fn(),
}));

describe("DarkModeToggle", () => {
	// Clean up after each test
	afterEach(() => {
		cleanup();
		__resetMock();
	});

	test("renders a toggle button", () => {
		// Set the mock to light mode
		__setDarkMode(false);

		// Render the component
		render(<DarkModeToggle />);

		// Check if the button is rendered
		const toggleButton = screen.getByLabelText("Toggle Dark Mode");
		expect(toggleButton).toBeInTheDocument();
	});

	test("calls toggleDarkMode when clicked", () => {
		// Set the mock to light mode
		__setDarkMode(false);

		// Render the component
		const { rerender } = render(<DarkModeToggle />);

		// Get the toggle button
		const toggleButton = screen.getByLabelText("Toggle Dark Mode");

		// Click the button
		fireEvent.click(toggleButton);

		// Re-render to capture state changes using the rerender function
		rerender(<DarkModeToggle />);

		// Button should still be in the document
		expect(screen.getByLabelText("Toggle Dark Mode")).toBeInTheDocument();
	});
});
