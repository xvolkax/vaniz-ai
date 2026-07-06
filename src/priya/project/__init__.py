"""Single-project data: one builder, one project.

Loaded once at startup, injected into the LLM context. No retrieval at runtime.
"""
from priya.project.loader import ProjectData, get_project, render_project_knowledge

__all__ = ["ProjectData", "get_project", "render_project_knowledge"]
