import {
	act,
	fireEvent,
	render,
	screen,
	waitFor,
} from "@testing-library/react";
import "@testing-library/jest-dom";
import type {
	ConversationMessageOut,
	ConversationResponse,
	ConversationSummary,
} from "@/client/types.gen";

// Mock ContentDisplay first to avoid import issues
jest.mock("../ContentDisplay", () => {
	return function ContentDisplay({
		content,
		title,
	}: {
		content: string;
		title?: string;
	}) {
		return (
			<div>
				{title && <h2>{title}</h2>}
				<div>{content}</div>
			</div>
		);
	};
});

// Mock remark-gfm
jest.mock("remark-gfm", () => ({}));

// Mock dynamic import
jest.mock("next/dynamic", () => () => {
	return function ReactMarkdown({ children }: { children: string }) {
		return <div>{children}</div>;
	};
});

// Mock the SDK functions
jest.mock("@/client/sdk.gen", () => ({
	listContentConversations: jest.fn(),
	getConversationThread: jest.fn(),
	continueConversation: jest.fn(),
	deleteConversation: jest.fn(),
}));

import {
	continueConversation,
	getConversationThread,
	listContentConversations,
} from "@/client/sdk.gen";

const mockListConversations = listContentConversations as jest.Mock;
const mockGetThread = getConversationThread as jest.Mock;
const mockContinueConversation = continueConversation as jest.Mock;

// Import component after mocks
import ContentWithChat from "../ContentWithChat";

