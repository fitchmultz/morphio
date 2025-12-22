"use client";

import Link from "next/link";
import type React from "react";
import { FaBolt, FaMagic, FaRocket } from "react-icons/fa";

const LandingPage: React.FC = () => {
	return (
		<div className="min-h-screen bg-linear-to-br from-gray-50 via-blue-50/30 to-purple-50/30 dark:from-gray-900 dark:via-blue-950 dark:to-purple-950">
			{/* Hero Section */}
			<section className="relative py-32 overflow-hidden">
				<div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(120,119,198,0.2),rgba(255,255,255,0))] dark:bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(120,119,198,0.4),rgba(255,255,255,0))]" />
				<div className="max-w-4xl mx-auto px-4 text-center relative">
					<h1 className="morphio-h1 text-7xl mb-8">Welcome to Morphio</h1>
					<p className="morphio-body-lg mb-12 max-w-2xl mx-auto">
						Transform your videos into engaging content with AI-powered
						processing
					</p>
					<div className="flex flex-col sm:flex-row items-center justify-center gap-6">
						<Link
							href="/login"
							className="morphio-button inline-flex items-center gap-3 px-8 py-4 text-lg shadow-xl hover:shadow-2xl bg-linear-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 ring-1 ring-purple-500/20 hover:ring-purple-500/40"
						>
							Get Started
							<FaRocket className="h-5 w-5" />
						</Link>
						<Link
							href="/register"
							className="morphio-button-secondary inline-flex items-center gap-3 px-8 py-4 text-lg bg-white/10 dark:bg-white/5 backdrop-blur-xl shadow-xl hover:shadow-2xl ring-1 ring-white/20 hover:ring-white/40 dark:text-white"
						>
							Create Account
						</Link>
					</div>
				</div>
			</section>

			{/* Features Section */}
			<section className="py-24">
				<div className="max-w-6xl mx-auto px-4">
					<h2 className="morphio-h2 text-center mb-16">Features</h2>
					<div className="grid grid-cols-1 md:grid-cols-3 gap-10">
						<div className="flex flex-col h-full bg-white/10 dark:bg-white/5 backdrop-blur-xl shadow-xl rounded-2xl border border-white/20 dark:border-white/10 p-8 text-center transform transition-all duration-300 hover:-translate-y-2 hover:shadow-2xl group hover:bg-white/20 dark:hover:bg-white/10">
							<div className="flex items-center justify-center mx-auto w-16 h-16 mb-6 rounded-2xl bg-linear-to-br from-blue-500/30 to-purple-500/30 dark:from-blue-500/40 dark:to-purple-500/40 group-hover:scale-110 transition-transform duration-300 ring-1 ring-white/20">
								<FaRocket className="h-8 w-8 text-blue-400 dark:text-blue-300" />
							</div>
							<h3 className="morphio-h4 mb-4">Fast Processing</h3>
							<p className="morphio-body">
								Generate content in minutes, not hours
							</p>
						</div>
						<div className="flex flex-col h-full bg-white/10 dark:bg-white/5 backdrop-blur-xl shadow-xl rounded-2xl border border-white/20 dark:border-white/10 p-8 text-center transform transition-all duration-300 hover:-translate-y-2 hover:shadow-2xl group hover:bg-white/20 dark:hover:bg-white/10">
							<div className="flex items-center justify-center mx-auto w-16 h-16 mb-6 rounded-2xl bg-linear-to-br from-blue-500/30 to-purple-500/30 dark:from-blue-500/40 dark:to-purple-500/40 group-hover:scale-110 transition-transform duration-300 ring-1 ring-white/20">
								<FaMagic className="h-8 w-8 text-purple-400 dark:text-purple-300" />
							</div>
							<h3 className="morphio-h4 mb-4">AI Powered</h3>
							<p className="morphio-body">
								Smart content generation with advanced AI
							</p>
						</div>
						<div className="flex flex-col h-full bg-white/10 dark:bg-white/5 backdrop-blur-xl shadow-xl rounded-2xl border border-white/20 dark:border-white/10 p-8 text-center transform transition-all duration-300 hover:-translate-y-2 hover:shadow-2xl group hover:bg-white/20 dark:hover:bg-white/10">
							<div className="flex items-center justify-center mx-auto w-16 h-16 mb-6 rounded-2xl bg-linear-to-br from-blue-500/30 to-purple-500/30 dark:from-blue-500/40 dark:to-purple-500/40 group-hover:scale-110 transition-transform duration-300 ring-1 ring-white/20">
								<FaBolt className="h-8 w-8 text-yellow-400 dark:text-yellow-300" />
							</div>
							<h3 className="morphio-h4 mb-4">Easy to Use</h3>
							<p className="morphio-body">Simple interface, powerful results</p>
						</div>
					</div>
				</div>
			</section>

			{/* Pricing Section */}
			<section className="py-24 relative">
				<div className="absolute inset-0 bg-linear-to-b from-transparent via-gray-100/30 to-transparent dark:via-gray-800/30" />
				<div className="max-w-6xl mx-auto px-4 relative">
					<h2 className="morphio-h2 text-center mb-16">Pricing Plans</h2>
					<div className="grid grid-cols-1 md:grid-cols-3 gap-10">
						{/* Free Plan */}
						<div className="flex flex-col h-full bg-white/10 dark:bg-white/5 backdrop-blur-xl shadow-xl rounded-2xl border border-white/20 dark:border-white/10 p-10 transform transition-all duration-300 hover:-translate-y-2 hover:shadow-2xl hover:bg-white/20 dark:hover:bg-white/10">
							<h3 className="morphio-h3 mb-4 bg-clip-text text-transparent bg-linear-to-r from-blue-600 to-blue-400">
								Free
							</h3>
							<p className="mb-8 morphio-body">
								For individuals and small projects
							</p>
							<p className="text-5xl font-bold mb-8 text-gray-900 dark:text-white">
								$0
							</p>
							<ul className="mb-10 space-y-4 morphio-body flex-grow">
								<li>Basic processing</li>
								<li>Limited features</li>
								<li>Community support</li>
							</ul>
							<Link
								href="/register"
								className="morphio-button w-full text-lg py-4 bg-linear-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 shadow-xl hover:shadow-2xl ring-1 ring-purple-500/20 hover:ring-purple-500/40"
							>
								Sign Up
							</Link>
						</div>
						{/* Pro Plan */}
						<div className="relative mt-4 md:mt-0">
							<div className="absolute -top-3 left-1/2 -translate-x-1/2 px-6 py-2 bg-linear-to-r from-[#4F46E5] to-[#7C3AED] text-white text-base font-medium rounded-full shadow-lg z-10">
								Popular
							</div>
							<div className="flex flex-col h-full bg-white/10 dark:bg-white/5 backdrop-blur-xl shadow-xl rounded-2xl border-2 border-blue-500/20 dark:border-blue-400/20 p-10 transform transition-all duration-300 hover:-translate-y-2 hover:shadow-2xl hover:bg-white/20 dark:hover:bg-white/10">
								<h3 className="morphio-h3 mb-4 bg-clip-text text-transparent bg-linear-to-r from-purple-600 to-purple-400">
									Pro
								</h3>
								<p className="mb-8 morphio-body">
									For professionals and growing businesses
								</p>
								<p className="text-5xl font-bold mb-8 text-gray-900 dark:text-white">
									$20/mo
								</p>
								<ul className="mb-10 space-y-4 morphio-body flex-grow">
									<li>Advanced processing</li>
									<li>Priority support</li>
									<li>More integrations</li>
								</ul>
								<Link
									href="/register"
									className="morphio-button w-full text-lg py-4 bg-linear-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 shadow-xl hover:shadow-2xl ring-1 ring-purple-500/20 hover:ring-purple-500/40"
								>
									Choose Plan
								</Link>
							</div>
						</div>
						{/* Enterprise Plan */}
						<div className="flex flex-col h-full bg-white/10 dark:bg-white/5 backdrop-blur-xl shadow-xl rounded-2xl border border-white/20 dark:border-white/10 p-10 transform transition-all duration-300 hover:-translate-y-2 hover:shadow-2xl hover:bg-white/20 dark:hover:bg-white/10">
							<h3 className="morphio-h3 mb-4 bg-clip-text text-transparent bg-linear-to-r from-purple-600 to-blue-400">
								Enterprise
							</h3>
							<p className="mb-8 morphio-body">
								Custom solutions for large organizations
							</p>
							<p className="text-5xl font-bold mb-8 text-gray-900 dark:text-white">
								Contact Us
							</p>
							<ul className="mb-10 space-y-4 morphio-body flex-grow">
								<li>Custom integrations</li>
								<li>Dedicated support</li>
								<li>Service level agreements</li>
							</ul>
							<Link
								href="mailto:support@morphio.io"
								className="morphio-button-secondary w-full text-lg py-4 bg-white/10 dark:bg-white/5 backdrop-blur-xl shadow-xl hover:shadow-2xl ring-1 ring-white/20 hover:ring-white/40 dark:text-white"
							>
								Get in Touch
							</Link>
						</div>
					</div>
				</div>
			</section>
		</div>
	);
};

export default LandingPage;
