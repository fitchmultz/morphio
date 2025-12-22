type LogLevel = "debug" | "info" | "warn" | "error";

const logger = {
	debug: (message: string, meta?: object) => logMessage("debug", message, meta),
	info: (message: string, meta?: object) => logMessage("info", message, meta),
	warn: (message: string, meta?: object) => logMessage("warn", message, meta),
	error: (message: string, meta?: object) => logMessage("error", message, meta),
	performance: (label: string, duration: number) =>
		logMessage("info", `Performance: ${label}`, { duration }),
};

function logMessage(level: LogLevel, message: string, meta?: object) {
	if (process.env.NODE_ENV !== "production") {
		const timestamp = new Date().toISOString();
		const logObject = { level, message, timestamp, ...meta };
		console[level](JSON.stringify(logObject));
	}
}

// Uncomment and implement when ready to send logs to a service
// async function sendLogsToService(logObject: object) {
//   try {
//     const response = await fetch('/api/logs', {
//       method: 'POST',
//       headers: { 'Content-Type': 'application/json' },
//       body: JSON.stringify(logObject)
//     });
//     if (!response.ok) throw new Error('Failed to send logs');
//   } catch (error) {
//     console.error('Error sending logs:', error);
//   }
// }

export default logger;
