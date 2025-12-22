import type React from "react";
import { useEffect, useState } from "react";
import { FaSearch, FaTimes } from "react-icons/fa";

interface ContentSearchBarProps {
	searchTerm: string;
	onSearchChange: (term: string) => void;
}

const ContentSearchBar: React.FC<ContentSearchBarProps> = ({
	searchTerm,
	onSearchChange,
}) => {
	const [localSearchTerm, setLocalSearchTerm] = useState(searchTerm);

	useEffect(() => {
		setLocalSearchTerm(searchTerm);
	}, [searchTerm]);

	const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		setLocalSearchTerm(e.target.value);
		onSearchChange(e.target.value);
	};

	const clearSearch = () => {
		setLocalSearchTerm("");
		onSearchChange("");
	};

	return (
		<div className="relative mb-6">
			<div className="flex items-center border border-gray-300 dark:border-gray-700 rounded-lg overflow-hidden bg-white dark:bg-gray-800">
				<div className="pl-3 text-gray-400 dark:text-gray-500">
					<FaSearch />
				</div>
				<input
					type="text"
					value={localSearchTerm}
					onChange={handleSearchChange}
					placeholder="Search saved content..."
					className="w-full px-3 py-2 bg-transparent focus:outline-none morphio-body"
				/>
				{localSearchTerm && (
					<button
						type="button"
						onClick={clearSearch}
						className="pr-3 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 morphio-icon-button bg-transparent"
						aria-label="Clear search"
					>
						<FaTimes />
					</button>
				)}
			</div>
		</div>
	);
};

export default ContentSearchBar;
