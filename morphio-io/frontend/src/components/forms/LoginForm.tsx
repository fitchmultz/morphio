import type { FC } from "react";
import { FaEnvelope, FaLock } from "react-icons/fa";
import { InputField, SubmitButton } from "@/components/common/FormFields";
import { FormWrapper } from "@/components/common/FormWrapper";
import { useAuth } from "@/contexts/AuthContext";
import { login as apiLogin } from "@/lib/auth";
import logger from "@/lib/logger";
import { emailValidation } from "@/utils/validation";

interface LoginFormData {
	email: string;
	password: string;
}

export const LoginForm: FC = () => {
	const { login } = useAuth();

	const handleSubmit = async (data: LoginFormData) => {
		const startTime = performance.now();
		// Avoid logging user email directly for security
		logger.info("Login attempt");

		try {
			const response = await apiLogin(data.email, data.password);
			if (response.access_token && response.user) {
				login(response.access_token, response.user);
				// Note: FormWrapper handles success toast, so we don't call notifySuccess here
				logger.info("Login successful");
			} else {
				throw new Error("Invalid credentials");
			}
		} catch (error) {
			const errorMessage =
				error instanceof Error && error.message === "Failed to fetch"
					? "Network error. Please check your connection and try again."
					: "An error occurred during login. Please try again.";

			// Throw to let FormWrapper handle the error display
			logger.error("Login error", {
				error: error instanceof Error ? error.message : String(error),
			});
			throw new Error(errorMessage);
		} finally {
			logger.performance(
				"Login attempt duration",
				performance.now() - startTime,
			);
		}
	};

	return (
		<FormWrapper<LoginFormData>
			onSubmit={handleSubmit}
			formId="login-form"
			successMessage="Login successful!"
		>
			{({ register, formState: { errors, isSubmitting } }) => (
				<>
					<InputField<LoginFormData>
						id="login-email"
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
					<InputField<LoginFormData>
						id="login-password"
						name="password"
						label="Password"
						type="password"
						placeholder="Enter your password"
						register={register}
						validation={{ required: "Password is required." }}
						error={errors.password}
						icon={<FaLock className="h-5 w-5" />}
						autoComplete="current-password"
					/>
					<SubmitButton
						isSubmitting={isSubmitting}
						label="Login"
						submittingLabel="Logging in..."
						className="morphio-button w-full"
					/>
				</>
			)}
		</FormWrapper>
	);
};
