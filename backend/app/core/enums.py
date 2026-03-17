# backend/app/core/enums.py
import enum


class GlobalTaskStatus(str, enum.Enum):
    """Used for all actionable work: Projects, Issues, Meetings, Bills."""
    OPEN        = "OPEN"         # Replaces: NEW, PENDING, PLANNING, SCHEDULED
    IN_PROGRESS = "IN_PROGRESS"  # Replaces: ONGOING, CONTACTED
    BLOCKED     = "BLOCKED"      # Replaces: ON_HOLD
    RESOLVED    = "RESOLVED"     # Replaces: COMPLETED, SOLVED, DONE
    CANCELLED   = "CANCELLED"    # Replaces: CANCELLED


class MasterPipelineStage(str, enum.Enum):
    """Used strictly for Shops/Leads — tracks the full deal lifecycle."""
    LEAD        = "LEAD"         # Replaces: NEW
    PITCHING    = "PITCHING"     # Replaces: CONTACTED, MEETING_SET
    NEGOTIATION = "NEGOTIATION"  # Bill generated, pending payment
    DELIVERY    = "DELIVERY"     # Replaces: CONVERTED (project active)
    MAINTENANCE = "MAINTENANCE"  # Project done, handling post-sale issues
