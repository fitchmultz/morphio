import type { FC } from "react";
import { FaEnvelope } from "react-icons/fa";
import { changeEmail } from "@/client/sdk.gen";
import { InputField, SubmitButton } from "@/components/common/FormFields";
import { FormWrapper } from "@/components/common/FormWrapper";
import { emailValidation } from "@/utils/validation";

interface ChangeEmailFormData {
	email: string;
}

interface ChangeEmailFormProps {
	currentEmail?: string;
	onUpdate: (newEmail: string) => void;
}

export const ChangeEmailForm: FC<ChangeEmailFormProps> = ({
	currentEmail,
	onUpdate,
}) => {
	const handleSubmit = async (data: ChangeEmailFormData) => {
		const response = await changeEmail({
			body: { email: data.email },
		});
		if (response.data) {
			onUpdate(response.data.email);
		} else {
			const errorMessage =
				response.error &&
				typeof response.error === "object" &&
				"message" in response.error
					? String(response.error.message)
					: "Failed to update email";
			throw new Error(errorMessage);
		}
	};

	return (
		<>
			{currentEmail && (
				<p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
					Current email: {currentEmail}
				</p>
			)}
			<FormWrapper<ChangeEmailFormData>
				onSubmit={handleSubmit}
				formId="change-email-form"
				successMessage="Email updated successfully."
			>
				{({ register, formState: { errors, isSubmitting } }) => (
					<>
						<InputField<ChangeEmailFormData>
							id="new-email"
							name="email"
							label="New Email"
							type="email"
							placeholder="Enter your new email"
							register={register}
							validation={emailValidation}
							error={errors.email}
							icon={<FaEnvelope className="h-5 w-5" />}
							autoComplete="email"
						/>
						<SubmitButton
							isSubmitting={isSubmitting}
							label="Update Email"
							submittingLabel="Updating..."
						/>
					</>
				)}
			</FormWrapper>
		</>
	);
};
