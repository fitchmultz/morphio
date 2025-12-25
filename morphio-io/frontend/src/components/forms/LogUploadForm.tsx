import type { FC } from "react";
import { useEffect, useRef, useState } from "react";
import { FaInfoCircle } from "react-icons/fa";
import { generateSplunkConfig, getLogConfig, processLogs } from "@/client";
import { SubmitButton } from "@/components/common/FormFields";
import { FormWrapper } from "@/components/common/FormWrapper";
import FileUpload from "@/components/features/content-generation/FileUpload";
import logger from "@/lib/logger";

const DEFAULT_MAX_UPLOAD_SIZE = 3221225472;

type ProcessType = "logs" | "splunk";

interface LogUploadFormProps {
	onSubmitSuccess?: (jobId: string) => void;
	isSubmitting?: boolean;
	/** Which SDK function to call. Defaults to 'logs' */
	processType?: ProcessType;
}

interface LogUploadFormData {
	logFile: FileList;
	anonymize: boolean;
}

export const LogUploadForm: FC<LogUploadFormProps> = ({
	onSubmitSuccess,
	isSubmitting: externalIsSubmitting,
	processType = "logs",
}) => {
	const [selectedFile, setSelectedFile] = useState<File | null>(null);
	const [allowedExtensions, setAllowedExtensions] = useState<string[]>([
		"log",
		"txt",
		"csv",
		"json",
		"md",
	]);
	const [maxUploadSize, setMaxUploadSize] = useState<number>(
		DEFAULT_MAX_UPLOAD_SIZE,
	);
	const fileInputRef = useRef<HTMLInputElement>(null);

	useEffect(() => {
		// Fetch the allowed extensions from the backend
		const fetchAllowedExtensions = async () => {
			try {
				const { data } = await getLogConfig();
				if (data?.status === "success" && data.data) {
					const configData = data.data as {
						allowed_extensions?: string[];
						max_upload_size?: number;
					};
					if (configData.allowed_extensions) {
						setAllowedExtensions(configData.allowed_extensions);
					}
					if (configData.max_upload_size) {
						setMaxUploadSize(configData.max_upload_size);
					}
				}
			} catch (error: unknown) {
				const msg = error instanceof Error ? error.message : "Unknown error";
				logger.warn("Log config unavailable, using defaults", { error: msg });
				// No user toast - silent fallback to defaults
			}
		};

		fetchAllowedExtensions();
	}, []);

	const handleSubmit = async (formData: LogUploadFormData) => {
		if (!selectedFile) {
			throw new Error("Please select a file");
		}

		const sdkFn = processType === "splunk" ? generateSplunkConfig : processLogs;
		const { data, error } = await sdkFn({
			body: { log_file: selectedFile },
			query: { anonymize: formData.anonymize },
		});

		if (error) {
			throw new Error(error instanceof Error ? error.message : String(error));
		}

		if (data?.status === "success" && data.data?.job_id) {
			onSubmitSuccess?.(data.data.job_id);
			setSelectedFile(null);
			if (fileInputRef.current) {
				fileInputRef.current.value = "";
			}
		} else {
			throw new Error(data?.message || "Failed to process log file");
		}
	};

	const acceptedFileTypes = allowedExtensions.map((ext) => `.${ext}`).join(",");
	const helpText = `Supported file types: Log files (${allowedExtensions.map((ext) => `.${ext}`).join(", ")})`;

	return (
		<FormWrapper<LogUploadFormData>
			onSubmit={handleSubmit}
			formId="log-upload-form"
			formConfig={{ defaultValues: { anonymize: true } }}
			successMessage="Log file uploaded successfully!"
		>
			{({ register, formState: { isSubmitting: formIsSubmitting } }) => {
				const isDisabled = externalIsSubmitting || formIsSubmitting;

				return (
					<>
						<FileUpload
							inputFile={selectedFile}
							setInputFile={setSelectedFile}
							setAutoDetectedType={() => {}} // Not needed for logs
							isLoading={isDisabled}
							hasUrl={false}
							maxUploadSize={maxUploadSize}
							acceptedTypes={acceptedFileTypes}
							helpText={helpText}
						/>

						<div className="flex items-center space-x-2">
							<input
								type="checkbox"
								id="anonymize"
								{...register("anonymize")}
								disabled={isDisabled}
								className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:focus:ring-blue-400"
							/>
							<label htmlFor="anonymize" className="morphio-body-sm">
								Anonymize sensitive data
							</label>
							<span
								title="Removes IP addresses, email addresses, usernames, and other personally identifiable information before processing"
								className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help"
							>
								<FaInfoCircle className="h-4 w-4" />
							</span>
						</div>

						<SubmitButton
							isSubmitting={isDisabled}
							label="Process Log File"
							submittingLabel="Processing..."
							className="morphio-button w-full px-6 py-3.5"
						/>
					</>
				);
			}}
		</FormWrapper>
	);
};
