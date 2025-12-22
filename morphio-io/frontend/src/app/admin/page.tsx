"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
	getAdminUsage,
	getSubscriptions,
	type SubscriptionOut,
} from "@/client";
import { Skeleton } from "@/components/common/Skeleton";
import { useAuth } from "@/contexts/AuthContext";
import logger from "@/lib/logger";
import { notifyError } from "@/lib/toast";

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

export default function AdminPage() {
	const { isAuthenticated, userData, loading } = useAuth();
	const router = useRouter();
	const [usageData, setUsageData] = useState<UsageStat[]>([]);
	const [isLoadingUsage, setIsLoadingUsage] = useState(true);
	const [subscriptions, setSubscriptions] = useState<SubscriptionOut[]>([]);
	const [isLoadingSubs, setIsLoadingSubs] = useState(true);

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

	useEffect(() => {
		// Helper to extract error message
		const toUserMessage = (err: unknown, fallback: string): string =>
			err instanceof Error ? err.message : fallback;

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

		const fetchSubsData = async () => {
			if (!userData || userData.role?.toLowerCase() !== "admin") return;
			try {
				setIsLoadingSubs(true);
				const { data, error } = await getSubscriptions();
				if (error) {
					throw new Error(
						(error as { detail?: string }).detail ||
							"Failed to retrieve subscriptions",
					);
				}
				if (data?.status === "success" && data.data) {
					setSubscriptions(data.data);
				} else {
					throw new Error(data?.message || "Failed to retrieve subscriptions");
				}
			} catch (err) {
				const message = toUserMessage(err, "Failed to retrieve subscriptions");
				logger.warn("Subscriptions fetch failed", { error: message });
				notifyError(message);
			} finally {
				setIsLoadingSubs(false);
			}
		};

		fetchUsageStats();
		fetchSubsData();
	}, [userData]);

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

			<div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
				{/* Usage Stats */}
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

				{/* Subscription Data */}
				<section className="morphio-card p-6">
					<h2 className="morphio-h3 mb-6">Subscription Data</h2>

					{isLoadingSubs ? (
						<div className="py-8 text-center">
							<p className="morphio-body-sm">Loading subscription data...</p>
						</div>
					) : subscriptions.length === 0 ? (
						<div className="py-8 text-center">
							<p className="morphio-body-sm mb-2">
								No active subscriptions available.
							</p>
							<p className="morphio-caption">
								When users subscribe to paid plans, they will appear here.
							</p>
						</div>
					) : (
						<div className="overflow-x-auto">
							<table className="min-w-full text-sm">
								<thead className="bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
									<tr>
										<th className="p-3 text-left font-medium">
											Subscription ID
										</th>
										<th className="p-3 text-left font-medium">User ID</th>
										<th className="p-3 text-left font-medium">User Email</th>
										<th className="p-3 text-left font-medium">Plan</th>
										<th className="p-3 text-left font-medium">Status</th>
										<th className="p-3 text-left font-medium">Created</th>
										<th className="p-3 text-left font-medium">Updated</th>
									</tr>
								</thead>
								<tbody>
									{subscriptions.map((sub) => (
										<tr
											key={sub.id}
											className="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50/50 dark:hover:bg-gray-700/50"
										>
											<td className="p-3">{sub.id}</td>
											<td className="p-3">{sub.user_id}</td>
											<td className="p-3">{sub.user?.email ?? "N/A"}</td>
											<td className="p-3">{sub.plan}</td>
											<td className="p-3">{sub.status}</td>
											<td className="p-3">
												{sub.created_at
													? new Date(sub.created_at).toLocaleString()
													: "N/A"}
											</td>
											<td className="p-3">
												{sub.updated_at
													? new Date(sub.updated_at).toLocaleString()
													: "N/A"}
											</td>
										</tr>
									))}
								</tbody>
							</table>
						</div>
					)}
				</section>
			</div>
		</div>
	);
}
