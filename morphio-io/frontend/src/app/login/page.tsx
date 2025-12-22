"use client";

import Link from "next/link";
import type React from "react";
import { useState } from "react";
import { FaArrowLeft, FaEnvelope, FaLock } from "react-icons/fa";
import { useAuth } from "@/contexts/AuthContext";
import { login as apiLogin } from "@/lib/auth";
import { notifyError, notifySuccess } from "@/lib/toast";

const LoginPage: React.FC = () => {
	const [email, setEmail] = useState("");
	const [password, setPassword] = useState("");
	const [isLoading, setIsLoading] = useState(false);
	const { login } = useAuth();

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setIsLoading(true);

		try {
			const loginResponse = await apiLogin(email, password);
			// AuthContext.login() handles localStorage + navigation to /dashboard
			login(loginResponse.access_token, loginResponse.user);
			notifySuccess("Successfully logged in!");
		} catch (error) {
			notifyError(error instanceof Error ? error.message : "Failed to login");
		} finally {
			setIsLoading(false);
		}
	};

	return (
		<div className="min-h-screen flex flex-col items-center justify-center relative">
			{/* Gradient Background */}
			<div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(120,119,198,0.3),rgba(255,255,255,0))] dark:bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(120,119,198,0.4),rgba(255,255,255,0))]" />

			{/* Back Button */}
			<Link
				href="/"
				className="absolute top-8 left-8 morphio-button-secondary inline-flex items-center gap-2"
			>
				<FaArrowLeft className="h-4 w-4" />
				Back to Home
			</Link>

			<div className="w-full max-w-md px-4 relative">
				{/* Login Card */}
				<div className="morphio-card p-8">
					<div className="text-center mb-8">
						<h1 className="morphio-h2 mb-2">Welcome Back</h1>
						<p className="morphio-body">Sign in to your account</p>
					</div>

					<form onSubmit={handleSubmit} className="space-y-6">
						{/* Email Input */}
						<div className="space-y-2">
							<label className="morphio-caption block font-medium">
								Email
								<div className="relative mt-2">
									<div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-gray-400 dark:text-gray-500">
										<FaEnvelope className="h-5 w-5" />
									</div>
									<input
										type="email"
										value={email}
										onChange={(e) => setEmail(e.target.value)}
										className="morphio-input pl-12"
										placeholder="Enter your email"
										required
									/>
								</div>
							</label>
						</div>

						{/* Password Input */}
						<div className="space-y-2">
							<label className="morphio-caption block font-medium">
								Password
								<div className="relative mt-2">
									<div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-gray-400 dark:text-gray-500">
										<FaLock className="h-5 w-5" />
									</div>
									<input
										type="password"
										value={password}
										onChange={(e) => setPassword(e.target.value)}
										className="morphio-input pl-12"
										placeholder="Enter your password"
										required
									/>
								</div>
							</label>
						</div>

						{/* Submit Button */}
						<button
							type="submit"
							disabled={isLoading}
							className="morphio-button w-full"
						>
							{isLoading ? (
								<div className="flex items-center justify-center gap-2">
									<div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
									<span>Logging in...</span>
								</div>
							) : (
								"Login"
							)}
						</button>

						{/* Register Link */}
						<p className="morphio-caption text-center">
							Don&apos;t have an account?{" "}
							<Link href="/register" className="morphio-link font-medium">
								Create one now
							</Link>
						</p>
					</form>
				</div>
			</div>
		</div>
	);
};

export default LoginPage;
