import { Component, type ErrorInfo, type ReactNode } from "react";
import logger from "@/lib/logger";

interface ErrorBoundaryProps {
	children: ReactNode;
	fallback?: ReactNode;
}

class ErrorBoundary extends Component<
	ErrorBoundaryProps,
	{ hasError: boolean }
> {
	state = { hasError: false };

	static getDerivedStateFromError() {
		return { hasError: true };
	}

	componentDidCatch(error: Error, errorInfo: ErrorInfo) {
		logger.error("Uncaught error:", { error, errorInfo });
	}

	resetError = () => this.setState({ hasError: false });

	render() {
		if (this.state.hasError) {
			return (
				this.props.fallback || (
					<div className="morphio-card p-8 flex flex-col items-center justify-center text-center">
						<h1 className="morphio-h2 mb-4">Sorry... there was an error</h1>
						<p className="morphio-body mb-6">
							Something went wrong. Please try again or contact support if the
							issue persists.
						</p>
						<button
							type="button"
							onClick={this.resetError}
							className="morphio-button"
						>
							Try again
						</button>
					</div>
				)
			);
		}

		return this.props.children;
	}
}

export default ErrorBoundary;
