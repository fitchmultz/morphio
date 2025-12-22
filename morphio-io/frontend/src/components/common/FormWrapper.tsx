import type { FC, ReactNode } from "react";
import {
	type FieldValues,
	type UseFormProps,
	type UseFormReturn,
	useForm,
} from "react-hook-form";
import logger from "@/lib/logger";
import { notifyError, notifySuccess } from "@/lib/toast";

export interface FormWrapperProps<T extends FieldValues> {
	onSubmit: (data: T) => Promise<void>;
	formConfig?: UseFormProps<T>;
	children: (methods: UseFormReturn<T>) => ReactNode;
	successMessage?: string;
	className?: string;
	formId?: string;
}

export const FormWrapper = <T extends FieldValues>({
	onSubmit,
	formConfig,
	children,
	successMessage = "Operation completed successfully.",
	className = "space-y-6",
	formId,
}: FormWrapperProps<T>): ReturnType<FC> => {
	const methods = useForm<T>({
		mode: "onBlur",
		reValidateMode: "onChange",
		...formConfig,
	});
	const { handleSubmit } = methods;

	const handleFormSubmit = async (data: T) => {
		const startTime = performance.now();
		try {
			await onSubmit(data);
			notifySuccess(successMessage);
			methods.reset();
		} catch (error) {
			logger.error("Form submission error", {
				error: error instanceof Error ? error.message : String(error),
				formId,
			});
			notifyError(
				error instanceof Error
					? error.message
					: "An error occurred during submission.",
			);
		} finally {
			logger.performance(
				`Form submission - ${formId || "unnamed form"}`,
				performance.now() - startTime,
			);
		}
	};

	return (
		<form
			id={formId}
			onSubmit={handleSubmit(handleFormSubmit)}
			className={className}
			noValidate
		>
			{children(methods)}
		</form>
	);
};
