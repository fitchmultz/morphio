import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type React from "react";
import { AuthProvider } from "@/contexts/AuthContext";
import { login as apiLogin } from "@/lib/auth";
import * as toast from "@/lib/toast";
import { LoginForm } from "../LoginForm";

// Mock window.matchMedia for next-themes
Object.defineProperty(window, "matchMedia", {
	writable: true,
	value: jest.fn().mockImplementation((query) => ({
		matches: false,
		media: query,
		onchange: null,
		addListener: jest.fn(), // Deprecated
		removeListener: jest.fn(), // Deprecated
		addEventListener: jest.fn(),
		removeEventListener: jest.fn(),
		dispatchEvent: jest.fn(),
	})),
});

// Mock localStorage
const localStorageMock = {
	getItem: jest.fn(),
	setItem: jest.fn(),
	removeItem: jest.fn(),
	clear: jest.fn(),
};
Object.defineProperty(window, "localStorage", {
	value: localStorageMock,
});

// Mock the useRouter hook
jest.mock("next/navigation", () => ({
	useRouter: () => ({
		push: jest.fn(),
		replace: jest.fn(),
		prefetch: jest.fn(),
	}),
}));

// Mock the auth module
jest.mock("@/lib/auth", () => ({
	login: jest.fn(),
}));

jest.mock("@/lib/toast", () => ({
	notifySuccess: jest.fn(),
	notifyError: jest.fn(),
}));

// Mock the logger to prevent console spam during tests
jest.mock("@/lib/logger", () => ({
	info: jest.fn(),
	error: jest.fn(),
	warn: jest.fn(),
	debug: jest.fn(),
	performance: jest.fn(),
}));

// Mock the useAuth hook
jest.mock("@/hooks/useAuth", () => ({
	useAuth: jest.fn().mockReturnValue({
		login: jest.fn(),
		isAuthenticated: false,
		loading: false,
	}),
}));

// Custom render with AuthProvider
const renderWithAuth = (ui: React.ReactElement) => {
	return render(<AuthProvider>{ui}</AuthProvider>);
};

describe("LoginForm", () => {
	beforeEach(() => {
		jest.clearAllMocks();
	});

	test("renders login form correctly", () => {
		renderWithAuth(<LoginForm />);

		// Check if form elements are present
		expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
		expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /login/i })).toBeInTheDocument();
	});

	test("validates form inputs", async () => {
		renderWithAuth(<LoginForm />);

		// Submit with empty fields
		const submitButton = screen.getByRole("button", { name: /login/i });
		fireEvent.click(submitButton);

		// Should show validation errors
		await waitFor(() => {
			expect(screen.getByText(/email is required/i)).toBeInTheDocument();
			expect(screen.getByText(/password is required/i)).toBeInTheDocument();
		});
	});

	test("validates email format", async () => {
		renderWithAuth(<LoginForm />);

		// Enter invalid email
		const emailInput = screen.getByLabelText(/email/i);
		fireEvent.change(emailInput, { target: { value: "invalid-email" } });

		// Enter some password
		const passwordInput = screen.getByLabelText(/password/i);
		fireEvent.change(passwordInput, { target: { value: "password123" } });

		// Submit form
		const submitButton = screen.getByRole("button", { name: /login/i });
		fireEvent.click(submitButton);

		// Should show email validation error
		await waitFor(() => {
			expect(screen.getByText(/invalid email format/i)).toBeInTheDocument();
		});
	});

	test("handles successful login", async () => {
		// Mock successful API response
		const mockUser = { id: "1", email: "test@example.com", name: "Test User" };
		(apiLogin as jest.Mock).mockResolvedValueOnce({
			access_token: "fake-token",
			user: mockUser,
		});

		renderWithAuth(<LoginForm />);

		// Fill in form
		const emailInput = screen.getByLabelText(/email/i);
		const passwordInput = screen.getByLabelText(/password/i);

		fireEvent.change(emailInput, { target: { value: "test@example.com" } });
		fireEvent.change(passwordInput, { target: { value: "password123" } });

		// Submit form
		const submitButton = screen.getByRole("button", { name: /login/i });
		fireEvent.click(submitButton);

		// Check if API was called with correct data
		await waitFor(() => {
			expect(apiLogin).toHaveBeenCalledWith("test@example.com", "password123");
			expect(toast.notifySuccess).toHaveBeenCalledWith("Login successful!");
		});
	});

	test("handles API error", async () => {
		// Mock API error
		(apiLogin as jest.Mock).mockRejectedValueOnce(
			new Error("Invalid credentials"),
		);

		renderWithAuth(<LoginForm />);

		// Fill in form
		const emailInput = screen.getByLabelText(/email/i);
		const passwordInput = screen.getByLabelText(/password/i);

		fireEvent.change(emailInput, { target: { value: "test@example.com" } });
		fireEvent.change(passwordInput, { target: { value: "wrong-password" } });

		// Submit form
		const submitButton = screen.getByRole("button", { name: /login/i });
		fireEvent.click(submitButton);

		// Check if error notification was shown
		await waitFor(() => {
			expect(toast.notifyError).toHaveBeenCalled();
		});
	});

	test("handles network error", async () => {
		// Mock network error
		(apiLogin as jest.Mock).mockRejectedValueOnce(new Error("Failed to fetch"));

		renderWithAuth(<LoginForm />);

		// Fill in form
		const emailInput = screen.getByLabelText(/email/i);
		const passwordInput = screen.getByLabelText(/password/i);

		fireEvent.change(emailInput, { target: { value: "test@example.com" } });
		fireEvent.change(passwordInput, { target: { value: "password123" } });

		// Submit form
		const submitButton = screen.getByRole("button", { name: /login/i });
		fireEvent.click(submitButton);

		// Check if correct error message was shown
		await waitFor(() => {
			expect(toast.notifyError).toHaveBeenCalledWith(
				"Network error. Please check your connection and try again.",
			);
		});
	});
});
