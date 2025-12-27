import type { FC } from "react";
import { FaUser } from "react-icons/fa";
import { changeDisplayName } from "@/client/sdk.gen";
import { InputField, SubmitButton } from "@/components/common/FormFields";
import { FormWrapper } from "@/components/common/FormWrapper";
import { displayNameValidation } from "@/utils/validation";

interface ChangeDisplayNameFormData {
	display_name: string;
}

interface ChangeDisplayNameFormProps {
	currentDisplayName?: string;
	onUpdate: (newDisplayName: string) => void;
}

export const ChangeDisplayNameForm: FC<ChangeDisplayNameFormProps> = ({
	currentDisplayName,
	onUpdate,
}) => {
	const handleSubmit = async (data: ChangeDisplayNameFormData) => {
		const response = await changeDisplayName({
			body: { display_name: data.display_name },
		});
		const updatedUser = response.data?.data;
		if (updatedUser?.display_name) {
			onUpdate(updatedUser.display_name);
		} else {
			const errorMessage =
				response.error &&
				typeof response.error === "object" &&
				"message" in response.error
					? String(response.error.message)
					: response.data?.message || "Failed to update display name";
			throw new Error(errorMessage);
		}
	};

	return (
		<>
			{currentDisplayName && (
				<p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
					Current display name: {currentDisplayName}
				</p>
			)}
			<FormWrapper<ChangeDisplayNameFormData>
				onSubmit={handleSubmit}
				formId="change-display-name-form"
				successMessage="Display name updated successfully."
			>
				{({ register, formState: { errors, isSubmitting } }) => (
					<>
						<InputField<ChangeDisplayNameFormData>
							id="new-display-name"
							name="display_name"
							label="New Display Name"
							type="text"
							placeholder="Enter your new display name"
							register={register}
							validation={displayNameValidation}
							error={errors.display_name}
							icon={<FaUser className="h-5 w-5" />}
						/>
						<SubmitButton
							isSubmitting={isSubmitting}
							label="Update Display Name"
							submittingLabel="Updating..."
						/>
					</>
				)}
			</FormWrapper>
		</>
	);
};
