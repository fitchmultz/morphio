import type { FC, ReactNode } from "react";
import type {
	FieldError,
	FieldValues,
	Path,
	UseFormRegister,
} from "react-hook-form";

interface FormFieldProps {
	id: string;
	label: string;
	error?: FieldError;
	children: ReactNode;
	className?: string;
}

export const FormField: FC<FormFieldProps> = ({
	id,
	label,
	error,
	children,
	className = "",
}) => {
	const errorId = error ? `${id}-error` : undefined;
	return (
		<div className={`space-y-2 ${className}`}>
			<label htmlFor={id} className="morphio-caption block font-medium">
				{label}
			</label>
			{children}
			{error && (
				<p
					id={errorId}
					className="morphio-caption text-red-600 dark:text-red-400"
					role="alert"
				>
					{error.message}
				</p>
			)}
		</div>
	);
};

interface InputFieldProps<T extends FieldValues> {
	id: string;
	name: Path<T>;
	label: string;
	type?: string;
	placeholder?: string;
	register: UseFormRegister<T>;
	error?: FieldError;
	validation?: object;
	icon?: ReactNode;
	autoComplete?: string;
	className?: string;
}

export const InputField = <T extends FieldValues>({
	id,
	name,
	label,
	type = "text",
	placeholder,
	register,
	error,
	validation = {},
	icon,
	autoComplete,
	className = "",
}: InputFieldProps<T>) => {
	const errorId = error ? `${id}-error` : undefined;
	return (
		<FormField id={id} label={label} error={error} className={className}>
			<div className="relative">
				{icon && (
					<div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-gray-400 dark:text-gray-500 z-10">
						{icon}
					</div>
				)}
				<input
					id={id}
					type={type}
					{...register(name, validation)}
					placeholder={placeholder}
					autoComplete={autoComplete}
					aria-invalid={error ? "true" : undefined}
					aria-describedby={errorId}
					className={`morphio-input ${icon ? "pl-12" : ""}`}
				/>
			</div>
		</FormField>
	);
};

interface SubmitButtonProps {
	isSubmitting: boolean;
	label: string;
	submittingLabel?: string;
	className?: string;
}

export const SubmitButton: FC<SubmitButtonProps> = ({
	isSubmitting,
	label,
	submittingLabel,
	className = "",
}) => (
	<button
		type="submit"
		disabled={isSubmitting}
		className={`morphio-button w-full flex justify-center items-center disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
		aria-busy={isSubmitting}
	>
		{isSubmitting ? (
			<div className="flex items-center justify-center gap-2">
				<div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
				<span>{submittingLabel || `${label}...`}</span>
			</div>
		) : (
			label
		)}
	</button>
);
