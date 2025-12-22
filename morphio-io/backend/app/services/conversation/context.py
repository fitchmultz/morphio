from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional


@dataclass
class ConversationContext:
    transcript_summary: Optional[str] = None
    key_points: List[str] = field(default_factory=list)
    style_guidelines: Dict[str, str] = field(default_factory=dict)
    previous_edits: List[Dict[str, str]] = field(default_factory=list)
    base_template: Optional[str] = None
    template_name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "ConversationContext":
        if not data:
            return cls()
        return cls(
            transcript_summary=data.get("transcript_summary"),
            key_points=list(data.get("key_points", [])),
            style_guidelines=dict(data.get("style_guidelines", {})),
            previous_edits=list(data.get("previous_edits", [])),
            base_template=data.get("base_template"),
            template_name=data.get("template_name"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transcript_summary": self.transcript_summary,
            "key_points": self.key_points,
            "style_guidelines": self.style_guidelines,
            "previous_edits": self.previous_edits,
            "base_template": self.base_template,
            "template_name": self.template_name,
        }

    def record_user_direction(self, message: str) -> None:
        self.previous_edits.append(
            {
                "timestamp": datetime.now(UTC).isoformat() + "Z",
                "message": message.strip(),
            }
        )
        # Keep only the most recent 10 edits to avoid unbounded growth
        if len(self.previous_edits) > 10:
            self.previous_edits = self.previous_edits[-10:]

    def update_key_points(self, points: List[str]) -> None:
        if points:
            combined = set(self.key_points)
            combined.update(point.strip() for point in points if point.strip())
            self.key_points = list(combined)[:12]

    def apply_style_guidelines(self, updates: Dict[str, str]) -> None:
        for key, value in updates.items():
            if value:
                self.style_guidelines[key] = value

    def build_prompt(self, user_message: str, current_content: str) -> str:
        preview = current_content.strip()
        if len(preview) > 1500:
            preview = preview[:1500] + "\n..."

        sections: List[str] = []

        if self.transcript_summary:
            sections.append(f"Transcript Summary:\n{self.transcript_summary}")
        if self.key_points:
            rendered_points = "\n".join(f"- {point}" for point in self.key_points)
            sections.append(f"Key Points to Preserve:\n{rendered_points}")
        if self.style_guidelines:
            rendered_guidelines = "\n".join(
                f"- {key}: {value}" for key, value in self.style_guidelines.items()
            )
            sections.append(f"Style Guidelines:\n{rendered_guidelines}")
        if self.previous_edits:
            rendered_edits = "\n".join(
                f"- {item['timestamp']}: {item['message']}" for item in self.previous_edits
            )
            sections.append(f"Recent Edit Requests:\n{rendered_edits}")
        if preview:
            sections.append(f"Current Content Snapshot:\n{preview}")

        sections.append(f"Latest User Request:\n{user_message.strip()}")
        return "\n\n".join(sections)
