import {
	FaCheck,
	FaExclamation,
	FaExclamationCircle,
	FaInfoCircle,
} from "react-icons/fa";
import { type ToastOptions, type TypeOptions, toast } from "react-toastify";
import logger from "./logger";

// Custom toast component with improved styling
const CustomToast = ({
	message,
	type,
}: {
	message: string;
	type: TypeOptions;
}) => {
	const icons = {
		success: <FaCheck className="text-green-500 dark:text-green-400" />,
		error: <FaExclamationCircle className="text-red-500 dark:text-red-400" />,
		info: <FaInfoCircle className="text-blue-500 dark:text-blue-400" />,
		warning: <FaExclamation className="text-yellow-500 dark:text-yellow-400" />,
		default: <FaInfoCircle className="text-blue-500 dark:text-blue-400" />,
	};

	const icon = icons[type] || icons.default;

	return (
		<div data-testid="morphio-toast" className="flex items-center gap-3">
			<div className="flex-shrink-0">{icon}</div>
			<p className="text-sm font-medium text-gray-800 dark:text-gray-200">
				{message}
			</p>
		</div>
	);
};

const DEFAULT_TOAST_OPTIONS: ToastOptions = {
	position: "top-right",
	autoClose: 3000,
	hideProgressBar: false,
	closeOnClick: true,
	pauseOnHover: true,
	draggable: true,
	progress: undefined,
	className: "morphio-toast",
	// Theme inherited from ToastContainer in layout.tsx
};

type ToastType = "success" | "error" | "info" | "warning";

// Rate limiting for error toasts
const ERROR_TOAST_COOLDOWN = 3000; // 3 seconds
// Use a Record to track when each error message was last shown
const lastErrorToasts: Record<string, number> = {};

const createToastNotification =
	(type: ToastType) => (message: string, options?: ToastOptions) => {
		logger[type === "error" ? "error" : "info"](
			"Toast notification displayed",
			{ type, message },
		);

		// Apply rate limiting only for error toasts
		if (type === "error") {
			const now = Date.now();

			// Check if this exact message was shown recently
			if (
				lastErrorToasts[message] &&
				now - lastErrorToasts[message] < ERROR_TOAST_COOLDOWN
			) {
				logger.info("Error toast rate limited", { message });
				return; // Skip showing this toast
			}

			// Update the last time this message was shown
			lastErrorToasts[message] = now;

			// Clean up old messages from the cache after 1 minute
			setTimeout(() => {
				delete lastErrorToasts[message];
			}, 60000);
		}

		toast[type](<CustomToast message={message} type={type} />, {
			...DEFAULT_TOAST_OPTIONS,
			...options,
		});
	};

export const notifySuccess = createToastNotification("success");
export const notifyError = createToastNotification("error");
export const notifyInfo = createToastNotification("info");
export const notifyWarning = createToastNotification("warning");

export const measureToastPerformance = (
	toastFunction: (message: string, options?: ToastOptions) => void,
	message: string,
	options?: ToastOptions,
) => {
	const start = performance.now();
	toastFunction(message, options);
	const end = performance.now();
	logger.performance("Toast display", end - start);
};
