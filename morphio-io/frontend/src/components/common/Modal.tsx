import type React from "react";
import { useCallback, useEffect, useRef } from "react";
import { createPortal } from "react-dom";

interface ModalProps {
	isOpen: boolean;
	onClose: () => void;
	title: string;
	children: React.ReactNode;
	size?: "sm" | "md" | "lg" | "xl";
}

const Modal: React.FC<ModalProps> = ({
	isOpen,
	onClose,
	title,
	children,
	size = "md",
}) => {
	const modalRef = useRef<HTMLDivElement>(null);
	const previousActiveElement = useRef<Element | null>(null);

	// Handle ESC key to close modal
	const handleKeyDown = useCallback(
		(event: KeyboardEvent) => {
			if (event.key === "Escape") {
				onClose();
			}
		},
		[onClose],
	);

	useEffect(() => {
		if (isOpen) {
			// Store the currently focused element to restore later
			previousActiveElement.current = document.activeElement;

			document.body.style.overflow = "hidden";
			document.addEventListener("keydown", handleKeyDown);

			// Focus the modal container for accessibility
			setTimeout(() => {
				modalRef.current?.focus();
			}, 0);
		} else {
			document.body.style.overflow = "unset";
			document.removeEventListener("keydown", handleKeyDown);

			// Restore focus to the previously focused element
			if (previousActiveElement.current instanceof HTMLElement) {
				previousActiveElement.current.focus();
			}
		}
		return () => {
			document.body.style.overflow = "unset";
			document.removeEventListener("keydown", handleKeyDown);
		};
	}, [isOpen, handleKeyDown]);

	if (!isOpen) return null;

	const sizeClasses = {
		sm: "max-w-sm",
		md: "max-w-md",
		lg: "max-w-lg",
		xl: "max-w-xl",
	};

	const modalContent = (
		<div
			className="fixed inset-0 flex items-center justify-center"
			style={{ zIndex: 9999 }}
		>
			{/* Backdrop */}
			<div
				className="fixed inset-0 bg-black/50 backdrop-blur-sm"
				onClick={onClose}
				aria-hidden="true"
			/>

			{/* Modal Container */}
			<div
				ref={modalRef}
				tabIndex={-1}
				className={`${sizeClasses[size]} w-full mx-auto p-4 relative z-50 max-h-screen flex`}
				role="dialog"
				aria-modal="true"
				aria-labelledby="modal-title"
			>
				{/* Modal Content Wrapper */}
				<div className="morphio-modal w-full flex flex-col max-h-[calc(100vh-2rem)]">
					{/* Fixed Header */}
					<header className="morphio-modal-header flex justify-between items-center">
						<h2 id="modal-title" className="morphio-h4">
							{title}
						</h2>
						<button
							type="button"
							onClick={onClose}
							className="morphio-icon-button"
							aria-label="Close modal"
						>
							<svg
								className="h-5 w-5"
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
								aria-hidden="true"
							>
								<path
									strokeLinecap="round"
									strokeLinejoin="round"
									strokeWidth={2}
									d="M6 18L18 6M6 6l12 12"
								/>
							</svg>
						</button>
					</header>

					{/* Scrollable Content */}
					<div className="flex-1 overflow-y-auto p-6 min-h-0 morphio-body">
						{children}
					</div>
				</div>
			</div>
		</div>
	);

	return createPortal(modalContent, document.body);
};

export default Modal;
