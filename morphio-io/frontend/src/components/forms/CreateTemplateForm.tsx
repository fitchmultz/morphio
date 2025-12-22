"use client";

import type { FC } from "react";
import { saveTemplate } from "@/client/sdk.gen";
import type { TemplateOut } from "@/client/types.gen";
import { TemplateForm } from "./TemplateForm";

interface CreateTemplateFormProps {
	onSuccess?: (template: TemplateOut) => void;
}

export const CreateTemplateForm: FC<CreateTemplateFormProps> = ({
	onSuccess,
}) => {
	const handleSubmit = async (data: {
		name: string;
		template_content: string;
	}) => {
		const response = await saveTemplate({
			body: {
				name: data.name,
				template_content: data.template_content,
				is_default: false,
			},
		});
		if (response.data?.status === "success" && response.data.data) {
			onSuccess?.(response.data.data);
		} else {
			const errorMessage =
				response.error &&
				typeof response.error === "object" &&
				"message" in response.error
					? String(response.error.message)
					: response.data?.message || "Failed to create template";
			throw new Error(errorMessage);
		}
	};

	return (
		<TemplateForm onSubmit={handleSubmit} submitButtonText="Create Template" />
	);
};
