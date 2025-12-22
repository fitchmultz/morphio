"use client";

import type { FC } from "react";
import { useAuth } from "@/contexts/AuthContext";
import logger from "@/lib/logger";

interface LogoutButtonProps {
	className?: string;
}

export const LogoutButton: FC<LogoutButtonProps> = ({ className = "" }) => {
	const { logout } = useAuth();

	const handleLogout = () => {
		logger.info("User initiated logout");
		logout("Successfully logged out");
	};

	return (
		<button
			type="button"
			onClick={handleLogout}
			className={`morphio-button-secondary !py-2 !px-4 ${className}`}
		>
			Logout
		</button>
	);
};
