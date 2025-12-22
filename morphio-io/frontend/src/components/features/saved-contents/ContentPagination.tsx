import type React from "react";

interface ContentPaginationProps {
	currentPage: number;
	totalPages?: number;
	onPageChange: (page: number) => void;
}

const ContentPagination: React.FC<ContentPaginationProps> = ({
	currentPage,
	totalPages = 1,
	onPageChange,
}) => {
	// Don't render pagination if there's only one page
	if (totalPages <= 1) {
		return null;
	}

	// Create page number buttons with ellipsis for large page counts
	const getPageNumbers = () => {
		const pageNumbers: (number | string)[] = [];
		const maxPagesToShow = 5;

		if (totalPages <= maxPagesToShow) {
			// Show all pages if total is small
			for (let i = 1; i <= totalPages; i++) {
				pageNumbers.push(i);
			}
		} else {
			// Always show first page
			pageNumbers.push(1);

			// Calculate range around current page
			const leftBound = Math.max(2, currentPage - 1);
			const rightBound = Math.min(totalPages - 1, currentPage + 1);

			// Add ellipsis if needed on left side
			if (leftBound > 2) {
				pageNumbers.push("...");
			}

			// Add pages around current page
			for (let i = leftBound; i <= rightBound; i++) {
				pageNumbers.push(i);
			}

			// Add ellipsis if needed on right side
			if (rightBound < totalPages - 1) {
				pageNumbers.push("...");
			}

			// Always show last page
			pageNumbers.push(totalPages);
		}

		return pageNumbers;
	};

	return (
		<div className="flex justify-center items-center space-x-2 mt-6">
			<button
				type="button"
				onClick={() => onPageChange(currentPage - 1)}
				disabled={currentPage === 1}
				className={`morphio-icon-button px-3 py-1 border ${
					currentPage === 1 ? "opacity-50 cursor-not-allowed" : ""
				} border-gray-200 dark:border-gray-700`}
			>
				Previous
			</button>

			{getPageNumbers().map((page, index) => {
				if (typeof page === "string") {
					// Render ellipsis
					return (
						<span
							key={`ellipsis-${page === "..." ? "left" : "right"}-${index}`}
							className="morphio-body-sm px-3 py-1 text-gray-500 dark:text-gray-400"
						>
							{page}
						</span>
					);
				}

				// Render page number
				return (
					<button
						type="button"
						key={page}
						onClick={() => onPageChange(page)}
						className={`morphio-icon-button px-3 py-1 ${
							currentPage === page
								? "bg-blue-500 text-white dark:bg-blue-600"
								: ""
						} border border-gray-200 dark:border-gray-700`}
					>
						{page}
					</button>
				);
			})}

			<button
				type="button"
				onClick={() => onPageChange(currentPage + 1)}
				disabled={currentPage === totalPages}
				className={`morphio-icon-button px-3 py-1 border ${
					currentPage === totalPages ? "opacity-50 cursor-not-allowed" : ""
				} border-gray-200 dark:border-gray-700`}
			>
				Next
			</button>
		</div>
	);
};

export default ContentPagination;
