"use client";

import type { FC } from "react";
import { useCallback, useEffect, useState } from "react";
import { getUserCredits, getUserProfile } from "@/client/sdk.gen";
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
import { notifyError } from "@/lib/toast";

export const ProfileManagement: FC = () => {
	const { updateUserData } = useAuth();
	const [userProfile, setUserProfile] =
		useState<AppSchemasAuthSchemaUserOut | null>(null);
	const [credits, setCredits] = useState<UserCredits | null>(null);
	const [loading, setLoading] = useState(true);
	const [fetchError, setFetchError] = useState<string | null>(null);

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

	const renderProfileSection = (title: string, content: React.ReactNode) => (
		<div className="bg-gray-50 dark:bg-gray-700 p-6 rounded-lg shadow-md">
			<h3 className="morphio-h3 mb-4">{title}</h3>
			{content}
		</div>
	);

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
										className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
										style={{
											width: `${Math.min(100, (credits.used / credits.limit) * 100)}%`,
										}}
									/>
								</div>
								<div className="flex justify-between items-center text-sm">
									<span className="text-gray-500 dark:text-gray-400">
										{credits.remaining} credits remaining
									</span>
									{credits.resets_monthly && (
										<span className="text-gray-500 dark:text-gray-400">
											Resets monthly
										</span>
									)}
								</div>
							</>
						)}
					</div>,
				)}
		</div>
	);
};
