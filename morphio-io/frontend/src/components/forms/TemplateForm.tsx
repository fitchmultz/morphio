import type { FC } from "react";
import { FaAlignLeft, FaFileAlt } from "react-icons/fa";
import { InputField, SubmitButton } from "@/components/common/FormFields";
import { FormWrapper } from "@/components/common/FormWrapper";

interface TemplateFormData {
	name: string;
	template_content: string;
}

interface TemplateFormProps {
	initialData?: Partial<TemplateFormData>;
	onSubmit: (data: TemplateFormData) => Promise<void>;
	submitButtonText: string;
}

export const TemplateForm: FC<TemplateFormProps> = ({
	initialData,
	onSubmit,
	submitButtonText,
}) => {
	return (
		<FormWrapper<TemplateFormData>
			onSubmit={onSubmit}
			formId="template-form"
			formConfig={{ defaultValues: initialData }}
		>
			{({ register, formState: { errors, isSubmitting } }) => (
				<>
					<InputField<TemplateFormData>
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
					<div className="space-y-2">
						<label
							htmlFor="template-content"
							className="morphio-caption block font-medium"
						>
							Template Content
						</label>
						<div className="relative">
							<div className="absolute inset-y-0 left-0 pl-4 pt-4 pointer-events-none text-gray-400 dark:text-gray-500">
								<FaAlignLeft className="h-5 w-5" />
							</div>
							<textarea
								id="template-content"
								{...register("template_content", {
									required: "Template content is required.",
								})}
								placeholder="Enter template content. Include {transcript} where you want the video transcript to appear."
								className="morphio-input pl-12"
								rows={6}
							/>
							{errors.template_content && (
								<p
									className="morphio-caption text-red-600 dark:text-red-400"
									role="alert"
								>
									{errors.template_content.message}
								</p>
							)}
						</div>
					</div>
					<p className="morphio-body-sm text-gray-600 dark:text-gray-400">
						Note: Your template must include the {"{transcript}"} placeholder.
					</p>
					<SubmitButton
						isSubmitting={isSubmitting}
						label={submitButtonText}
						submittingLabel="Submitting..."
					/>
				</>
			)}
		</FormWrapper>
	);
};
