"use client";

import type { FC } from "react";
import { useCallback, useEffect, useState } from "react";
import {
	createApiKey,
	createCheckoutSession,
	createPortalSession,
	getUserCredits,
	getUserProfile,
	listApiKeys,
	revokeApiKey,
} from "@/client/sdk.gen";
import type {
	AppSchemasAuthSchemaUserOut,
	UserCredits,
} from "@/client/types.gen";
import { Skeleton } from "@/components/common/Skeleton";
import { ChangeDisplayNameForm } from "@/components/forms/ChangeDisplayNameForm";
import { ChangeEmailForm } from "@/components/forms/ChangeEmailForm";
import { ChangePasswordForm } from "@/components/forms/ChangePasswordForm";
import { useAuth } from "@/contexts/AuthContext";
import logger from "@/lib/logger";
import { notifyError, notifySuccess } from "@/lib/toast";

type ApiKey = {
	id: number;
	name: string;
	key_prefix: string;
	scopes: string[];
	last_used_at: string | null;
	created_at: string;
};

type ApiKeyCreated = ApiKey & {
	key: string;
};

export const ProfileManagement: FC = () => {
	const { updateUserData } = useAuth();
	const [userProfile, setUserProfile] =
		useState<AppSchemasAuthSchemaUserOut | null>(null);
	const [credits, setCredits] = useState<UserCredits | null>(null);
	const [loading, setLoading] = useState(true);
	const [fetchError, setFetchError] = useState<string | null>(null);
	const [isUpgrading, setIsUpgrading] = useState(false);
	const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
	const [apiKeysLoading, setApiKeysLoading] = useState(true);
	const [apiKeyError, setApiKeyError] = useState<string | null>(null);
	const [apiKeyName, setApiKeyName] = useState("");
	const [isCreatingKey, setIsCreatingKey] = useState(false);
	const [newApiKey, setNewApiKey] = useState<ApiKeyCreated | null>(null);
	const [revokingKeyId, setRevokingKeyId] = useState<number | null>(null);

	const fetchUserProfile = useCallback(async () => {
		try {
			setLoading(true);
			setFetchError(null);
			const response = await getUserProfile();

			if (response.data) {
				setUserProfile(response.data);
				updateUserData(response.data);
			} else {
				const errorMessage =
					response.error &&
					typeof response.error === "object" &&
					"message" in response.error
						? String(response.error.message)
						: "Failed to fetch user profile";
				throw new Error(errorMessage);
			}

			// Fetch credits
			try {
				const creditsResponse = await getUserCredits();
				if (creditsResponse.data) {
					setCredits(creditsResponse.data);
				}
			} catch (creditsError) {
				logger.warn("Failed to fetch credits", { error: creditsError });
				// Non-fatal - profile can still display without credits
			}
		} catch (error) {
			const message =
				error instanceof Error ? error.message : "Failed to load user profile";
			logger.warn("Failed to fetch user profile", { error });
			setFetchError(message);
			notifyError("Failed to load user profile. Please try again.");
		} finally {
			setLoading(false);
		}
	}, [updateUserData]);

	useEffect(() => {
		fetchUserProfile();
	}, [fetchUserProfile]);

	const fetchApiKeys = useCallback(async () => {
		try {
			setApiKeysLoading(true);
			setApiKeyError(null);
			const { data, error } = await listApiKeys();
			if (error) {
				throw new Error(
					typeof error === "object" && error && "detail" in error
						? String((error as { detail?: string }).detail)
						: "Failed to load API keys",
				);
			}
			const responseData = data as {
				status?: string;
				data?: ApiKey[];
				message?: string;
			} | null;
			if (responseData?.status === "success" && responseData.data) {
				setApiKeys(responseData.data);
			} else {
				throw new Error(responseData?.message || "Failed to load API keys");
			}
		} catch (error) {
			const message =
				error instanceof Error ? error.message : "Failed to load API keys";
			setApiKeyError(message);
			logger.warn("Failed to fetch API keys", { error });
		} finally {
			setApiKeysLoading(false);
		}
	}, []);

	useEffect(() => {
		fetchApiKeys();
	}, [fetchApiKeys]);

	const handleProfileUpdate = (
		updateKey: keyof AppSchemasAuthSchemaUserOut,
		newValue: string,
	) => {
		if (userProfile) {
			const updatedProfile = { ...userProfile, [updateKey]: newValue };
			setUserProfile(updatedProfile);
			updateUserData(updatedProfile);
			logger.info(`${updateKey} updated successfully`, {
				userId: userProfile.id,
			});
		}
	};

	const handleUpgrade = async (plan: "pro" | "enterprise") => {
		try {
			setIsUpgrading(true);
			const response = await createCheckoutSession({
				query: { plan },
			});
			const responseData = response.data as {
				data?: { checkout_url?: string };
			} | null;
			if (responseData?.data?.checkout_url) {
				window.location.href = responseData.data.checkout_url;
			} else {
				notifyError("Failed to create checkout session");
			}
		} catch (error) {
			logger.error("Failed to create checkout session", { error });
			notifyError("Failed to start upgrade process. Please try again.");
		} finally {
			setIsUpgrading(false);
		}
	};

	const handleCreateApiKey = async () => {
		const trimmedName = apiKeyName.trim();
		if (!trimmedName) {
			notifyError("Please enter a name for the API key.");
			return;
		}

		try {
			setIsCreatingKey(true);
			const { data, error } = await createApiKey({
				body: { name: trimmedName },
			});
			if (error) {
				throw new Error(
					typeof error === "object" && error && "detail" in error
						? String((error as { detail?: string }).detail)
						: "Failed to create API key",
				);
			}
			const responseData = data as {
				status?: string;
				data?: ApiKeyCreated;
				message?: string;
			} | null;
			if (responseData?.status === "success" && responseData.data) {
				setNewApiKey(responseData.data);
				setApiKeyName("");
				await fetchApiKeys();
				notifySuccess("API key created. Store it securely.");
			} else {
				throw new Error(responseData?.message || "Failed to create API key");
			}
		} catch (error) {
			logger.error("Failed to create API key", { error });
			notifyError("Failed to create API key. Please try again.");
		} finally {
			setIsCreatingKey(false);
		}
	};

	const handleCopyApiKey = async (key: string) => {
		try {
			await navigator.clipboard.writeText(key);
			notifySuccess("API key copied to clipboard.");
		} catch (error) {
			logger.warn("Clipboard copy failed, falling back", { error });
			const input = document.createElement("input");
			input.value = key;
			document.body.appendChild(input);
			input.select();
			document.execCommand("copy");
			input.remove();
			notifySuccess("API key copied to clipboard.");
		}
	};

	const handleRevokeApiKey = async (keyId: number) => {
		if (
			!window.confirm("Revoke this API key? It will stop working immediately.")
		) {
			return;
		}

		try {
			setRevokingKeyId(keyId);
			const { data, error } = await revokeApiKey({
				path: { key_id: keyId },
			});
			if (error) {
				throw new Error(
					typeof error === "object" && error && "detail" in error
						? String((error as { detail?: string }).detail)
						: "Failed to revoke API key",
				);
			}
			const responseData = data as {
				status?: string;
				message?: string;
			} | null;
			if (responseData?.status === "success") {
				await fetchApiKeys();
				notifySuccess("API key revoked.");
			} else {
				throw new Error(responseData?.message || "Failed to revoke API key");
			}
		} catch (error) {
			logger.error("Failed to revoke API key", { error });
			notifyError("Failed to revoke API key. Please try again.");
		} finally {
			setRevokingKeyId(null);
		}
	};

	const handleManageBilling = async () => {
		try {
			setIsUpgrading(true);
			const response = await createPortalSession();
			const responseData = response.data as {
				data?: { portal_url?: string };
			} | null;
			if (responseData?.data?.portal_url) {
				window.location.href = responseData.data.portal_url;
			} else {
				notifyError("Failed to create portal session");
			}
		} catch (error) {
			logger.error("Failed to create portal session", { error });
			notifyError("Failed to open billing portal. Please try again.");
		} finally {
			setIsUpgrading(false);
		}
	};

	const renderProfileSection = (title: string, content: React.ReactNode) => (
		<div className="bg-gray-50 dark:bg-gray-700 p-6 rounded-lg shadow-md">
			<h3 className="morphio-h3 mb-4">{title}</h3>
			{content}
		</div>
	);

	const formatDateTime = (value: string | null) =>
		value ? new Date(value).toLocaleString() : "Never";

	if (loading) {
		return (
			<div className="space-y-8">
				<div className="bg-gray-50 dark:bg-gray-700 p-6 rounded-lg shadow-md">
					<Skeleton className="h-6 w-48 mb-4" />
					<Skeleton className="h-4 w-64 mb-2" variant="text" />
					<Skeleton className="h-4 w-56 mb-2" variant="text" />
					<Skeleton className="h-4 w-32" variant="text" />
				</div>
				<div className="bg-gray-50 dark:bg-gray-700 p-6 rounded-lg shadow-md">
					<Skeleton className="h-6 w-32 mb-4" />
					<Skeleton className="h-10 w-full mb-2" />
					<Skeleton className="h-10 w-24" />
				</div>
				<div className="bg-gray-50 dark:bg-gray-700 p-6 rounded-lg shadow-md">
					<Skeleton className="h-6 w-40 mb-4" />
					<Skeleton className="h-10 w-full mb-2" />
					<Skeleton className="h-10 w-24" />
				</div>
			</div>
		);
	}

	if (!userProfile) {
		return (
			<div className="text-center py-8 space-y-4">
				<p className="morphio-body text-red-600 dark:text-red-400">
					{fetchError || "Failed to load user profile."}
				</p>
				<button
					type="button"
					onClick={fetchUserProfile}
					className="morphio-button px-6 py-2"
				>
					Retry
				</button>
			</div>
		);
	}

	return (
		<div className="space-y-8">
			{renderProfileSection(
				"Current Profile Information",
				<>
					<p className="morphio-body">Email: {userProfile.email}</p>
					<p className="morphio-body">
						Display Name: {userProfile.display_name}
					</p>
					<p className="morphio-body">Role: {userProfile.role}</p>
				</>,
			)}
			{renderProfileSection(
				"Change Email",
				<ChangeEmailForm
					currentEmail={userProfile.email}
					onUpdate={(newEmail) => handleProfileUpdate("email", newEmail)}
				/>,
			)}
			{renderProfileSection(
				"Change Display Name",
				<ChangeDisplayNameForm
					currentDisplayName={userProfile.display_name}
					onUpdate={(newDisplayName) =>
						handleProfileUpdate("display_name", newDisplayName)
					}
				/>,
			)}
			{renderProfileSection("Change Password", <ChangePasswordForm />)}
			{credits &&
				renderProfileSection(
					"Usage Credits",
					<div className="space-y-4">
						{/* Warning banners for low credits */}
						{!credits.is_admin &&
							credits.remaining_pct !== undefined &&
							credits.remaining_pct < 5 && (
								<div className="p-3 bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded-lg">
									<p className="morphio-body-sm text-red-700 dark:text-red-300 font-medium">
										Critical: Less than 5% of credits remaining!
									</p>
									<p className="morphio-caption text-red-600 dark:text-red-400">
										Upgrade your plan to continue using AI features.
									</p>
								</div>
							)}
						{!credits.is_admin &&
							credits.remaining_pct !== undefined &&
							credits.remaining_pct >= 5 &&
							credits.remaining_pct < 20 && (
								<div className="p-3 bg-yellow-100 dark:bg-yellow-900/30 border border-yellow-300 dark:border-yellow-700 rounded-lg">
									<p className="morphio-body-sm text-yellow-700 dark:text-yellow-300 font-medium">
										Warning: Less than 20% of credits remaining
									</p>
									<p className="morphio-caption text-yellow-600 dark:text-yellow-400">
										Consider upgrading to avoid running out of credits.
									</p>
								</div>
							)}

						<div className="flex justify-between items-center">
							<span className="morphio-body font-medium">Plan:</span>
							<span className="morphio-body capitalize">{credits.plan}</span>
						</div>
						{credits.is_admin ? (
							<p className="morphio-body text-green-600 dark:text-green-400">
								Unlimited credits (Admin)
							</p>
						) : (
							<>
								<div className="flex justify-between items-center">
									<span className="morphio-body">Used this month:</span>
									<span className="morphio-body">
										{credits.used} / {credits.limit}
									</span>
								</div>
								<div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2.5">
									<div
										className={`h-2.5 rounded-full transition-all duration-300 ${
											credits.remaining_pct !== undefined &&
											credits.remaining_pct < 5
												? "bg-red-600"
												: credits.remaining_pct !== undefined &&
														credits.remaining_pct < 20
													? "bg-yellow-500"
													: "bg-blue-600"
										}`}
										style={{
											width: `${Math.min(100, (credits.used / credits.limit) * 100)}%`,
										}}
									/>
								</div>
								<div className="flex justify-between items-center text-sm">
									<span className="text-gray-500 dark:text-gray-400">
										{credits.remaining} credits remaining (
										{credits.remaining_pct?.toFixed(0) ?? 0}%)
									</span>
									{credits.reset_date && (
										<span className="text-gray-500 dark:text-gray-400">
											Resets {new Date(credits.reset_date).toLocaleDateString()}
										</span>
									)}
								</div>

								{/* Upgrade CTA */}
								<div className="pt-4 border-t border-gray-200 dark:border-gray-600">
									{credits.plan === "free" ? (
										<div className="space-y-2">
											<p className="morphio-body-sm text-gray-600 dark:text-gray-300">
												Upgrade for more credits and features
											</p>
											<div className="flex gap-3">
												<button
													type="button"
													onClick={() => handleUpgrade("pro")}
													disabled={isUpgrading}
													className="morphio-button px-4 py-2 text-sm"
												>
													{isUpgrading ? "Loading..." : "Upgrade to Pro"}
												</button>
												<button
													type="button"
													onClick={() => handleUpgrade("enterprise")}
													disabled={isUpgrading}
													className="morphio-button-secondary px-4 py-2 text-sm"
												>
													{isUpgrading ? "Loading..." : "Enterprise"}
												</button>
											</div>
										</div>
									) : (
										<button
											type="button"
											onClick={handleManageBilling}
											disabled={isUpgrading}
											className="morphio-button-secondary px-4 py-2 text-sm"
										>
											{isUpgrading ? "Loading..." : "Manage Billing"}
										</button>
									)}
								</div>
							</>
						)}
					</div>,
				)}
			{renderProfileSection(
				"API Keys",
				<div className="space-y-4">
					<div className="space-y-2">
						<label
							htmlFor="apiKeyName"
							className="morphio-body-sm text-gray-600 dark:text-gray-300"
						>
							Create a new API key
						</label>
						<div className="flex flex-col sm:flex-row gap-3">
							<input
								id="apiKeyName"
								type="text"
								value={apiKeyName}
								onChange={(event) => setApiKeyName(event.target.value)}
								placeholder="Key name (e.g. CLI access)"
								className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-sm"
							/>
							<button
								type="button"
								onClick={handleCreateApiKey}
								disabled={isCreatingKey}
								className="morphio-button px-4 py-2 text-sm"
							>
								{isCreatingKey ? "Creating..." : "Create Key"}
							</button>
						</div>
					</div>

					{newApiKey && (
						<div className="p-4 border border-amber-200 dark:border-amber-700 rounded-lg bg-amber-50 dark:bg-amber-900/20 space-y-2">
							<p className="morphio-body-sm font-medium text-amber-800 dark:text-amber-200">
								Save this key now. It will not be shown again.
							</p>
							<div className="flex flex-col sm:flex-row sm:items-center gap-3">
								<code className="px-3 py-2 rounded bg-amber-100 dark:bg-amber-900/40 text-amber-900 dark:text-amber-100 text-sm break-all">
									{newApiKey.key}
								</code>
								<button
									type="button"
									onClick={() => handleCopyApiKey(newApiKey.key)}
									className="morphio-button-secondary px-3 py-2 text-sm"
								>
									Copy
								</button>
							</div>
							<p className="morphio-caption text-amber-700 dark:text-amber-300">
								Key name: {newApiKey.name} • Prefix: {newApiKey.key_prefix}
							</p>
						</div>
					)}

					<div className="space-y-3">
						<h4 className="morphio-body font-medium">Existing API keys</h4>
						{apiKeysLoading ? (
							<p className="morphio-body-sm">Loading API keys...</p>
						) : apiKeyError ? (
							<p className="morphio-body-sm text-red-600 dark:text-red-400">
								{apiKeyError}
							</p>
						) : apiKeys.length === 0 ? (
							<p className="morphio-body-sm text-gray-500">
								No API keys created yet.
							</p>
						) : (
							<div className="overflow-x-auto">
								<table className="min-w-full text-sm">
									<thead className="bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300">
										<tr>
											<th className="p-3 text-left font-medium">Name</th>
											<th className="p-3 text-left font-medium">Prefix</th>
											<th className="p-3 text-left font-medium">Created</th>
											<th className="p-3 text-left font-medium">Last Used</th>
											<th className="p-3 text-right font-medium">Actions</th>
										</tr>
									</thead>
									<tbody>
										{apiKeys.map((key) => (
											<tr
												key={key.id}
												className="border-b border-gray-200 dark:border-gray-600"
											>
												<td className="p-3">{key.name}</td>
												<td className="p-3 font-mono">{key.key_prefix}</td>
												<td className="p-3">
													{formatDateTime(key.created_at)}
												</td>
												<td className="p-3">
													{formatDateTime(key.last_used_at)}
												</td>
												<td className="p-3 text-right">
													<button
														type="button"
														onClick={() => handleRevokeApiKey(key.id)}
														disabled={revokingKeyId === key.id}
														className="morphio-button-secondary px-3 py-1.5 text-xs"
													>
														{revokingKeyId === key.id
															? "Revoking..."
															: "Revoke"}
													</button>
												</td>
											</tr>
										))}
									</tbody>
								</table>
							</div>
						)}
					</div>
				</div>,
			)}
		</div>
	);
};
