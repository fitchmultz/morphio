export const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
export const PASSWORD_REGEX =
	/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<>])[A-Za-z\d!@#$%^&*(),.?":{}|<>]{8,}$/;

export const isValidEmail = (email: string): boolean => {
	return EMAIL_REGEX.test(email);
};

export const isValidPassword = (password: string): boolean => {
	return PASSWORD_REGEX.test(password);
};

export const isValidUsername = (username: string): boolean => {
	return username.length >= 3 && username.length <= 30;
};

export const isValidFileSize = (fileSize: number, maxSize: number): boolean => {
	return fileSize <= maxSize;
};

export const isValidFileType = (
	fileType: string,
	allowedTypes: readonly string[],
): boolean => {
	return allowedTypes.includes(fileType);
};

// Form validation schemas for react-hook-form
export const emailValidation = {
	required: "Email is required.",
	pattern: {
		value: EMAIL_REGEX,
		message: "Invalid email format",
	},
};

export const displayNameValidation = {
	required: "Display name is required.",
	minLength: {
		value: 3,
		message: "Display name must be at least 3 characters long.",
	},
	maxLength: {
		value: 50,
		message: "Display name must not exceed 50 characters.",
	},
};

export const passwordValidation = {
	required: "Password is required.",
	pattern: {
		value: PASSWORD_REGEX,
		message:
			"Password must contain at least 8 characters, including uppercase, lowercase, number, and special character.",
	},
};

export const confirmPasswordValidation = (getPassword: () => string) => ({
	required: "Please confirm your password.",
	validate: (value: string) =>
		value === getPassword() || "The passwords do not match.",
});
