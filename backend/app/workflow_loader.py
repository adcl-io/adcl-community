# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Workflow Loader - Load and save workflows from text files
Follows ADCL principle: "Configuration is Code"
"""
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
from .config_loader import get_workflow_config


class WorkflowLoader:
    """
    Load workflows from filesystem (text-based configuration).

    Directory structure:
        workflows/
        ├── templates/     # Built-in workflows
        └── custom/        # User-created workflows
    """

    def __init__(self, base_dir: str = None):
        # Load from config (ADCL: Configuration is Code)
        if base_dir is None:
            config = get_workflow_config()
            base_dir = config["workflows"]["base_dir"]

        self.base_dir = Path(base_dir)
        self.templates_dir = self.base_dir / "templates"
        self.custom_dir = self.base_dir / "custom"

        # Ensure directories exist (best effort - don't fail on permission errors)
        # This allows the module to load even in restricted environments (tests, dev)
        try:
            self.templates_dir.mkdir(parents=True, exist_ok=True)
            self.custom_dir.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError) as e:
            # Log warning but don't crash - directories will be created when needed
            import sys
            print(f"Warning: Could not create workflow directories: {e}", file=sys.stderr)
            print(f"  Directories will be created on-demand when workflows are used.", file=sys.stderr)

    def load(self, name: str, category: str = "templates") -> Dict[str, Any]:
        """
        Load a workflow by name.

        Args:
            name: Workflow name (without .json extension)
            category: "templates" or "custom"

        Returns:
            Workflow definition as dict

        Raises:
            FileNotFoundError: If workflow doesn't exist
        """
        if category == "templates":
            workflow_dir = self.templates_dir
        elif category == "custom":
            workflow_dir = self.custom_dir
        else:
            raise ValueError(f"Invalid category: {category}. Must be 'templates' or 'custom'")

        # Support both with and without .json extension
        if not name.endswith(".json"):
            name = f"{name}.json"

        workflow_path = workflow_dir / name

        if not workflow_path.exists():
            raise FileNotFoundError(f"Workflow not found: {workflow_path}")

        with open(workflow_path, 'r') as f:
            workflow_data = json.load(f)

        return workflow_data

    def save(self, workflow: Dict[str, Any], category: str = "custom", name: Optional[str] = None):
        """
        Save a workflow to disk.

        Args:
            workflow: Workflow definition
            category: "templates" or "custom"
            name: Optional filename override (uses workflow['name'] if not provided)
        """
        if category == "templates":
            workflow_dir = self.templates_dir
        elif category == "custom":
            workflow_dir = self.custom_dir
        else:
            raise ValueError(f"Invalid category: {category}")

        # Determine filename
        if name is None:
            name = workflow.get("name", "unnamed_workflow")

        # Slugify name (lowercase, replace spaces with underscores)
        name = name.lower().replace(" ", "_").replace("-", "_")

        # Remove special characters
        name = "".join(c for c in name if c.isalnum() or c == "_")

        if not name.endswith(".json"):
            name = f"{name}.json"

        workflow_path = workflow_dir / name

        with open(workflow_path, 'w') as f:
            json.dump(workflow, f, indent=2)

        return str(workflow_path)

    def list_templates(self) -> List[Dict[str, Any]]:
        """
        List all template workflows.

        Returns:
            List of workflow metadata (name, description, version)
        """
        return self._list_workflows(self.templates_dir)

    def list_custom(self) -> List[Dict[str, Any]]:
        """
        List all custom workflows.

        Returns:
            List of workflow metadata (name, description, version)
        """
        return self._list_workflows(self.custom_dir)

    def list_all(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        List all workflows (templates and custom).

        Returns:
            Dict with "templates" and "custom" keys
        """
        return {
            "templates": self.list_templates(),
            "custom": self.list_custom()
        }

    def _list_workflows(self, directory: Path) -> List[Dict[str, Any]]:
        """
        List workflows in a directory.

        Args:
            directory: Directory to scan

        Returns:
            List of workflow metadata
        """
        workflows = []

        for workflow_file in directory.glob("*.json"):
            try:
                with open(workflow_file, 'r') as f:
                    workflow_data = json.load(f)

                # Extract metadata
                metadata = {
                    "name": workflow_data.get("name", workflow_file.stem),
                    "file": workflow_file.name,
                    "version": workflow_data.get("version", "1.0.0"),
                    "description": workflow_data.get("description", ""),
                    "author": workflow_data.get("author", ""),
                    "parameters": workflow_data.get("parameters", {}),
                    "node_count": len(workflow_data.get("nodes", [])),
                    "edge_count": len(workflow_data.get("edges", []))
                }

                workflows.append(metadata)
            except Exception as e:
                print(f"Warning: Failed to load workflow {workflow_file}: {e}")

        return workflows

    def exists(self, name: str, category: str = "templates") -> bool:
        """
        Check if a workflow exists.

        Args:
            name: Workflow name
            category: "templates" or "custom"

        Returns:
            True if workflow exists
        """
        try:
            self.load(name, category)
            return True
        except FileNotFoundError:
            return False

    def delete(self, name: str, category: str = "custom"):
        """
        Delete a workflow.

        Args:
            name: Workflow name
            category: "templates" or "custom" (templates protected by default)

        Raises:
            PermissionError: If trying to delete a template
            FileNotFoundError: If workflow doesn't exist
        """
        if category == "templates":
            raise PermissionError("Cannot delete template workflows. Use 'custom' category.")

        workflow_dir = self.custom_dir

        if not name.endswith(".json"):
            name = f"{name}.json"

        workflow_path = workflow_dir / name

        if not workflow_path.exists():
            raise FileNotFoundError(f"Workflow not found: {workflow_path}")

        workflow_path.unlink()
        return True
