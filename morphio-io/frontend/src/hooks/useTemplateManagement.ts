"use client";

import { useCallback, useMemo, useState } from "react";
import {
	deleteTemplate as deleteTemplateSdk,
	saveTemplate,
	type TemplateOut,
} from "@/client";
import type { TemplateGroups } from "@/hooks/useTemplatesQuery";
import logger from "@/lib/logger";
import { isTemplatePinned, togglePinTemplate } from "@/lib/pinnedTemplates";
import { notifyError, notifySuccess } from "@/lib/toast";

export interface UseTemplateManagementOptions {
	templates: TemplateGroups;
	refetch: () => void;
}

export interface UseTemplateManagementReturn {
	pinnedDefault: TemplateOut[];
	pinnedCustom: TemplateOut[];
	cloneDefaultTemplate: (template: TemplateOut) => Promise<void>;
	deleteTemplateById: (templateId: number) => Promise<void>;
	togglePin: (templateId: number) => void;
	isPinned: (templateId: number) => boolean;
}

export function useTemplateManagement({
	templates,
	refetch,
}: UseTemplateManagementOptions): UseTemplateManagementReturn {
	const [pinnedRefresh, setPinnedRefresh] = useState(0);

	const cloneDefaultTemplate = useCallback(
		async (template: TemplateOut) => {
			try {
				const name = `${template.name} (Clone)`;
				const { data, error } = await saveTemplate({
					body: {
						name,
						template_content: template.template_content,
						is_default: false,
					},
				});

				if (error) {
					throw new Error(
						error instanceof Error ? error.message : String(error),
					);
				}
				if (data?.status !== "success") {
					throw new Error(data?.message || "Failed to clone template");
				}
				notifySuccess("Template cloned successfully");
				refetch();
			} catch (err) {
				const message =
					err instanceof Error ? err.message : "Failed to clone template";
				logger.warn("Error cloning default template", { err });
				notifyError(message);
			}
		},
		[refetch],
	);

	const deleteTemplateById = useCallback(
		async (templateId: number) => {
			try {
				const { data, error } = await deleteTemplateSdk({
					path: { template_id: templateId },
				});

				if (error) {
					throw new Error(
						error instanceof Error ? error.message : String(error),
					);
				}
				if (data?.status !== "success") {
					throw new Error(data?.message || "Failed to delete template");
				}
				notifySuccess("Template deleted successfully");
				refetch();
			} catch (err) {
				const message =
					err instanceof Error ? err.message : "Failed to delete template";
				logger.warn("Error deleting template", { err });
				notifyError(message);
			}
		},
		[refetch],
	);

	const togglePin = useCallback((templateId: number) => {
		togglePinTemplate(templateId);
		setPinnedRefresh((prev) => prev + 1);
	}, []);

	const isPinned = useCallback((templateId: number) => {
		return isTemplatePinned(templateId);
	}, []);

	// biome-ignore lint/correctness/useExhaustiveDependencies: pinnedRefresh triggers recalculation when pins change (localStorage-based)
	const pinnedDefault = useMemo(() => {
		return templates.default.slice().sort((a, b) => {
			const aPinned = isTemplatePinned(a.id);
			const bPinned = isTemplatePinned(b.id);
			if (aPinned && !bPinned) return -1;
			if (!aPinned && bPinned) return 1;
			return a.name.localeCompare(b.name);
		});
	}, [templates.default, pinnedRefresh]);

	// biome-ignore lint/correctness/useExhaustiveDependencies: pinnedRefresh triggers recalculation when pins change (localStorage-based)
	const pinnedCustom = useMemo(() => {
		return templates.custom.slice().sort((a, b) => {
			const aPinned = isTemplatePinned(a.id);
			const bPinned = isTemplatePinned(b.id);
			if (aPinned && !bPinned) return -1;
			if (!aPinned && bPinned) return 1;
			return a.name.localeCompare(b.name);
		});
	}, [templates.custom, pinnedRefresh]);

	return {
		pinnedDefault,
		pinnedCustom,
		cloneDefaultTemplate,
		deleteTemplateById,
		togglePin,
		isPinned,
	};
}
