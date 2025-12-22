"use client";

import type React from "react";
import { Skeleton } from "@/components/common/Skeleton";
import { ProfileManagement } from "@/components/features/ProfileManagement";
import { useAuthGuard } from "@/hooks/useAuthGuard";

const ProfilePage: React.FC = () => {
	const { isAuthenticated, isLoading } = useAuthGuard();

	if (isLoading) {
		return (
			<div className="min-h-screen bg-linear-to-br from-gray-900 via-blue-900 to-purple-900 text-gray-100 flex items-center justify-center">
				<Skeleton />
			</div>
		);
	}

	if (!isAuthenticated) {
		return (
			<div className="min-h-screen bg-linear-to-br from-gray-900 via-blue-900 to-purple-900 text-gray-100 flex items-center justify-center">
				<p className="morphio-body">Please log in to view this page.</p>
			</div>
		);
	}

	return (
		<div className="min-h-screen bg-linear-to-br from-gray-900 via-blue-900 to-purple-900 text-gray-100 py-12 px-4 sm:px-6 lg:px-8">
			<div className="max-w-4xl mx-auto">
				<div className="morphio-card">
					<div className="px-6 py-8 sm:p-10 space-y-8">
						<h1 className="morphio-h2 mb-6">Profile Management</h1>
						<ProfileManagement />
					</div>
				</div>
			</div>
		</div>
	);
};

export default ProfilePage;
