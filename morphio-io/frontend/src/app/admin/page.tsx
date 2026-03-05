/**
 * Purpose: Render the administrator control panel.
 * Responsibilities: Show system health, usage analytics, and export tools for maintainers.
 * Scope: Client-side admin dashboard for authenticated admin users.
 * Usage: Mounted on `/admin` for users with the admin role.
 * Invariants/Assumptions: Public portfolio builds should focus this page on operational visibility, not monetization management.
 */

"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { getAdminUsage, getLlmUsageSummary } from "@/client";
import { Skeleton } from "@/components/common/Skeleton";
import { SystemHealthPanel } from "@/components/features/admin/SystemHealthPanel";
import { useAuth } from "@/contexts/AuthContext";
import logger from "@/lib/logger";
import { notifyError, notifySuccess } from "@/lib/toast";
import { API_BASE_URL } from "@/utils/constants";

type UsageStat = {
	usage_id: number;
	user_id: number;
	user_email: string | null;
	display_name: string | null;
	usage_type: string;
	usage_calls: number;
	usage_points: number;
	last_used_at?: string;
	created_at?: string;
	updated_at?: string;
};

type LLMUsageSummary = {
	total_requests: number;
	total_tokens: number;
	total_cost_usd: number;
	by_provider: Array<{
		provider: string;
		requests: number;
		tokens: number;
		cost_usd: number;
	}>;
};

