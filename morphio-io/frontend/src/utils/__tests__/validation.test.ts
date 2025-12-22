import {
	confirmPasswordValidation,
	EMAIL_REGEX,
	isValidEmail,
	isValidFileSize,
	isValidFileType,
	isValidPassword,
	isValidUsername,
	PASSWORD_REGEX,
} from "../validation";

describe("Email validation", () => {
	test("EMAIL_REGEX is defined correctly", () => {
		expect(EMAIL_REGEX).toBeDefined();
		expect(EMAIL_REGEX).toBeInstanceOf(RegExp);
	});

	test("isValidEmail returns true for valid emails", () => {
		const validEmails = [
			"test@example.com",
			"user.name@domain.com",
			"user-name@domain.co.uk",
			"user123@domain.io",
		];

		validEmails.forEach((email) => {
			expect(isValidEmail(email)).toBe(true);
		});
	});

	test("isValidEmail returns false for invalid emails", () => {
		const invalidEmails = [
			"",
			"plaintext",
			"@domain.com",
			"user@",
			"user@domain",
			"user@.com",
			"user name@domain.com",
		];

		invalidEmails.forEach((email) => {
			expect(isValidEmail(email)).toBe(false);
		});
	});
});

describe("Password validation", () => {
	test("PASSWORD_REGEX is defined correctly", () => {
		expect(PASSWORD_REGEX).toBeDefined();
		expect(PASSWORD_REGEX).toBeInstanceOf(RegExp);
	});

	test("isValidPassword returns true for valid passwords", () => {
		const validPasswords = [
			"Password1!",
			"Secure@123",
			"ComplexP@ss1",
			"V3ryStr0ng!",
		];

		validPasswords.forEach((password) => {
			expect(isValidPassword(password)).toBe(true);
		});
	});

	test("isValidPassword returns false for invalid passwords", () => {
		const invalidPasswords = [
			"",
			"short",
			"onlylowercase1!",
			"ONLYUPPERCASE1!",
			"NoSpecialChar123",
			"NoNumbers!",
			"no$pec1als",
		];

		invalidPasswords.forEach((password) => {
			expect(isValidPassword(password)).toBe(false);
		});
	});
});

describe("Username validation", () => {
	test("isValidUsername returns true for valid usernames", () => {
		const validUsernames = [
			"abc",
			"user123",
			"john_doe",
			"a".repeat(30), // max allowed length
		];

		validUsernames.forEach((username) => {
			expect(isValidUsername(username)).toBe(true);
		});
	});

	test("isValidUsername returns false for invalid usernames", () => {
		const invalidUsernames = [
			"",
			"ab", // too short
			"a".repeat(31), // too long
		];

		invalidUsernames.forEach((username) => {
			expect(isValidUsername(username)).toBe(false);
		});
	});
});

describe("File validation", () => {
	test("isValidFileSize returns true when file size is within limit", () => {
		expect(isValidFileSize(1000, 2000)).toBe(true);
		expect(isValidFileSize(2000, 2000)).toBe(true);
	});

	test("isValidFileSize returns false when file size exceeds limit", () => {
		expect(isValidFileSize(2001, 2000)).toBe(false);
	});

	test("isValidFileType returns true for allowed file types", () => {
		const allowedTypes = ["image/jpeg", "image/png", "image/gif"] as const;

		expect(isValidFileType("image/jpeg", allowedTypes)).toBe(true);
		expect(isValidFileType("image/png", allowedTypes)).toBe(true);
	});

	test("isValidFileType returns false for disallowed file types", () => {
		const allowedTypes = ["image/jpeg", "image/png", "image/gif"] as const;

		expect(isValidFileType("application/pdf", allowedTypes)).toBe(false);
		expect(isValidFileType("text/plain", allowedTypes)).toBe(false);
	});
});

describe("confirmPasswordValidation", () => {
	test("returns validation function that checks password match", () => {
		const mockGetPassword = jest.fn().mockReturnValue("Password1!");
		const validator = confirmPasswordValidation(mockGetPassword);

		expect(validator.required).toBe("Please confirm your password.");
		expect(validator.validate("Password1!")).toBe(true);
		expect(validator.validate("DifferentPass1!")).toBe(
			"The passwords do not match.",
		);
		expect(mockGetPassword).toHaveBeenCalled();
	});
});
