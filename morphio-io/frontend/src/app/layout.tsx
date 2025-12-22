import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "next-themes";
import { ToastContainer } from "react-toastify";
import { AuthProvider } from "@/contexts/AuthContext";
import "react-toastify/dist/ReactToastify.css";
import { TopBar } from "@/components/layout/TopBar";
import { QueryProvider } from "@/lib/providers/query-provider";
import logger from "../lib/logger";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
	title: "Morphio",
	description: "Generate content from YouTube videos or local video files",
};

export default function RootLayout({
	children,
}: {
	children: React.ReactNode;
}) {
	logger.info("Rendering RootLayout");
	return (
		<html lang="en" suppressHydrationWarning>
			<body
				className={`${inter.className} antialiased min-h-screen bg-linear-to-br from-white via-blue-50/50 to-purple-50/50 dark:from-gray-900 dark:via-blue-950 dark:to-purple-950`}
			>
				<QueryProvider>
					<ThemeProvider attribute="class" defaultTheme="dark">
						<AuthProvider>
							<div className="flex flex-col min-h-screen relative">
								{/* Gradient overlay */}
								<div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(120,119,198,0.15),rgba(255,255,255,0))] dark:bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(120,119,198,0.3),rgba(255,255,255,0))]" />
								<TopBar />
								<main className="grow relative">
									<div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-4 sm:py-6 lg:py-8">
										{children}
									</div>
								</main>
								<footer className="text-center py-6">
									<p className="morphio-caption">
										&copy; {new Date().getFullYear()} Morphio. All rights
										reserved.
									</p>
								</footer>
							</div>
							<ToastContainer
								position="top-right"
								autoClose={3000}
								hideProgressBar={false}
								newestOnTop
								closeOnClick
								rtl={false}
								pauseOnFocusLoss
								draggable
								pauseOnHover
								theme="colored"
								className="morphio-toast-container"
							/>
						</AuthProvider>
					</ThemeProvider>
				</QueryProvider>
			</body>
		</html>
	);
}