export default function AdminPage() {
	const { isAuthenticated, userData, loading, getToken } = useAuth();
	const router = useRouter();
	const [usageData, setUsageData] = useState<UsageStat[]>([]);
	const [isLoadingUsage, setIsLoadingUsage] = useState(true);
	const [llmSummary, setLLMSummary] = useState<LLMUsageSummary | null>(null);
	const [isLoadingLLM, setIsLoadingLLM] = useState(true);
	const [exportStartDate, setExportStartDate] = useState<string>("");
	const [exportEndDate, setExportEndDate] = useState<string>("");
	const [isExporting, setIsExporting] = useState(false);

	useEffect(() => {
		// Only allow admins
		if (
			!loading &&
			(!isAuthenticated ||
				!userData?.role ||
				userData.role.toLowerCase() !== "admin")
		) {
			logger.warn("Non-admin user attempted to access admin page");
			router.push("/");
		}
	}, [loading, isAuthenticated, userData, router]);

	// Helper to extract error message
	const toUserMessage = useCallback(
		(err: unknown, fallback: string): string =>
			err instanceof Error ? err.message : fallback,
		[],
	);

	const handleExportCSV = useCallback(async () => {
		if (!userData || userData.role?.toLowerCase() !== "admin") return;
		setIsExporting(true);
		try {
			const params = new URLSearchParams();
			if (exportStartDate) params.append("start", exportStartDate);
			if (exportEndDate) params.append("end", exportEndDate);
			params.append("format", "csv");
			const token = getToken();
			const headers: HeadersInit = {};
			if (token) {
				headers.Authorization = `Bearer ${token}`;
			}

			const response = await fetch(
				`${API_BASE_URL}/admin/usage/export?${params.toString()}`,
				{
					credentials: "include",
					headers,
				},
			);

			if (!response.ok) {
				throw new Error("Failed to export usage data");
			}

			const blob = await response.blob();
			const url = window.URL.createObjectURL(blob);
			const a = document.createElement("a");
			a.href = url;
			a.download =
				response.headers
					.get("Content-Disposition")
					?.match(/filename="(.+)"/)?.[1] || "llm_usage.csv";
			document.body.appendChild(a);
			a.click();
			window.URL.revokeObjectURL(url);
			a.remove();

			notifySuccess("Usage data exported successfully");
		} catch (err) {
			const message = toUserMessage(err, "Failed to export usage data");
			logger.warn("Export failed", { error: message });
			notifyError(message);
		} finally {
			setIsExporting(false);
		}
	}, [userData, exportStartDate, exportEndDate, getToken, toUserMessage]);

	useEffect(() => {
		const fetchUsageStats = async () => {
			if (!userData || userData.role?.toLowerCase() !== "admin") return;
			try {
				setIsLoadingUsage(true);
				const { data, error } = await getAdminUsage();
				if (error) {
					throw new Error(
						(error as { detail?: string }).detail ||
							"Failed to retrieve usage data",
					);
				}
				if (data?.status === "success" && data.data) {
					setUsageData(data.data as unknown as UsageStat[]);
				} else {
					throw new Error(data?.message || "Failed to retrieve usage data");
				}
			} catch (err) {
				const message = toUserMessage(err, "Failed to retrieve usage data");
				logger.warn("Usage data fetch failed", { error: message });
				notifyError(message);
			} finally {
				setIsLoadingUsage(false);
			}
		};

		const fetchLLMSummary = async () => {
			if (!userData || userData.role?.toLowerCase() !== "admin") return;
			try {
				setIsLoadingLLM(true);
				const { data, error } = await getLlmUsageSummary();
				if (error) {
					throw new Error(
						(error as { detail?: string }).detail ||
							"Failed to retrieve LLM usage summary",
					);
				}
				const responseData = data as {
					status?: string;
					data?: LLMUsageSummary;
				} | null;
				if (responseData?.status === "success" && responseData.data) {
					setLLMSummary(responseData.data);
				}
			} catch (err) {
				const message = toUserMessage(
					err,
					"Failed to retrieve LLM usage summary",
				);
				logger.warn("LLM summary fetch failed", { error: message });
				// Non-fatal - don't show error toast
			} finally {
				setIsLoadingLLM(false);
			}
		};

		fetchUsageStats();
		fetchLLMSummary();
	}, [userData, toUserMessage]);

	if (loading) {
		return (
			<div className="max-w-7xl mx-auto py-8 px-4 space-y-8">
				<Skeleton className="h-10 w-64" />
				<div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
					<div className="morphio-card p-6 space-y-6">
						<Skeleton className="h-8 w-48" />
						<Skeleton className="h-64 w-full" />
					</div>
					<div className="morphio-card p-6 space-y-6">
						<Skeleton className="h-8 w-48" />
						<Skeleton className="h-64 w-full" />
					</div>
				</div>
			</div>
		);
	}

	if (!isAuthenticated || userData?.role?.toLowerCase() !== "admin") {
		return null;
	}

	return (
		<div className="max-w-7xl mx-auto py-8 px-4">
			<h1 className="morphio-h2 mb-8">Admin Dashboard</h1>

			<SystemHealthPanel />

			{/* LLM Usage Summary and Export */}
			<section className="morphio-card p-6 mb-8">
				<div className="flex flex-col md:flex-row md:items-center md:justify-between mb-6">
					<h2 className="morphio-h3 mb-4 md:mb-0">LLM Usage Summary</h2>
					<div className="flex flex-col sm:flex-row gap-3">
						<div className="flex items-center gap-2">
							<label
								htmlFor="startDate"
								className="morphio-body-sm text-gray-600 dark:text-gray-400"
							>
								From:
							</label>
							<input
								type="date"
								id="startDate"
								value={exportStartDate}
								onChange={(e) => setExportStartDate(e.target.value)}
								className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-sm"
							/>
						</div>
						<div className="flex items-center gap-2">
							<label
								htmlFor="endDate"
								className="morphio-body-sm text-gray-600 dark:text-gray-400"
							>
								To:
							</label>
							<input
								type="date"
								id="endDate"
								value={exportEndDate}
								onChange={(e) => setExportEndDate(e.target.value)}
								className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-sm"
							/>
						</div>
						<button
							type="button"
							onClick={handleExportCSV}
							disabled={isExporting}
							className="morphio-button px-4 py-1.5 text-sm disabled:opacity-50"
						>
							{isExporting ? "Exporting..." : "Export CSV"}
						</button>
					</div>
				</div>

				{isLoadingLLM ? (
					<div className="py-4 text-center">
						<p className="morphio-body-sm">Loading LLM usage summary...</p>
					</div>
				) : llmSummary ? (
					<div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
						<div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
							<p className="morphio-body-sm text-blue-600 dark:text-blue-400">
								Total Requests
							</p>
							<p className="morphio-h3 text-blue-800 dark:text-blue-200">
								{llmSummary.total_requests.toLocaleString()}
							</p>
						</div>
						<div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
							<p className="morphio-body-sm text-green-600 dark:text-green-400">
								Total Tokens
							</p>
							<p className="morphio-h3 text-green-800 dark:text-green-200">
								{llmSummary.total_tokens.toLocaleString()}
							</p>
						</div>
						<div className="bg-purple-50 dark:bg-purple-900/20 p-4 rounded-lg">
							<p className="morphio-body-sm text-purple-600 dark:text-purple-400">
								Estimated Cost
							</p>
							<p className="morphio-h3 text-purple-800 dark:text-purple-200">
								${llmSummary.total_cost_usd.toFixed(2)}
							</p>
						</div>
					</div>
				) : (
					<p className="morphio-body-sm text-gray-500">
						No LLM usage data available yet.
					</p>
				)}

				{llmSummary && llmSummary.by_provider.length > 0 && (
					<div>
						<h3 className="morphio-body font-medium mb-3">Usage by Provider</h3>
						<div className="overflow-x-auto">
							<table className="min-w-full text-sm">
								<thead className="bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
									<tr>
										<th className="p-3 text-left font-medium">Provider</th>
										<th className="p-3 text-right font-medium">Requests</th>
										<th className="p-3 text-right font-medium">Tokens</th>
										<th className="p-3 text-right font-medium">Cost</th>
									</tr>
								</thead>
								<tbody>
									{llmSummary.by_provider.map((p) => (
										<tr
											key={p.provider}
											className="border-b border-gray-200 dark:border-gray-700"
										>
											<td className="p-3 capitalize">{p.provider}</td>
											<td className="p-3 text-right">
												{p.requests.toLocaleString()}
											</td>
											<td className="p-3 text-right">
												{p.tokens.toLocaleString()}
											</td>
											<td className="p-3 text-right">
												${p.cost_usd.toFixed(2)}
											</td>
										</tr>
									))}
								</tbody>
							</table>
						</div>
					</div>
				)}
			</section>

			<section className="morphio-card p-6">
				<h2 className="morphio-h3 mb-6">Usage Stats</h2>

				{isLoadingUsage ? (
					<div className="py-8 text-center">
						<p className="morphio-body-sm">Loading usage data...</p>
					</div>
				) : usageData.length === 0 ? (
					<div className="py-8 text-center">
						<p className="morphio-body-sm">No usage data available.</p>
					</div>
				) : (
					<div className="overflow-x-auto">
						<table className="min-w-full text-sm">
							<thead className="bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
								<tr>
									<th className="p-3 text-left font-medium">User ID</th>
									<th className="p-3 text-left font-medium">Email</th>
									<th className="p-3 text-left font-medium">Display Name</th>
									<th className="p-3 text-left font-medium">Usage Type</th>
									<th className="p-3 text-right font-medium">Calls</th>
								</tr>
							</thead>
							<tbody>
								{usageData.map((u) => (
									<tr
										key={u.usage_id}
										className="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50/50 dark:hover:bg-gray-700/50"
									>
										<td className="p-3">{u.user_id}</td>
										<td className="p-3">{u.user_email || "N/A"}</td>
										<td className="p-3">{u.display_name || "N/A"}</td>
										<td className="p-3">{u.usage_type}</td>
										<td className="p-3 text-right">{u.usage_calls}</td>
									</tr>
								))}
							</tbody>
						</table>
					</div>
				)}
			</section>
		</div>
	);
}
