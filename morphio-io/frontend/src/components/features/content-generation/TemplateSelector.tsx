import type React from "react";
import { type JSX, useMemo, useState } from "react";
import { FaChevronDown, FaChevronUp, FaEye } from "react-icons/fa";
import type { TemplateOut } from "@/client/types.gen";
import { isTemplatePinned } from "@/lib/pinnedTemplates";

interface TemplateSelectorProps {
	selectedTemplate: number | null;
	onTemplateChange: (templateId: number) => void;
	pinnedDefault: TemplateOut[];
	pinnedCustom: TemplateOut[];
	isLoading: boolean;
}

const TemplateSelector: React.FC<TemplateSelectorProps> = ({
	selectedTemplate,
	onTemplateChange,
	pinnedDefault,
	pinnedCustom,
	isLoading,
}) => {
	const [showPreview, setShowPreview] = useState(false);

	const handleTemplateChange = (templateId: number) => {
		onTemplateChange(templateId);
		setShowPreview(false); // Hide preview when template changes
	};

	const selectedTemplateData = useMemo(() => {
		if (!selectedTemplate) return null;
		return (
			pinnedDefault.find((t) => t.id === selectedTemplate) ||
			pinnedCustom.find((t) => t.id === selectedTemplate)
		);
	}, [selectedTemplate, pinnedDefault, pinnedCustom]);

	return (
		<div className="space-y-2">
			<label className="morphio-caption block font-medium">
				Select Template
				<div className="relative mt-2">
					<select
						value={selectedTemplate ?? ""}
						onChange={(e) => handleTemplateChange(parseInt(e.target.value, 10))}
						className="morphio-input appearance-none"
						disabled={isLoading}
					>
						{(() => {
							const pinnedDefaultTemplates = pinnedDefault.filter((t) =>
								isTemplatePinned(t.id),
							);
							const pinnedCustomTemplates = pinnedCustom.filter((t) =>
								isTemplatePinned(t.id),
							);
							const pinnedCount =
								pinnedDefaultTemplates.length + pinnedCustomTemplates.length;

							const items: JSX.Element[] = [];

							if (pinnedCount > 0) {
								items.push(
									<optgroup label="Pinned Templates" key="pinned-group">
										{pinnedCustomTemplates.map((template) => (
											<option key={template.id} value={template.id}>
												{template.name}
											</option>
										))}
										{pinnedDefaultTemplates.map((template) => (
											<option key={template.id} value={template.id}>
												{template.name}
											</option>
										))}
									</optgroup>,
								);
							}

							const unpinnedCustom = pinnedCustom.filter(
								(t) => !isTemplatePinned(t.id),
							);

							if (unpinnedCustom.length > 0) {
								items.push(
									<optgroup label="Custom Templates" key="custom-group">
										{unpinnedCustom.map((template) => (
											<option key={template.id} value={template.id}>
												{template.name}
											</option>
										))}
									</optgroup>,
								);
							}

							const unpinnedDefault = pinnedDefault.filter(
								(t) => !isTemplatePinned(t.id),
							);

							if (unpinnedDefault.length > 0) {
								items.push(
									<optgroup label="Default Templates" key="default-group">
										{unpinnedDefault.map((template) => (
											<option key={template.id} value={template.id}>
												{template.name}
											</option>
										))}
									</optgroup>,
								);
							}

							return items;
						})()}
					</select>
					<div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
						<FaChevronDown className="text-gray-400" />
					</div>
				</div>
			</label>
			{selectedTemplateData && (
				<div className="mt-2">
					<button
						type="button"
						onClick={() => setShowPreview(!showPreview)}
						className="flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
					>
						<FaEye className="h-3 w-3" />
						{showPreview ? "Hide" : "Preview"} template
						{showPreview ? (
							<FaChevronUp className="h-3 w-3" />
						) : (
							<FaChevronDown className="h-3 w-3" />
						)}
					</button>
					{showPreview && (
						<div className="mt-2 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 max-h-60 overflow-y-auto">
							<pre className="text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap font-mono">
								{selectedTemplateData.template_content}
							</pre>
						</div>
					)}
				</div>
			)}
		</div>
	);
};

export default TemplateSelector;
