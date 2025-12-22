import type React from "react";
import { useEffect, useState } from "react";
import { FaCheck, FaTimes } from "react-icons/fa";

interface TitleEditorProps {
	contentId: number;
	currentTitle: string;
	onSave: (id: number, newTitle: string) => Promise<void>;
	onCancel: () => void;
}

const TitleEditor: React.FC<TitleEditorProps> = ({
	contentId,
	currentTitle,
	onSave,
	onCancel,
}) => {
	const [newTitle, setNewTitle] = useState("");
	const [isSaving, setIsSaving] = useState(false);

	useEffect(() => {
		setNewTitle(currentTitle);
	}, [currentTitle]);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		if (newTitle.trim() === "") return;

		setIsSaving(true);
		try {
			await onSave(contentId, newTitle);
		} catch {
			// Error handling is done in parent component
		} finally {
			setIsSaving(false);
		}
	};

	return (
		<div className="p-4 border-t border-gray-100 dark:border-gray-700">
			<form onSubmit={handleSubmit} className="flex flex-col space-y-2">
				<div className="morphio-caption font-medium mb-1">Edit Title</div>
				<input
					type="text"
					value={newTitle}
					onChange={(e) => setNewTitle(e.target.value)}
					className="morphio-input w-full"
					placeholder="Enter a new title"
					disabled={isSaving}
				/>
				<div className="flex justify-end space-x-2">
					<button
						type="button"
						onClick={onCancel}
						className="morphio-icon-button inline-flex items-center px-3 py-1.5 border border-gray-300 dark:border-gray-700"
						disabled={isSaving}
					>
						<FaTimes className="mr-1.5" />
						Cancel
					</button>
					<button
						type="submit"
						className="morphio-button inline-flex items-center px-3 py-1.5"
						disabled={isSaving || newTitle.trim() === ""}
					>
						<FaCheck className="mr-1.5" />
						{isSaving ? "Saving..." : "Save"}
					</button>
				</div>
			</form>
		</div>
	);
};

export default TitleEditor;
