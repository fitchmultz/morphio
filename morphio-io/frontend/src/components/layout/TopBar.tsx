"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React from "react";
import { FaBars, FaTimes } from "react-icons/fa";
import { DarkModeToggle } from "@/components/common/DarkModeToggle";
import { LogoutButton } from "@/components/features/LogoutButton";
import { useAuth } from "@/contexts/AuthContext";
import { logout } from "@/lib/auth";

export const TopBar: React.FC = () => {
	const { isAuthenticated, loading, userData } = useAuth();
	const pathname = usePathname();
	const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);

	const isAdmin = userData?.role?.toLowerCase() === "admin";

	const navItems = [
		{ href: "/", label: "Home" },
		{ href: "/dashboard", label: "Dashboard", authRequired: true },
		{ href: "/transcripts", label: "Transcripts", authRequired: true },
		{ href: "/logs", label: "Logs", authRequired: true },
		{ href: "/splunk-config", label: "Splunk Config", authRequired: true },
		{ href: "/profile", label: "Profile", authRequired: true },
		{ href: "/admin", label: "Admin", authRequired: true, adminOnly: true },
	];

	const toggleMobileMenu = () => {
		setIsMobileMenuOpen((prev) => !prev);
	};

	const handleLogoutClick = async () => {
		await logout();
		setIsMobileMenuOpen(false);
	};

	return (
		<header className="sticky top-0 z-50">
			<nav className="bg-white/90 dark:bg-gray-900/90 backdrop-blur-xl shadow-md border-b border-gray-200/50 dark:border-gray-800/50">
				<div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
					<div className="flex justify-between items-center py-4">
						{/* Logo */}
						<div className="flex-shrink-0">
							<Link href="/" className="flex items-center">
								<span className="morphio-title text-2xl">Morphio</span>
							</Link>
						</div>

						{/* Desktop Navigation */}
						<div className="hidden md:flex items-center space-x-6">
							{navItems.map((item) => {
								if (item.authRequired && !isAuthenticated) return null;
								if (item.adminOnly && !isAdmin) return null;
								const isActive = pathname === item.href;
								return (
									<Link
										key={item.href}
										href={item.href}
										className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-200 ${
											isActive
												? "bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300"
												: "morphio-text hover:bg-gray-100 dark:hover:bg-gray-800/50 hover:text-blue-600 dark:hover:text-blue-400"
										}`}
									>
										{item.label}
									</Link>
								);
							})}
							<DarkModeToggle />
							{isAuthenticated && !loading && <LogoutButton />}
							{!isAuthenticated && !loading && (
								<Link href="/login" className="morphio-button !py-2 !px-4">
									Login
								</Link>
							)}
						</div>

						{/* Mobile Menu Button */}
						<div className="md:hidden flex items-center">
							<DarkModeToggle />
							<button
								type="button"
								onClick={toggleMobileMenu}
								className="morphio-icon-button ml-4"
								aria-label="Toggle menu"
							>
								{isMobileMenuOpen ? (
									<FaTimes className="h-6 w-6" />
								) : (
									<FaBars className="h-6 w-6" />
								)}
							</button>
						</div>
					</div>

					{/* Mobile Navigation */}
					{isMobileMenuOpen && (
						<div className="md:hidden px-2 pt-2 pb-3 space-y-1 bg-white/95 dark:bg-gray-900/95 backdrop-blur-xl border-t border-gray-200/50 dark:border-gray-800/50">
							{navItems.map((item) => {
								if (item.authRequired && !isAuthenticated) return null;
								if (item.adminOnly && !isAdmin) return null;
								const isActive = pathname === item.href;
								return (
									<Link
										key={item.href}
										href={item.href}
										className={`block px-3 py-2 rounded-lg text-base font-medium transition-colors duration-200 ${
											isActive
												? "bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300"
												: "morphio-text hover:bg-gray-100 dark:hover:bg-gray-800/50 hover:text-blue-600 dark:hover:text-blue-400"
										}`}
										onClick={() => setIsMobileMenuOpen(false)}
									>
										{item.label}
									</Link>
								);
							})}
							{!isAuthenticated && !loading && (
								<Link
									href="/login"
									className="morphio-button block !px-3 !py-2 w-full text-left"
									onClick={() => setIsMobileMenuOpen(false)}
								>
									Login
								</Link>
							)}
							{isAuthenticated && !loading && (
								<button
									type="button"
									onClick={handleLogoutClick}
									className="morphio-button-secondary w-full text-left !px-3 !py-2"
								>
									Logout
								</button>
							)}
						</div>
					)}
				</div>
			</nav>
		</header>
	);
};
