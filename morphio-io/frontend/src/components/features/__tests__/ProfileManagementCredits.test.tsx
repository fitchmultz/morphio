import { render, screen, waitFor } from "@testing-library/react";
import * as sdk from "@/client/sdk.gen";
import { ProfileManagement } from "../ProfileManagement";

const mockUpdateUserData = jest.fn();

jest.mock("@/client/sdk.gen", () => ({
	createApiKey: jest.fn(),
	getUserCredits: jest.fn(),
	getUserProfile: jest.fn(),
	listApiKeys: jest.fn(),
	revokeApiKey: jest.fn(),
}));

jest.mock("@/contexts/AuthContext", () => ({
	useAuth: () => ({
		updateUserData: mockUpdateUserData,
	}),
}));

jest.mock("@/lib/logger", () => ({
	info: jest.fn(),
	warn: jest.fn(),
	error: jest.fn(),
	debug: jest.fn(),
}));

jest.mock("@/lib/toast", () => ({
	notifySuccess: jest.fn(),
	notifyError: jest.fn(),
}));

const mockUserProfile = {
	id: 1,
	email: "user@example.com",
	display_name: "Test User",
	role: "user",
};

describe("ProfileManagement Credits", () => {
	beforeEach(() => {
		jest.clearAllMocks();
		(sdk.getUserProfile as jest.Mock).mockResolvedValue({
			data: { status: "success", data: mockUserProfile },
		});
		(sdk.listApiKeys as jest.Mock).mockResolvedValue({
			data: { status: "success", data: [] },
		});
	});

	test("renders Usage Credits section when credits data is available", async () => {
		(sdk.getUserCredits as jest.Mock).mockResolvedValue({
			data: {
				status: "success",
				data: {
					tier: "free",
					limit: 50,
					used: 10,
					remaining: 40,
					remaining_pct: 80.0,
					reset_date: "2025-02-01",
					resets_monthly: true,
					is_admin: false,
				},
			},
		});

		render(<ProfileManagement />);

		await waitFor(() => {
			expect(screen.getByText("Usage Credits")).toBeInTheDocument();
		});
	});

	test("renders plan and usage text correctly", async () => {
		(sdk.getUserCredits as jest.Mock).mockResolvedValue({
			data: {
				status: "success",
				data: {
					tier: "free",
					limit: 50,
					used: 10,
					remaining: 40,
					remaining_pct: 80.0,
					reset_date: "2025-02-01",
					resets_monthly: true,
					is_admin: false,
				},
			},
		});

		render(<ProfileManagement />);

		await waitFor(() => {
			expect(screen.getByText("Tier:")).toBeInTheDocument();
			expect(screen.getByText("free")).toBeInTheDocument();
			expect(screen.getByText("10 / 50")).toBeInTheDocument();
		});
	});

	test("renders critical banner when remaining_pct < 5", async () => {
		(sdk.getUserCredits as jest.Mock).mockResolvedValue({
			data: {
				status: "success",
				data: {
					tier: "free",
					limit: 50,
					used: 48,
					remaining: 2,
					remaining_pct: 4.0,
					reset_date: "2025-02-01",
					resets_monthly: true,
					is_admin: false,
				},
			},
		});

		render(<ProfileManagement />);

		await waitFor(() => {
			expect(
				screen.getByText("Critical: Less than 5% of credits remaining!"),
			).toBeInTheDocument();
		});
	});

	test("renders monthly quota guidance when plan is free", async () => {
		(sdk.getUserCredits as jest.Mock).mockResolvedValue({
			data: {
				status: "success",
				data: {
					tier: "free",
					limit: 50,
					used: 10,
					remaining: 40,
					remaining_pct: 80.0,
					reset_date: "2025-02-01",
					resets_monthly: true,
					is_admin: false,
				},
			},
		});

		render(<ProfileManagement />);

		await waitFor(() => {
			expect(
				screen.getByText(/fixed monthly quota tiers for demo stability/i),
			).toBeInTheDocument();
		});
	});

	test("does not render critical banner when remaining_pct >= 5", async () => {
		(sdk.getUserCredits as jest.Mock).mockResolvedValue({
			data: {
				status: "success",
				data: {
					tier: "free",
					limit: 50,
					used: 10,
					remaining: 40,
					remaining_pct: 80.0,
					reset_date: "2025-02-01",
					resets_monthly: true,
					is_admin: false,
				},
			},
		});

		render(<ProfileManagement />);

		await waitFor(() => {
			expect(screen.getByText("Usage Credits")).toBeInTheDocument();
		});

		expect(
			screen.queryByText("Critical: Less than 5% of credits remaining!"),
		).not.toBeInTheDocument();
	});

	test("does not render billing actions for paid plans", async () => {
		(sdk.getUserCredits as jest.Mock).mockResolvedValue({
			data: {
				status: "success",
				data: {
					tier: "pro",
					limit: 1000,
					used: 100,
					remaining: 900,
					remaining_pct: 90.0,
					reset_date: "2025-02-01",
					resets_monthly: true,
					is_admin: false,
				},
			},
		});

		render(<ProfileManagement />);

		await waitFor(() => {
			expect(screen.getByText("pro")).toBeInTheDocument();
		});

		expect(
			screen.queryByRole("button", { name: /manage billing/i }),
		).not.toBeInTheDocument();
		expect(
			screen.queryByRole("button", { name: /upgrade to pro/i }),
		).not.toBeInTheDocument();
	});
});
