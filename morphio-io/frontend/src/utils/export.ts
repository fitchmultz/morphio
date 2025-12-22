/**
 * File export utilities for downloading content in various formats.
 */

const sanitizeFilename = (name: string): string => {
	return name
		.trim()
		.replace(/[<>:"/\\|?*]/g, "") // Remove invalid chars
		.replace(/\s+/g, "_")
		.substring(0, 200); // Max filename length
};

const downloadFile = (
	content: string,
	filename: string,
	mimeType: string,
): void => {
	const blob = new Blob([content], { type: `${mimeType};charset=utf-8` });
	const url = URL.createObjectURL(blob);

	const link = document.createElement("a");
	link.href = url;
	link.download = filename;
	document.body.appendChild(link);
	link.click();
	document.body.removeChild(link);

	// Critical: Prevent memory leak
	URL.revokeObjectURL(url);
};

export const exportAsMarkdown = (content: string, title: string): void => {
	downloadFile(content, `${sanitizeFilename(title)}.md`, "text/markdown");
};

export const exportAsText = (content: string, title: string): void => {
	// Strip markdown formatting for plain text
	const plainText = content
		.replace(/#{1,6}\s/g, "") // Remove headers
		.replace(/\*\*([^*]+)\*\*/g, "$1") // Remove bold
		.replace(/\*([^*]+)\*/g, "$1") // Remove italic
		.replace(/`([^`]+)`/g, "$1") // Remove inline code
		.replace(/\[([^\]]+)\]\([^)]+\)/g, "$1"); // Remove links, keep text

	downloadFile(plainText, `${sanitizeFilename(title)}.txt`, "text/plain");
};

export const exportAsHtml = (content: string, title: string): void => {
	// Basic markdown to HTML conversion for common elements
	const htmlContent = content
		.replace(/^### (.+)$/gm, "<h3>$1</h3>")
		.replace(/^## (.+)$/gm, "<h2>$1</h2>")
		.replace(/^# (.+)$/gm, "<h1>$1</h1>")
		.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
		.replace(/\*([^*]+)\*/g, "<em>$1</em>")
		.replace(/`([^`]+)`/g, "<code>$1</code>")
		.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>')
		.replace(/\n/g, "<br>\n");

	const fullHtml = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${sanitizeFilename(title)}</title>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; max-width: 800px; margin: 0 auto; padding: 2rem; line-height: 1.6; }
        h1, h2, h3 { margin-top: 1.5em; margin-bottom: 0.5em; }
        code { background: #f4f4f4; padding: 0.2em 0.4em; border-radius: 3px; }
        a { color: #0066cc; }
    </style>
</head>
<body>
${htmlContent}
</body>
</html>`;

	downloadFile(fullHtml, `${sanitizeFilename(title)}.html`, "text/html");
};
