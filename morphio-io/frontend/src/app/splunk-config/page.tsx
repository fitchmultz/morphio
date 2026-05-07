import { ProcessedContentPage } from "@/components/features/log-processing/ProcessedContentPage";

export default function SplunkConfigPage() {
	return (
		<ProcessedContentPage
			processType="splunk"
			savedContentType="splunk-config"
			resultKey="content"
			pageTitle="Generate Splunk Configuration"
			pageDescription="Upload a log file sample to generate Splunk configuration files"
			savedTitle="Saved Splunk Configurations"
			fallbackResultTitle="Splunk Configuration"
			accentClasses={{
				headerVia: "via-cyan-50/30 dark:via-cyan-900/20",
				titleGradient:
					"from-cyan-600 to-teal-600 dark:from-cyan-400 dark:to-teal-400",
				progressGradient: "from-cyan-500 to-teal-500",
				savedHeaderVia: "via-cyan-50/30 dark:via-cyan-900/20",
				savedTitleGradient:
					"from-cyan-600 to-teal-600 dark:from-cyan-400 dark:to-teal-400",
			}}
		/>
	);
}
