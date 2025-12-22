import type { FC } from "react";
import { FaLock } from "react-icons/fa";
import { changePassword } from "@/client/sdk.gen";
import { InputField, SubmitButton } from "@/components/common/FormFields";
import { FormWrapper } from "@/components/common/FormWrapper";
import {
	confirmPasswordValidation,
	passwordValidation,
} from "@/utils/validation";

interface ChangePasswordFormData {
	current_password: string;
	new_password: string;
	confirm_new_password: string;
}

export const ChangePasswordForm: FC = () => {
	const handleSubmit = async ({
		current_password,
		new_password,
	}: ChangePasswordFormData) => {
		const response = await changePassword({
			body: { current_password, new_password },
		});
		if (!response.data) {
			const errorMessage =
				response.error &&
				typeof response.error === "object" &&
				"message" in response.error
					? String(response.error.message)
					: "Failed to update password";
			throw new Error(errorMessage);
		}
	};

	return (
		<FormWrapper<ChangePasswordFormData>
			onSubmit={handleSubmit}
			formId="change-password-form"
			successMessage="Password updated successfully."
		>
			{({ register, watch, formState: { errors, isSubmitting } }) => {
				const newPassword = watch("new_password");
				return (
					<>
						<InputField<ChangePasswordFormData>
							id="current-password"
							name="current_password"
							label="Current Password"
							type="password"
							placeholder="Enter your current password"
							register={register}
							validation={{ required: "Current password is required." }}
							error={errors.current_password}
							icon={<FaLock className="h-5 w-5" />}
							autoComplete="current-password"
						/>
						<InputField<ChangePasswordFormData>
							id="new-password"
							name="new_password"
							label="New Password"
							type="password"
							placeholder="Enter your new password"
							register={register}
							validation={passwordValidation}
							error={errors.new_password}
							icon={<FaLock className="h-5 w-5" />}
							autoComplete="new-password"
						/>
						<InputField<ChangePasswordFormData>
							id="confirm-new-password"
							name="confirm_new_password"
							label="Confirm New Password"
							type="password"
							placeholder="Confirm your new password"
							register={register}
							validation={confirmPasswordValidation(() => newPassword)}
							error={errors.confirm_new_password}
							icon={<FaLock className="h-5 w-5" />}
							autoComplete="new-password"
						/>
						<SubmitButton
							isSubmitting={isSubmitting}
							label="Change Password"
							submittingLabel="Changing Password..."
							className="morphio-button"
						/>
					</>
				);
			}}
		</FormWrapper>
	);
};
