"""Explicit service facade for the application's 2D CAD engines."""

from __future__ import annotations

from typing import Any


class TwoDCADService:
    """Expose image, text, and DXF editing workflows through one API."""

    def __init__(self, pipeline_manager: Any):
        self.pipeline_manager = pipeline_manager

    def generate_from_image(
        self,
        *,
        image_path: str,
        user_prompt: str | None = None,
        params: dict | None = None,
        user_id: str = "default_user",
        project_id: str | None = None,
    ) -> str:
        return self.pipeline_manager.image_to_2d(
            image_path=image_path,
            user_prompt=user_prompt,
            params=params,
            user_id=user_id,
            project_id=project_id,
        )

    def generate_from_text(
        self,
        *,
        prompt: str,
        params: dict | None = None,
        user_id: str = "default_user",
        project_id: str | None = None,
    ) -> str:
        return self.pipeline_manager.text_to_2d(
            user_prompt=prompt,
            params=params,
            user_id=user_id,
            project_id=project_id,
        )

    def edit_dxf(
        self,
        *,
        file_path: str,
        prompt: str,
        user_id: str = "default_user",
        project_id: str | None = None,
    ) -> str:
        return self.pipeline_manager.run_2d_pipeline(
            user_id=user_id,
            project_id=project_id,
            mode="Edit",
            prompt=prompt,
            image_path=file_path,
        )
