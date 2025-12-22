import type React from "react";

interface FormProgressProps {
	isLoading: boolean;
	progress?: number;
	statusMessage?: string;
	error?: string | null;
}

const FormProgress: React.FC<FormProgressProps> = ({
	isLoading,
	progress,
	statusMessage,
	error,
}) => {
	if (!isLoading) {
		return null;
	}

	return (
		<div className="mt-4 space-y-4">
			<div className="relative w-full bg-gray-200 dark:bg-gray-700 rounded-full h-4 overflow-hidden">
				<div
					className="absolute top-0 left-0 h-full bg-blue-500 dark:bg-blue-400 transition-all duration-300 ease-out"
					style={{ width: `${progress || 0}%` }}
				></div>
			</div>
			<div className="morphio-body-sm text-center text-gray-600 dark:text-gray-400">
				{statusMessage ? (
					<>
						{statusMessage}
						{typeof progress === "number" && progress > 0 && (
							<span className="ml-2 font-medium">
								({Math.round(progress)}%)
							</span>
						)}
					</>
				) : (
					typeof progress === "number" &&
					progress > 0 && (
						<span className="font-medium">
							{Math.round(progress)}% complete
						</span>
					)
				)}
			</div>
			{error && (
				<div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700/30 text-red-600 dark:text-red-400 p-3 rounded-lg morphio-body-sm">
					{error}
				</div>
			)}
		</div>
	);
};

export default FormProgress;
