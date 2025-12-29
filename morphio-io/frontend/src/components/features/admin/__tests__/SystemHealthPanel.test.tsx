import { render, screen, waitFor } from "@testing-library/react";
import { getAdminHealth } from "@/client";
import { SystemHealthPanel } from "../SystemHealthPanel";

jest.mock("@/client", () => ({
	getAdminHealth: jest.fn(),
}));

jest.mock("@/lib/logger", () => ({
	info: jest.fn(),
	warn: jest.fn(),
	error: jest.fn(),
	debug: jest.fn(),
}));

const mockHealthResponse = {
	status: "success",
	data: {
		overall_status: "degraded",
		components: {
			database: { status: "ok", latency_ms: 12 },
			redis: { status: "error", detail: "Redis unavailable" },
			worker_ml: { status: "skipped", detail: "Not configured" },
			crawler: { status: "skipped", detail: "Not configured" },
		},
	},
};

describe("SystemHealthPanel", () => {
	beforeEach(() => {
		jest.clearAllMocks();
		(getAdminHealth as jest.Mock).mockResolvedValue({
			data: mockHealthResponse,
		});
	});

	it("renders component rows and status badges from the API response", async () => {
		render(<SystemHealthPanel />);

		await waitFor(() => {
			expect(getAdminHealth).toHaveBeenCalled();
		});

		expect(await screen.findByText("Database")).toBeInTheDocument();
		expect(screen.getByText("Redis")).toBeInTheDocument();
		expect(screen.getByText("Worker ML")).toBeInTheDocument();
		expect(screen.getByText("Crawler")).toBeInTheDocument();

		expect(screen.getByText("OK")).toBeInTheDocument();
		expect(screen.getByText("Error")).toBeInTheDocument();
		expect(screen.getAllByText("Skipped")).toHaveLength(2);
		expect(screen.getByText("Redis unavailable")).toBeInTheDocument();
	});
});
