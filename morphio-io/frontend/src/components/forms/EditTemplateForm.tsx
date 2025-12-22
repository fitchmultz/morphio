"use client";

import type { FC } from "react";
import { updateTemplate } from "@/client/sdk.gen";
import type { TemplateOut } from "@/client/types.gen";
import { TemplateForm } from "./TemplateForm";

interface EditTemplateFormProps {
	template: TemplateOut;
	onSuccess?: (template: TemplateOut) => void;
}

export const EditTemplateForm: FC<EditTemplateFormProps> = ({
	template,
	onSuccess,
}) => {
	const handleSubmit = async (data: {
		name: string;
		template_content: string;
	}) => {
		const response = await updateTemplate({
			path: {
				template_id: template.id,
			},
			body: {
				name: data.name,
				template_content: data.template_content,
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
					: response.data?.message || "Failed to update template";
			throw new Error(errorMessage);
		}
	};

	return (
		<TemplateForm
			initialData={template}
			onSubmit={handleSubmit}
			submitButtonText="Update Template"
		/>
	);
};
