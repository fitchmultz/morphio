import { ProcessedContentPage } from "@/components/features/log-processing/ProcessedContentPage";

export default function LogsPage() {
	return (
		<ProcessedContentPage
			processType="logs"
			savedContentType="log-summary"
			resultKey="summary"
			pageTitle="Process Log File"
			pageDescription="Upload your log files for analysis and processing"
			savedTitle="Saved Log Summaries"
			fallbackResultTitle="Log Analysis"
			accentClasses={{
				headerVia: "via-blue-50/30 dark:via-blue-900/20",
				titleGradient:
					"from-blue-600 to-purple-600 dark:from-blue-400 dark:to-purple-400",
				progressGradient: "from-blue-500 to-purple-500",
				savedHeaderVia: "via-purple-50/30 dark:via-purple-900/20",
				savedTitleGradient:
					"from-purple-600 to-pink-600 dark:from-purple-400 dark:to-pink-400",
			}}
		/>
	);
}
