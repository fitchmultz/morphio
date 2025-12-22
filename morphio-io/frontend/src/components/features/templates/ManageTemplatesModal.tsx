"use client";

import type { TemplateOut } from "@/client";
import Modal from "@/components/common/Modal";
import { TemplateListItem } from "./TemplateListItem";

export interface ManageTemplatesModalProps {
	isOpen: boolean;
	onClose: () => void;
	customTemplates: TemplateOut[];
	defaultTemplates: TemplateOut[];
	onEditTemplate: (templateId: number) => void;
	onCloneTemplate: (template: TemplateOut) => void;
	onDeleteTemplate: (templateId: number) => void;
	onTogglePin: (templateId: number) => void;
	isPinned: (templateId: number) => boolean;
}

export function ManageTemplatesModal({
	isOpen,
	onClose,
	customTemplates,
	defaultTemplates,
	onEditTemplate,
	onCloneTemplate,
	onDeleteTemplate,
	onTogglePin,
	isPinned,
}: ManageTemplatesModalProps) {
	return (
		<Modal isOpen={isOpen} onClose={onClose} title="Manage Templates" size="lg">
			<div className="space-y-6">
				<div className="mb-4">
					<h3 className="morphio-h3 mb-2">Custom Templates</h3>
					<div className="grid gap-4">
						{customTemplates.length > 0 ? (
							customTemplates.map((template) => (
								<TemplateListItem
									key={template.id}
									template={template}
									variant="custom"
									isPinned={isPinned(template.id)}
									onEdit={onEditTemplate}
									onDelete={onDeleteTemplate}
									onTogglePin={onTogglePin}
								/>
							))
						) : (
							<div className="text-center py-4">
								<p className="morphio-body text-gray-500 dark:text-gray-400">
									No custom templates yet. Create one to get started!
								</p>
							</div>
						)}
					</div>
				</div>

				<div className="mb-4">
					<h3 className="morphio-h3 mb-2">Default Templates</h3>
					<div className="grid gap-4">
						{defaultTemplates.length > 0 ? (
							defaultTemplates.map((template) => (
								<TemplateListItem
									key={template.id}
									template={template}
									variant="default"
									isPinned={isPinned(template.id)}
									onClone={onCloneTemplate}
									onTogglePin={onTogglePin}
								/>
							))
						) : (
							<div className="text-center py-4">
								<p className="morphio-body text-gray-500 dark:text-gray-400">
									No default templates found.
								</p>
							</div>
						)}
					</div>
				</div>
			</div>
		</Modal>
	);
}
