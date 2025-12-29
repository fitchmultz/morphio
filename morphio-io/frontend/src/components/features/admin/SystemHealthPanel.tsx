"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { getAdminHealth } from "@/client";
import { Skeleton } from "@/components/common/Skeleton";
import logger from "@/lib/logger";

type HealthComponent = {
	status: string;
	latency_ms?: number | null;
	detail?: string | null;
};

type SystemHealthData = {
	overall_status: string;
	components: Record<string, HealthComponent>;
};

const STATUS_STYLES: Record<string, { label: string; className: string }> = {
	ok: {
		label: "OK",
		className:
			"bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-200",
	},
	error: {
		label: "Error",
		className:
			"bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-200",
	},
	skipped: {
		label: "Skipped",
		className: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300",
	},
	degraded: {
		label: "Degraded",
		className:
			"bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-200",
	},
	down: {
		label: "Down",
		className:
			"bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-200",
	},
};

const formatName = (key: string) => {
	const formatted = key
		.replace(/_/g, " ")
		.replace(/\b\w/g, (char) => char.toUpperCase());
	if (formatted.toLowerCase() === "worker ml") {
		return "Worker ML";
	}
	return formatted;
};

export function SystemHealthPanel() {
	const [health, setHealth] = useState<SystemHealthData | null>(null);
	const [isLoading, setIsLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	const loadHealth = useCallback(async () => {
		setIsLoading(true);
		setError(null);
		try {
			const { data, error: apiError } = await getAdminHealth();
			if (apiError) {
				throw new Error(
					(apiError as { detail?: string }).detail ||
						"Failed to load system health",
				);
			}
			if (data?.status === "success" && data.data) {
				setHealth(data.data as SystemHealthData);
				return;
			}
			throw new Error(data?.message || "Failed to load system health");
		} catch (err) {
			const message =
				err instanceof Error ? err.message : "Failed to load system health";
			logger.warn("System health fetch failed", { error: message });
			setError(message);
		} finally {
			setIsLoading(false);
		}
	}, []);

	useEffect(() => {
		void loadHealth();
	}, [loadHealth]);

	const orderedComponents = useMemo(() => {
		if (!health?.components) {
			return [];
		}
		const order = ["database", "redis", "worker_ml", "crawler"];
		const entries = Object.entries(health.components);
		return [
			...order
				.filter((key) => key in health.components)
				.map((key) => [key, health.components[key]] as const),
			...entries.filter(([key]) => !order.includes(key)),
		];
	}, [health]);

	const isInitialLoading = isLoading && !health;

	return (
		<section className="morphio-card p-6 mb-8">
			<div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
				<div>
					<h2 className="morphio-h3">System Health</h2>
					{health?.overall_status && (
						<p className="morphio-body-sm text-gray-500 mt-1">
							Overall status:{" "}
							<span
								className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${
									STATUS_STYLES[health.overall_status]?.className ??
									STATUS_STYLES.skipped.className
								}`}
							>
								{STATUS_STYLES[health.overall_status]?.label ??
									health.overall_status}
							</span>
						</p>
					)}
				</div>
				<button
					type="button"
					onClick={loadHealth}
					disabled={isLoading}
					className="morphio-button px-4 py-1.5 text-sm disabled:opacity-50"
				>
					{isLoading ? "Refreshing..." : "Refresh"}
				</button>
			</div>

			{isInitialLoading ? (
				<div className="space-y-3">
					<Skeleton className="h-6 w-48" />
					<Skeleton className="h-10 w-full" />
					<Skeleton className="h-10 w-full" />
					<Skeleton className="h-10 w-full" />
				</div>
			) : error ? (
				<div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-rose-700 dark:border-rose-900/40 dark:bg-rose-900/20 dark:text-rose-200">
					<p className="morphio-body-sm">{error}</p>
				</div>
			) : (
				<div className="overflow-x-auto">
					<table className="min-w-full text-sm">
						<thead className="bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
							<tr>
								<th className="p-3 text-left font-medium">Component</th>
								<th className="p-3 text-left font-medium">Status</th>
								<th className="p-3 text-right font-medium">Latency</th>
								<th className="p-3 text-left font-medium">Detail</th>
							</tr>
						</thead>
						<tbody>
							{orderedComponents.map(([key, component]) => (
								<tr
									key={key}
									className="border-b border-gray-200 dark:border-gray-700"
								>
									<td className="p-3">{formatName(key)}</td>
									<td className="p-3">
										<span
											className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${
												STATUS_STYLES[component.status]?.className ??
												STATUS_STYLES.skipped.className
											}`}
										>
											{STATUS_STYLES[component.status]?.label ??
												component.status}
										</span>
									</td>
									<td className="p-3 text-right text-gray-500">
										{component.latency_ms != null
											? `${component.latency_ms} ms`
											: "—"}
									</td>
									<td className="p-3 text-gray-500">
										{component.detail || "—"}
									</td>
								</tr>
							))}
						</tbody>
					</table>
				</div>
			)}
		</section>
	);
}
