from pydantic import field_validator

from app.schemas.common import BaseSchema


class UserProfileUpdate(BaseSchema):
    """Email changes go through /auth/send-email-change-verification instead."""

    username: str | None = None
    current_password: str | None = None
    new_password: str | None = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        if v is not None:
            if len(v.strip()) < 3:
                raise ValueError("Username must be at least 3 characters long")
            if len(v.strip()) > 50:
                raise ValueError("Username cannot exceed 50 characters")
            if not v.strip().replace("_", "").replace("-", "").isalnum():
                raise ValueError(
                    "Username can only contain letters, numbers, underscores, and hyphens"
                )
            return v.strip()
        return v

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v):
        if v is not None and len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UsernameCheck(BaseSchema):
    username: str
    available: bool


class SettingsAppearance(BaseSchema):
    theme: str = "dark"  # "light", "dark", "system"
    font_size: str = "medium"  # "small", "medium", "large"
    layout_density: str = "comfortable"  # "compact", "dense", "comfortable"


class SettingsGraph(BaseSchema):
    edge_thickness_scale: float = 1.0
    node_spacing: float = 1.0
    show_backlinks: bool = True
    physics_enabled: bool = True
    clustering_strength: float = 0.5


class SettingsAI(BaseSchema):
    use_openai: bool = True
    daily_request_limit: int = 100
    enable_caching: bool = True


class SettingsStudyFlow(BaseSchema):
    quiz_enabled: bool = True
    flashcard_auto_review: bool = True
    linked_notes_suggestions: bool = True


class SettingsAdvanced(BaseSchema):
    data_export_enabled: bool = True
    analytics_enabled: bool = True


class UserSettings(BaseSchema):
    appearance: SettingsAppearance
    graph: SettingsGraph
    ai: SettingsAI
    study_flow: SettingsStudyFlow
    advanced: SettingsAdvanced
