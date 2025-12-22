import type { FC } from "react";
import { FaFileAlt } from "react-icons/fa";
import { saveTemplate } from "@/client/sdk.gen";
import { InputField, SubmitButton } from "@/components/common/FormFields";
import { FormWrapper } from "@/components/common/FormWrapper";

interface SaveTemplateFormData {
	name: string;
}

interface SaveTemplateFormProps {
	template: string;
	onSuccess?: () => void;
}

export const SaveTemplateForm: FC<SaveTemplateFormProps> = ({
	template,
	onSuccess,
}) => {
	const handleSubmit = async (data: SaveTemplateFormData) => {
		const response = await saveTemplate({
			body: {
				name: data.name,
				template_content: template,
				is_default: false,
			},
		});

		if (response.data?.status !== "success") {
			const errorMessage =
				response.error &&
				typeof response.error === "object" &&
				"message" in response.error
					? String(response.error.message)
					: response.data?.message || "Failed to save template";
			throw new Error(errorMessage);
		}

		onSuccess?.();
	};

	return (
		<FormWrapper<SaveTemplateFormData>
			onSubmit={handleSubmit}
			formId="save-template-form"
			successMessage="Template saved successfully!"
		>
			{({ register, formState: { errors, isSubmitting } }) => (
				<>
					<InputField<SaveTemplateFormData>
						id="template-name"
						name="name"
						label="Template Name"
						type="text"
						placeholder="Enter template name"
						register={register}
						validation={{ required: "Template name is required." }}
						error={errors.name}
						icon={<FaFileAlt className="h-5 w-5" />}
					/>
					<SubmitButton
						isSubmitting={isSubmitting}
						label="Save Template"
						submittingLabel="Saving..."
					/>
				</>
			)}
		</FormWrapper>
	);
};
