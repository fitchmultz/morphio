import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import * as sdk from "@/client/sdk.gen";
import * as toast from "@/lib/toast";
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

describe("ProfileManagement API keys", () => {
	beforeEach(() => {
		jest.clearAllMocks();
		(sdk.getUserProfile as jest.Mock).mockResolvedValue({
			data: { status: "success", data: mockUserProfile },
		});
		(sdk.getUserCredits as jest.Mock).mockResolvedValue({
			data: { status: "success", data: null },
		});
	});

	test("creates an API key and surfaces the plaintext key", async () => {
		(sdk.listApiKeys as jest.Mock).mockResolvedValue({
			data: { status: "success", data: [] },
		});
		(sdk.createApiKey as jest.Mock).mockResolvedValue({
			data: {
				status: "success",
				data: {
					id: 42,
					name: "CLI",
					key_prefix: "mk_123",
					scopes: [],
					last_used_at: null,
					created_at: "2025-01-01T00:00:00Z",
					key: "mk_live_plaintext",
				},
			},
		});

		render(<ProfileManagement />);

		await screen.findByText("Current Profile Information");

		fireEvent.change(screen.getByPlaceholderText(/key name/i), {
			target: { value: "CLI" },
		});
		fireEvent.click(screen.getByRole("button", { name: /create key/i }));

		await waitFor(() => {
			expect(sdk.createApiKey).toHaveBeenCalledWith({
				body: { name: "CLI" },
			});
			expect(screen.getByText(/save this key now/i)).toBeInTheDocument();
			expect(screen.getByText("mk_live_plaintext")).toBeInTheDocument();
			expect(toast.notifySuccess).toHaveBeenCalled();
		});
	});

	test("revokes an API key from the list", async () => {
		const confirmSpy = jest.spyOn(window, "confirm").mockReturnValue(true);

		(sdk.listApiKeys as jest.Mock)
			.mockResolvedValueOnce({
				data: {
					status: "success",
					data: [
						{
							id: 7,
							name: "Automation",
							key_prefix: "mk_777",
							scopes: [],
							last_used_at: null,
							created_at: "2025-01-02T00:00:00Z",
						},
					],
				},
			})
			.mockResolvedValueOnce({
				data: { status: "success", data: [] },
			});
		(sdk.revokeApiKey as jest.Mock).mockResolvedValue({
			data: { status: "success", data: { id: 7 } },
		});

		render(<ProfileManagement />);

		await screen.findByText("Current Profile Information");
		await screen.findByText("Automation");

		fireEvent.click(screen.getByRole("button", { name: /revoke/i }));

		await waitFor(() => {
			expect(sdk.revokeApiKey).toHaveBeenCalledWith({
				path: { key_id: 7 },
			});
			expect(toast.notifySuccess).toHaveBeenCalled();
		});

		confirmSpy.mockRestore();
	});
});