describe("ContentWithChat", () => {
	const mockContentId = 1;
	const mockContent = "This is test content";
	const mockTitle = "Test Content";

	const mockConversationSummary: ConversationSummary = {
		id: "conv-1",
		content_id: mockContentId,
		template_id: null,
		template_used: null,
		model: "gpt-5.1",
		parent_id: null,
		created_at: new Date().toISOString(),
		updated_at: new Date().toISOString(),
		message_count: 2,
	};

	const mockMessages: ConversationMessageOut[] = [
		{
			id: 1,
			role: "user",
			content: "Test user message",
			created_at: new Date().toISOString(),
		},
		{
			id: 2,
			role: "assistant",
			content: "Test assistant response",
			created_at: new Date().toISOString(),
		},
	];

	beforeEach(() => {
		jest.clearAllMocks();
		mockListConversations.mockResolvedValue({
			data: {
				status: "success",
				message: "",
				data: [],
			},
		});
		mockGetThread.mockResolvedValue({
			data: {
				status: "success",
				message: "",
				data: {
					...mockConversationSummary,
					messages: mockMessages,
				},
			},
		});
	});

	// Helper to render and wait for initial load to complete
	async function renderAndWaitForLoad(
		props: Partial<Parameters<typeof ContentWithChat>[0]> = {},
	) {
		const defaultProps = {
			content: mockContent,
			contentId: mockContentId,
			title: mockTitle,
		};
		let result: ReturnType<typeof render> | undefined;
		await act(async () => {
			result = render(<ContentWithChat {...defaultProps} {...props} />);
		});
		// Wait for any pending state updates to flush
		await act(async () => {
			await new Promise((resolve) => setTimeout(resolve, 0));
		});
		if (!result) {
			throw new Error("Render failed");
		}
		return result;
	}

	it("renders content correctly", async () => {
		await renderAndWaitForLoad();

		expect(screen.getByText(mockTitle)).toBeInTheDocument();
		expect(screen.getByText(mockContent)).toBeInTheDocument();
	});

	it("shows message when contentId is not provided", async () => {
		await renderAndWaitForLoad({ contentId: null });

		// The message is split across two elements
		expect(
			screen.getByText("Save this content to start iterating"),
		).toBeInTheDocument();
		expect(
			screen.getByText("with the conversation assistant"),
		).toBeInTheDocument();
	});

	it("loads conversation summaries on mount", async () => {
		mockListConversations.mockResolvedValue({
			data: {
				status: "success",
				message: "",
				data: [mockConversationSummary],
			},
		});

		await renderAndWaitForLoad();

		await waitFor(() => {
			expect(mockListConversations).toHaveBeenCalledWith({
				path: { content_id: mockContentId },
			});
		});
	});

	it("handles sending a message successfully", async () => {
		const mockResponse: ConversationResponse = {
			conversation_id: "conv-1",
			content_id: mockContentId,
			updated_content: "Updated content",
			model_used: "gpt-5.1",
			change_summary: ["Changed something"],
			notes: null,
			suggestions: ["Make it shorter"],
			messages: [
				...mockMessages,
				{
					id: 3,
					role: "user",
					content: "Test new message",
					created_at: new Date().toISOString(),
				},
				{
					id: 4,
					role: "assistant",
					content: "Test new response",
					created_at: new Date().toISOString(),
				},
			],
			created_new_conversation: false,
		};

		mockContinueConversation.mockResolvedValue({
			data: {
				status: "success",
				message: "",
				data: mockResponse,
			},
		});

		mockListConversations.mockResolvedValue({
			data: {
				status: "success",
				message: "",
				data: [mockConversationSummary],
			},
		});

		await renderAndWaitForLoad();

		// Wait for initial load
		await waitFor(() => {
			expect(mockListConversations).toHaveBeenCalled();
		});

		const input = screen.getByPlaceholderText("Describe what should change...");
		const sendButton = screen.getByRole("button", { name: /send/i });

		await act(async () => {
			fireEvent.change(input, { target: { value: "Test new message" } });
			fireEvent.click(sendButton);
		});

		await waitFor(() => {
			expect(mockContinueConversation).toHaveBeenCalledWith(
				expect.objectContaining({
					path: { content_id: mockContentId },
					body: expect.objectContaining({
						message: "Test new message",
						preserve_context: true,
					}),
				}),
			);
		});
	});

	it("prevents sending duplicate messages when busy", async () => {
		mockListConversations.mockResolvedValue({
			data: {
				status: "success",
				message: "",
				data: [mockConversationSummary],
			},
		});

		// Mock a slow API response
		mockContinueConversation.mockImplementation(
			() =>
				new Promise((resolve) => {
					setTimeout(() => {
						resolve({
							data: {
								status: "success",
								message: "",
								data: {
									conversation_id: "conv-1",
									content_id: mockContentId,
									updated_content: "Updated",
									model_used: "gpt-5.1",
									change_summary: [],
									notes: null,
									suggestions: [],
									messages: mockMessages,
									created_new_conversation: false,
								},
							},
						});
					}, 100);
				}),
		);

		await renderAndWaitForLoad();

		await waitFor(() => {
			expect(mockListConversations).toHaveBeenCalled();
		});

		const input = screen.getByPlaceholderText("Describe what should change...");
		const sendButton = screen.getByRole("button", { name: /send/i });

		await act(async () => {
			fireEvent.change(input, { target: { value: "Test message" } });
			fireEvent.click(sendButton);
			// Try to click again immediately
			fireEvent.click(sendButton);
		});

		// Should only be called once
		await waitFor(() => {
			expect(mockContinueConversation).toHaveBeenCalledTimes(1);
		});
	});

	it("validates message length", async () => {
		await renderAndWaitForLoad();

		const input = screen.getByPlaceholderText(
			"Describe what should change...",
		) as HTMLTextAreaElement;
		const longMessage = "x".repeat(5001);

		await act(async () => {
			fireEvent.change(input, { target: { value: longMessage } });
		});

		// Should not allow more than 5000 characters
		expect(input.value.length).toBeLessThanOrEqual(5000);
	});

	it("shows character count warning near limit", async () => {
		await renderAndWaitForLoad();

		const input = screen.getByPlaceholderText(
			"Describe what should change...",
		) as HTMLTextAreaElement;
		const nearLimitMessage = "x".repeat(4501);

		await act(async () => {
			fireEvent.change(input, { target: { value: nearLimitMessage } });
		});

		await waitFor(() => {
			expect(screen.getByText(/characters remaining/i)).toBeInTheDocument();
		});
	});

	it("handles conversation not found error gracefully", async () => {
		mockListConversations.mockResolvedValue({
			data: {
				status: "success",
				message: "",
				data: [mockConversationSummary],
			},
		});

		mockContinueConversation.mockResolvedValue({
			data: {
				status: "error",
				message: "Conversation not found",
				data: undefined,
			},
		});

		await renderAndWaitForLoad();

		await waitFor(() => {
			expect(mockListConversations).toHaveBeenCalled();
		});

		const input = screen.getByPlaceholderText("Describe what should change...");
		const sendButton = screen.getByRole("button", { name: /send/i });

		await act(async () => {
			fireEvent.change(input, { target: { value: "Test message" } });
			fireEvent.click(sendButton);
		});

		await waitFor(() => {
			expect(
				screen.getByText(/conversation was not found/i),
			).toBeInTheDocument();
		});
	});

	it("handles API errors gracefully", async () => {
		mockListConversations.mockRejectedValue(new Error("Network error"));

		await renderAndWaitForLoad();

		await waitFor(() => {
			expect(screen.getByText(/network error/i)).toBeInTheDocument();
		});
	});

	it("displays conversation thread selector when multiple conversations exist", async () => {
		const mockConversation2: ConversationSummary = {
			...mockConversationSummary,
			id: "conv-2",
			message_count: 4,
		};

		mockListConversations.mockResolvedValue({
			data: {
				status: "success",
				message: "",
				data: [mockConversationSummary, mockConversation2],
			},
		});

		await renderAndWaitForLoad();

		await waitFor(() => {
			expect(screen.getByText(/Conversation Threads/i)).toBeInTheDocument();
		});
	});

	it("allows switching between conversation threads", async () => {
		const mockConversation2: ConversationSummary = {
			...mockConversationSummary,
			id: "conv-2",
			message_count: 4,
		};

		mockListConversations.mockResolvedValue({
			data: {
				status: "success",
				message: "",
				data: [mockConversationSummary, mockConversation2],
			},
		});

		mockGetThread.mockResolvedValue({
			data: {
				status: "success",
				message: "",
				data: {
					...mockConversation2,
					messages: mockMessages,
				},
			},
		});

		await renderAndWaitForLoad();

		await waitFor(() => {
			expect(screen.getByText(/Conversation Threads/i)).toBeInTheDocument();
		});

		// Find the second thread button (Thread 2) and click it
		const threadButtons = screen.getAllByRole("button", { name: /Thread/i });
		const thread2Button = threadButtons.find((btn) =>
			btn.textContent?.includes("Thread 2"),
		);

		if (thread2Button) {
			await act(async () => {
				fireEvent.click(thread2Button);
			});
		}

		await waitFor(() => {
			expect(mockGetThread).toHaveBeenCalledWith({
				path: {
					content_id: mockContentId,
					conversation_id: "conv-2",
				},
			});
		});
	});

	it("refreshes conversation summaries on button click", async () => {
		mockListConversations.mockResolvedValue({
			data: {
				status: "success",
				message: "",
				data: [mockConversationSummary],
			},
		});

		mockGetThread.mockResolvedValue({
			data: {
				status: "success",
				message: "",
				data: {
					...mockConversationSummary,
					messages: mockMessages,
				},
			},
		});

		await renderAndWaitForLoad();

		await waitFor(() => {
			expect(mockListConversations).toHaveBeenCalled();
		});

		const refreshButton = screen.getByLabelText(/refresh conversations/i);

		await act(async () => {
			fireEvent.click(refreshButton);
		});

		await waitFor(
			() => {
				expect(mockListConversations).toHaveBeenCalledTimes(2);
			},
			{ timeout: 3000 },
		);
	});
});
