import type { FC } from "react";
import { FaEnvelope, FaLock, FaUser } from "react-icons/fa";
import { InputField, SubmitButton } from "@/components/common/FormFields";
import { FormWrapper } from "@/components/common/FormWrapper";
import { useAuth } from "@/contexts/AuthContext";
import { register as apiRegister } from "@/lib/auth";
import {
	confirmPasswordValidation,
	displayNameValidation,
	emailValidation,
	passwordValidation,
} from "@/utils/validation";

interface RegisterFormData {
	email: string;
	password: string;
	confirm_password: string;
	display_name: string;
}

export const RegisterForm: FC = () => {
	const { login } = useAuth();

	const handleSubmit = async (data: RegisterFormData) => {
		const response = await apiRegister(
			data.email,
			data.password,
			data.display_name,
		);
		if (response.access_token && response.user) {
			login(response.access_token, response.user);
		} else {
			throw new Error("Registration failed");
		}
	};

	return (
		<FormWrapper<RegisterFormData>
			onSubmit={handleSubmit}
			formId="register-form"
			successMessage="Registration successful!"
		>
			{({ register, watch, formState: { errors, isSubmitting } }) => {
				const password = watch("password");
				return (
					<>
						<InputField<RegisterFormData>
							id="register-email"
							name="email"
							label="Email"
							type="email"
							placeholder="Enter your email"
							register={register}
							validation={emailValidation}
							error={errors.email}
							icon={<FaEnvelope className="h-5 w-5" />}
							autoComplete="email"
						/>
						<InputField<RegisterFormData>
							id="register-display-name"
							name="display_name"
							label="Display Name"
							type="text"
							placeholder="Choose a display name"
							register={register}
							validation={displayNameValidation}
							error={errors.display_name}
							icon={<FaUser className="h-5 w-5" />}
						/>
						<InputField<RegisterFormData>
							id="register-password"
							name="password"
							label="Password"
							type="password"
							placeholder="Create a password"
							register={register}
							validation={passwordValidation}
							error={errors.password}
							icon={<FaLock className="h-5 w-5" />}
							autoComplete="new-password"
						/>
						<InputField<RegisterFormData>
							id="register-confirm-password"
							name="confirm_password"
							label="Confirm Password"
							type="password"
							placeholder="Confirm your password"
							register={register}
							validation={confirmPasswordValidation(() => password)}
							error={errors.confirm_password}
							icon={<FaLock className="h-5 w-5" />}
							autoComplete="new-password"
						/>
						<SubmitButton
							isSubmitting={isSubmitting}
							label="Register"
							submittingLabel="Registering..."
						/>
					</>
				);
			}}
		</FormWrapper>
	);
};
