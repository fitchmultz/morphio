import type React from "react";
import { FaExclamationTriangle } from "react-icons/fa";
import Modal from "@/components/common/Modal";

interface DeleteConfirmationModalProps {
	isOpen: boolean;
	contentTitle: string;
	onClose: () => void;
	onConfirm: () => Promise<void>;
	isDeleting: boolean;
}

const DeleteConfirmationModal: React.FC<DeleteConfirmationModalProps> = ({
	isOpen,
	contentTitle,
	onClose,
	onConfirm,
	isDeleting,
}) => {
	const handleConfirmClick = async () => {
		await onConfirm();
	};

	return (
		<Modal isOpen={isOpen} onClose={onClose} title="Delete Content">
			<div className="p-6">
				<div className="flex items-center gap-3 mb-4">
					<div className="flex-shrink-0 text-amber-500 dark:text-amber-400">
						<FaExclamationTriangle size={24} />
					</div>
					<h3 className="morphio-h3">Delete Content</h3>
				</div>

				<div className="mt-2">
					<p className="morphio-body">
						Are you sure you want to delete{" "}
						<span className="font-semibold">{contentTitle}</span>?
					</p>
					<p className="mt-2 morphio-body-sm text-gray-500 dark:text-gray-400">
						This action cannot be undone.
					</p>
				</div>

				<div className="mt-6 flex justify-end gap-3">
					<button
						type="button"
						className="morphio-button-secondary px-4 py-2"
						onClick={onClose}
						disabled={isDeleting}
					>
						Cancel
					</button>
					<button
						type="button"
						className="morphio-button bg-red-600 hover:bg-red-700 px-4 py-2 disabled:opacity-50 disabled:cursor-not-allowed"
						onClick={handleConfirmClick}
						disabled={isDeleting}
					>
						{isDeleting ? "Deleting..." : "Delete"}
					</button>
				</div>
			</div>
		</Modal>
	);
};

export default DeleteConfirmationModal;
