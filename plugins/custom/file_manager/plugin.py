"""
File Manager Plugin

A simple file management plugin providing file upload, download, directory browsing,
and basic file operations with web API and UI.
"""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field

from nexus.plugins import BasePlugin

logger = logging.getLogger(__name__)


# Data Models
class FileItem(BaseModel):
    """File item model."""

    name: str
    path: str
    type: str  # file, directory
    size: int = 0
    modified: datetime
    permissions: str = ""
    is_hidden: bool = False


class FileOperation(BaseModel):
    """File operation model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    operation: str  # upload, download, delete, move, copy
    source_path: str
    target_path: Optional[str] = None
    status: str = "pending"  # pending, in_progress, completed, failed
    progress: int = 0
    error_message: Optional[str] = None
    user_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class FileManagerPlugin(BasePlugin):
    """File Manager Plugin with file operations and web interface."""

    def __init__(self):
        super().__init__()
        self.name = "file_manager"
        self.version = "1.0.0"
        self.category = "custom"
        self.description = (
            "Simple file management system with upload/download and directory browsing"
        )

        # Configuration
        self.base_directory = Path.cwd() / "file_storage"
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        self.allowed_extensions = {
            ".txt",
            ".md",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".svg",
            ".zip",
            ".tar",
            ".gz",
            ".json",
            ".xml",
            ".csv",
        }

        # Storage
        self.file_operations: List[FileOperation] = []

        # Ensure base directory exists
        self.base_directory.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> bool:
        """Initialize the plugin."""
        logger.info(f"Initializing {self.name} plugin v{self.version}")

        # Create sample directories
        self._create_sample_structure()

        await self.publish_event(
            "file_manager.initialized",
            {
                "plugin": self.name,
                "base_directory": str(self.base_directory),
                "max_file_size": self.max_file_size,
            },
        )

        logger.info(f"{self.name} plugin initialized successfully")
        return True

    async def shutdown(self) -> None:
        """Shutdown the plugin."""
        logger.info(f"Shutting down {self.name} plugin")
        await self.publish_event(
            "file_manager.shutdown",
            {"plugin": self.name, "timestamp": datetime.utcnow().isoformat()},
        )

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for this plugin."""
        router = APIRouter(prefix="/plugins/file_manager", tags=["file_manager"])

        @router.get("/files")
        async def list_files(path: str = "", show_hidden: bool = False):
            """List files and directories."""
            try:
                target_path = self._resolve_path(path)
                if not target_path.exists():
                    raise HTTPException(status_code=404, detail="Path not found")

                if not target_path.is_dir():
                    raise HTTPException(status_code=400, detail="Path is not a directory")

                items = []
                for item in target_path.iterdir():
                    if not show_hidden and item.name.startswith("."):
                        continue

                    try:
                        stat = item.stat()
                        file_item = FileItem(
                            name=item.name,
                            path=str(item.relative_to(self.base_directory)),
                            type="directory" if item.is_dir() else "file",
                            size=stat.st_size if item.is_file() else 0,
                            modified=datetime.fromtimestamp(stat.st_mtime),
                            permissions=oct(stat.st_mode)[-3:],
                            is_hidden=item.name.startswith("."),
                        )
                        items.append(file_item)
                    except (OSError, ValueError) as e:
                        logger.warning(f"Error reading item {item}: {e}")
                        continue

                # Sort: directories first, then files
                items.sort(key=lambda x: (x.type != "directory", x.name.lower()))

                return {
                    "path": path,
                    "items": [item.dict() for item in items],
                    "total": len(items),
                }

            except Exception as e:
                logger.error(f"Error listing files: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @router.get("/files/info")
        async def get_file_info(path: str):
            """Get detailed file information."""
            try:
                target_path = self._resolve_path(path)
                if not target_path.exists():
                    raise HTTPException(status_code=404, detail="File not found")

                stat = target_path.stat()
                return {
                    "name": target_path.name,
                    "path": path,
                    "absolute_path": str(target_path),
                    "type": "directory" if target_path.is_dir() else "file",
                    "size": stat.st_size,
                    "size_formatted": self._format_file_size(stat.st_size),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "permissions": oct(stat.st_mode)[-3:],
                    "is_readable": os.access(target_path, os.R_OK),
                    "is_writable": os.access(target_path, os.W_OK),
                    "extension": target_path.suffix.lower() if target_path.is_file() else None,
                }

            except Exception as e:
                logger.error(f"Error getting file info: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @router.post("/files/upload")
        async def upload_file(path: str = "", file: UploadFile = File(...)):
            """Upload a file."""
            try:
                # Validate file size
                if file.size and file.size > self.max_file_size:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size: {self._format_file_size(self.max_file_size)}",
                    )

                # Validate file extension
                if file.filename:
                    file_ext = Path(file.filename).suffix.lower()
                    if file_ext and file_ext not in self.allowed_extensions:
                        raise HTTPException(
                            status_code=400,
                            detail=f"File type not allowed. Allowed extensions: {', '.join(self.allowed_extensions)}",
                        )

                # Resolve upload directory
                upload_dir = self._resolve_path(path)
                upload_dir.mkdir(parents=True, exist_ok=True)

                # Create unique filename if file already exists
                filename = file.filename or "uploaded_file"
                target_file = upload_dir / filename
                counter = 1
                while target_file.exists():
                    stem = Path(filename).stem
                    suffix = Path(filename).suffix
                    target_file = upload_dir / f"{stem}_{counter}{suffix}"
                    counter += 1

                # Save file
                content = await file.read()
                target_file.write_bytes(content)

                # Log operation
                operation = FileOperation(
                    operation="upload",
                    source_path=filename,
                    target_path=str(target_file.relative_to(self.base_directory)),
                    status="completed",
                    progress=100,
                )
                self.file_operations.append(operation)

                await self.publish_event(
                    "file_manager.file.uploaded",
                    {
                        "filename": target_file.name,
                        "path": str(target_file.relative_to(self.base_directory)),
                        "size": len(content),
                    },
                )

                return {
                    "message": "File uploaded successfully",
                    "filename": target_file.name,
                    "path": str(target_file.relative_to(self.base_directory)),
                    "size": len(content),
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error uploading file: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @router.get("/files/download")
        async def download_file(path: str):
            """Download a file."""
            try:
                target_path = self._resolve_path(path)
                if not target_path.exists():
                    raise HTTPException(status_code=404, detail="File not found")

                if not target_path.is_file():
                    raise HTTPException(status_code=400, detail="Path is not a file")

                # Log operation
                operation = FileOperation(
                    operation="download",
                    source_path=path,
                    status="completed",
                    progress=100,
                )
                self.file_operations.append(operation)

                await self.publish_event(
                    "file_manager.file.downloaded",
                    {"filename": target_path.name, "path": path},
                )

                return FileResponse(
                    path=target_path,
                    filename=target_path.name,
                    media_type="application/octet-stream",
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error downloading file: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @router.delete("/files")
        async def delete_file(path: str):
            """Delete a file or directory."""
            try:
                target_path = self._resolve_path(path)
                if not target_path.exists():
                    raise HTTPException(status_code=404, detail="File not found")

                # Prevent deletion of base directory
                if target_path == self.base_directory:
                    raise HTTPException(status_code=400, detail="Cannot delete base directory")

                if target_path.is_dir():
                    shutil.rmtree(target_path)
                else:
                    target_path.unlink()

                # Log operation
                operation = FileOperation(
                    operation="delete",
                    source_path=path,
                    status="completed",
                    progress=100,
                )
                self.file_operations.append(operation)

                await self.publish_event(
                    "file_manager.file.deleted",
                    {"path": path, "type": "directory" if target_path.is_dir() else "file"},
                )

                return {
                    "message": f"{'Directory' if target_path.is_dir() else 'File'} deleted successfully"
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error deleting file: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @router.post("/files/create-directory")
        async def create_directory(path: str, name: str):
            """Create a new directory."""
            try:
                parent_path = self._resolve_path(path)
                new_dir = parent_path / name

                if new_dir.exists():
                    raise HTTPException(status_code=400, detail="Directory already exists")

                new_dir.mkdir(parents=True)

                await self.publish_event(
                    "file_manager.directory.created",
                    {"name": name, "path": str(new_dir.relative_to(self.base_directory))},
                )

                return {
                    "message": "Directory created successfully",
                    "name": name,
                    "path": str(new_dir.relative_to(self.base_directory)),
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error creating directory: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @router.post("/files/move")
        async def move_file(source_path: str, target_path: str):
            """Move or rename a file/directory."""
            try:
                source = self._resolve_path(source_path)
                target = self._resolve_path(target_path)

                if not source.exists():
                    raise HTTPException(status_code=404, detail="Source file not found")

                if target.exists():
                    raise HTTPException(status_code=400, detail="Target already exists")

                # Create target directory if needed
                target.parent.mkdir(parents=True, exist_ok=True)

                source.rename(target)

                # Log operation
                operation = FileOperation(
                    operation="move",
                    source_path=source_path,
                    target_path=target_path,
                    status="completed",
                    progress=100,
                )
                self.file_operations.append(operation)

                await self.publish_event(
                    "file_manager.file.moved",
                    {"source": source_path, "target": target_path},
                )

                return {"message": "File moved successfully"}

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error moving file: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @router.get("/operations")
        async def get_operations(limit: int = 50):
            """Get recent file operations."""
            # Sort by timestamp (newest first)
            recent_ops = sorted(self.file_operations, key=lambda x: x.timestamp, reverse=True)[
                :limit
            ]
            return {"operations": [op.dict() for op in recent_ops]}

        @router.get("/stats")
        async def get_stats():
            """Get file system statistics."""
            try:
                total_files = 0
                total_size = 0
                file_types = {}

                for root, dirs, files in os.walk(self.base_directory):
                    for file in files:
                        file_path = Path(root) / file
                        try:
                            stat = file_path.stat()
                            total_files += 1
                            total_size += stat.st_size

                            # Count file types
                            ext = file_path.suffix.lower() or "no extension"
                            file_types[ext] = file_types.get(ext, 0) + 1

                        except (OSError, ValueError):
                            continue

                # Get disk usage
                disk_usage = shutil.disk_usage(self.base_directory)

                return {
                    "total_files": total_files,
                    "total_size": total_size,
                    "total_size_formatted": self._format_file_size(total_size),
                    "file_types": file_types,
                    "disk_usage": {
                        "total": disk_usage.total,
                        "used": disk_usage.used,
                        "free": disk_usage.free,
                        "total_formatted": self._format_file_size(disk_usage.total),
                        "used_formatted": self._format_file_size(disk_usage.used),
                        "free_formatted": self._format_file_size(disk_usage.free),
                    },
                    "recent_operations": len(self.file_operations),
                }

            except Exception as e:
                logger.error(f"Error getting stats: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        # Web UI
        @router.get("/ui", response_class=HTMLResponse)
        async def file_manager_ui():
            """Serve the file manager web interface."""
            return self._get_file_manager_html()

        return [router]

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for this plugin."""
        return {
            "collections": {
                f"{self.name}_operations": {
                    "indexes": [
                        {"field": "id", "unique": True},
                        {"field": "operation"},
                        {"field": "status"},
                        {"field": "timestamp"},
                        {"field": "user_id"},
                    ]
                },
            }
        }

    # Helper methods
    def _resolve_path(self, path: str) -> Path:
        """Resolve a relative path to absolute path within base directory."""
        if not path or path == "/":
            return self.base_directory

        # Remove leading slash and resolve relative to base directory
        clean_path = path.lstrip("/")
        resolved = (self.base_directory / clean_path).resolve()

        # Ensure the path is within base directory (security check)
        if not str(resolved).startswith(str(self.base_directory.resolve())):
            raise ValueError("Path outside allowed directory")

        return resolved

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size = float(size_bytes)

        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1

        return f"{size:.1f} {size_names[i]}"

    def _create_sample_structure(self):
        """Create sample directory structure and files."""
        # Create sample directories
        (self.base_directory / "Documents").mkdir(exist_ok=True)
        (self.base_directory / "Images").mkdir(exist_ok=True)
        (self.base_directory / "Downloads").mkdir(exist_ok=True)
        (self.base_directory / "Projects").mkdir(exist_ok=True)

        # Create sample files
        sample_files = {
            "Documents/README.md": "# File Manager\n\nWelcome to the Nexus File Manager!\n",
            "Documents/sample.txt": "This is a sample text file created by the File Manager plugin.\n",
            "Projects/project_info.json": json.dumps(
                {
                    "name": "Sample Project",
                    "version": "1.0.0",
                    "description": "A sample project file",
                },
                indent=2,
            ),
        }

        for file_path, content in sample_files.items():
            full_path = self.base_directory / file_path
            if not full_path.exists():
                full_path.write_text(content)

    def _get_file_manager_html(self) -> str:
        """Generate the file manager HTML UI."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>File Manager - Nexus Platform</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }

        .header {
            background: white;
            padding: 1rem 2rem;
            border-bottom: 1px solid #ddd;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h1 {
            color: #2563eb;
            font-size: 1.5rem;
            font-weight: 600;
        }

        .toolbar {
            display: flex;
            gap: 0.5rem;
        }

        .container {
            max-width: 1200px;
            margin: 2rem auto;
            padding: 0 1rem;
        }

        .file-manager {
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            overflow: hidden;
        }

        .breadcrumb {
            padding: 1rem;
            background: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .breadcrumb-item {
            color: #6c757d;
            text-decoration: none;
            cursor: pointer;
        }

        .breadcrumb-item:hover {
            color: #2563eb;
        }

        .breadcrumb-item.active {
            color: #495057;
            font-weight: 500;
        }

        .file-list {
            min-height: 400px;
        }

        .file-list table {
            width: 100%;
            border-collapse: collapse;
        }

        .file-list th,
        .file-list td {
            padding: 0.75rem 1rem;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }

        .file-list th {
            background: #f8f9fa;
            font-weight: 600;
            color: #495057;
        }

        .file-list tr:hover {
            background: #f8f9fa;
        }

        .file-icon {
            width: 20px;
            text-align: center;
            margin-right: 0.5rem;
        }

        .file-name {
            cursor: pointer;
            color: #2563eb;
            text-decoration: none;
        }

        .file-name:hover {
            text-decoration: underline;
        }

        .file-actions {
            display: flex;
            gap: 0.25rem;
        }

        .btn {
            padding: 0.25rem 0.5rem;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8rem;
            text-decoration: none;
            display: inline-block;
        }

        .btn-primary {
            background: #2563eb;
            color: white;
        }

        .btn-danger {
            background: #dc3545;
            color: white;
        }

        .btn-secondary {
            background: #6c757d;
            color: white;
        }

        .btn:hover {
            opacity: 0.9;
        }

        .upload-area {
            padding: 2rem;
            border: 2px dashed #dee2e6;
            margin: 1rem;
            text-align: center;
            border-radius: 8px;
            transition: border-color 0.3s;
        }

        .upload-area:hover,
        .upload-area.dragover {
            border-color: #2563eb;
            background: #f0f4ff;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .stat-card {
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            text-align: center;
        }

        .stat-value {
            font-size: 1.5rem;
            font-weight: bold;
            color: #2563eb;
            margin-bottom: 0.5rem;
        }

        .stat-label {
            color: #6c757d;
            font-size: 0.9rem;
        }

        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
        }

        .modal.show {
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .modal-content {
            background: white;
            padding: 2rem;
            border-radius: 8px;
            max-width: 500px;
            width: 90%;
        }

        .form-group {
            margin-bottom: 1rem;
        }

        .form-group label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
        }

        .form-control {
            width: 100%;
            padding: 0.5rem;
            border: 1px solid #ced4da;
            border-radius: 4px;
        }

        .loading {
            text-align: center;
            padding: 2rem;
            color: #6c757d;
        }

        .empty-state {
            text-align: center;
            padding: 3rem;
            color: #6c757d;
        }

        .hidden {
            display: none;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📁 File Manager</h1>
        <div class="toolbar">
            <button class="btn btn-primary" onclick="showCreateDirectoryModal()">📁 New Folder</button>
            <button class="btn btn-primary" onclick="showUploadModal()">📤 Upload</button>
            <button class="btn btn-secondary" onclick="refreshFiles()">🔄 Refresh</button>
        </div>
    </div>

    <div class="container">
        <!-- Stats -->
        <div class="stats-grid" id="statsGrid">
            <div class="stat-card">
                <div class="stat-value" id="totalFiles">-</div>
                <div class="stat-label">Total Files</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="totalSize">-</div>
                <div class="stat-label">Total Size</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="freeSpace">-</div>
                <div class="stat-label">Free Space</div>
            </div>
        </div>

        <!-- File Manager -->
        <div class="file-manager">
            <div class="breadcrumb" id="breadcrumb">
                <span class="breadcrumb-item active" onclick="navigateToPath('')">🏠 Home</span>
            </div>

            <div class="file-list">
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Size</th>
                            <th>Modified</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="fileListBody">
                        <tr>
                            <td colspan="4" class="loading">Loading files...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Upload Modal -->
    <div class="modal" id="uploadModal">
        <div class="modal-content">
            <h3>Upload Files</h3>
            <div class="upload-area" id="uploadArea">
                <p>Drag and drop files here or click to select</p>
                <input type="file" id="fileInput" multiple style="display: none;">
                <button class="btn btn-primary" onclick="document.getElementById('fileInput').click()">Select Files</button>
            </div>
            <div style="margin-top: 1rem; text-align: right;">
                <button class="btn btn-secondary" onclick="closeModal('uploadModal')">Cancel</button>
            </div>
        </div>
    </div>

    <!-- Create Directory Modal -->
    <div class="modal" id="createDirModal">
        <div class="modal-content">
            <h3>Create Directory</h3>
            <div class="form-group">
                <label>Directory Name</label>
                <input type="text" class="form-control" id="dirName" placeholder="Enter directory name">
            </div>
            <div style="text-align: right;">
                <button class="btn btn-secondary" onclick="closeModal('createDirModal')">Cancel</button>
                <button class="btn btn-primary" onclick="createDirectory()">Create</button>
            </div>
        </div>
    </div>

    <script>
        let currentPath = '';
        let fileStats = {};

        async function loadFiles(path = '') {
            try {
                const response = await fetch(`/plugins/file_manager/files?path=${encodeURIComponent(path)}`);
                const data = await response.json();

                currentPath = path;
                updateBreadcrumb(path);
                displayFiles(data.items);

            } catch (error) {
                console.error('Error loading files:', error);
                displayError('Error loading files');
            }
        }

        async function loadStats() {
            try {
                const response = await fetch('/plugins/file_manager/stats');
                const data = await response.json();

                document.getElementById('totalFiles').textContent = data.total_files.toLocaleString();
                document.getElementById('totalSize').textContent = data.total_size_formatted;
                document.getElementById('freeSpace').textContent = data.disk_usage.free_formatted;

                fileStats = data;

            } catch (error) {
                console.error('Error loading stats:', error);
            }
        }

        function displayFiles(items) {
            const tbody = document.getElementById('fileListBody');

            if (!items || items.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="empty-state">No files in this directory</td></tr>';
                return;
            }

            tbody.innerHTML = items.map(item => {
                const icon = item.type === 'directory' ? '📁' : getFileIcon(item.name);
                const size = item.type === 'directory' ? '-' : formatFileSize(item.size);
                const modified = new Date(item.modified).toLocaleString();

                return `
                    <tr>
                        <td>
                            <span class="file-icon">${icon}</span>
                            <a href="#" class="file-name" onclick="handleFileClick('${item.path}', '${item.type}')">
                                ${item.name}
                            </a>
                        </td>
                        <td>${size}</td>
                        <td>${modified}</td>
                        <td class="file-actions">
                            ${item.type === 'file' ?
                                `<a href="/plugins/file_manager/files/download?path=${encodeURIComponent(item.path)}"
                                   class="btn btn-primary" title="Download">⬇️</a>` : ''
                            }
                            <button class="btn btn-danger" onclick="deleteFile('${item.path}')" title="Delete">🗑️</button>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        function handleFileClick(path, type) {
            if (type === 'directory') {
                navigateToPath(path);
            } else {
                // For files, trigger download
                window.open(`/plugins/file_manager/files/download?path=${encodeURIComponent(path)}`);
            }
        }

        function navigateToPath(path) {
            loadFiles(path);
        }

        function updateBreadcrumb(path) {
            const breadcrumb = document.getElementById('breadcrumb');
            const parts = path ? path.split('/').filter(p => p) : [];

            let html = '<span class="breadcrumb-item" onclick="navigateToPath(\'\')">🏠 Home</span>';

            let currentPath = '';
            for (let i = 0; i < parts.length; i++) {
                currentPath += (currentPath ? '/' : '') + parts[i];
                const isLast = i === parts.length - 1;

                html += ` / <span class="breadcrumb-item ${isLast ? 'active' : ''}"
                               onclick="navigateToPath('${currentPath}')">${parts[i]}</span>`;
            }

            breadcrumb.innerHTML = html;
        }

        function getFileIcon(filename) {
            const ext = filename.split('.').pop().toLowerCase();
            const icons = {
                'pdf': '📄', 'doc': '📝', 'docx': '📝', 'txt': '📄', 'md': '📝',
                'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️', 'svg': '🖼️',
                'zip': '📦', 'tar': '📦', 'gz': '📦',
                'json': '📋', 'xml': '📋', 'csv': '📊', 'xls': '📊', 'xlsx': '📊'
            };
            return icons[ext] || '📄';
        }

        function formatFileSize(bytes) {
            if (bytes === 0) return '0 B';
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(1024));
            return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
        }

        async function deleteFile(path) {
            if (!confirm('Are you sure you want to delete this item?')) {
                return;
            }

            try {
                const response = await fetch(`/plugins/file_manager/files?path=${encodeURIComponent(path)}`, {
                    method: 'DELETE'
                });

                if (response.ok) {
                    refreshFiles();
                } else {
                    const error = await response.json();
                    alert('Error: ' + error.detail);
                }

            } catch (error) {
                console.error('Error deleting file:', error);
                alert('Error deleting file');
            }
        }

        async function createDirectory() {
            const name = document.getElementById('dirName').value.trim();
            if (!name) {
                alert('Please enter a directory name');
                return;
            }

            try {
                const response = await fetch('/plugins/file_manager/files/create-directory', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: `path=${encodeURIComponent(currentPath)}&name=${encodeURIComponent(name)}`
                });

                if (response.ok) {
                    closeModal('createDirModal');
                    document.getElementById('dirName').value = '';
                    refreshFiles();
                } else {
                    const error = await response.json();
                    alert('Error: ' + error.detail);
                }

            } catch (error) {
                console.error('Error creating directory:', error);
                alert('Error creating directory');
            }
        }

        function setupUpload() {
            const fileInput = document.getElementById('fileInput');
            const uploadArea = document.getElementById('uploadArea');

            fileInput.addEventListener('change', handleFileUpload);

            // Drag and drop
            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });

            uploadArea.addEventListener('dragleave', () => {
                uploadArea.classList.remove('dragover');
            });

            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
                fileInput.files = e.dataTransfer.files;
                handleFileUpload({ target: fileInput });
            });
        }

        async function handleFileUpload(event) {
            const files = event.target.files;
            if (!files.length) return;

            for (const file of files) {
                const formData = new FormData();
                formData.append('file', file);
                formData.append('path', currentPath);

                try {
                    const response = await fetch('/plugins/file_manager/files/upload', {
                        method: 'POST',
                        body: formData
                    });

                    if (!response.ok) {
                        const error = await response.json();
                        alert(`Error uploading ${file.name}: ${error.detail}`);
                    }

                } catch (error) {
                    console.error('Upload error:', error);
                    alert(`Error uploading ${file.name}`);
                }
            }

            closeModal('uploadModal');
            refreshFiles();
            loadStats();
        }

        function showUploadModal() {
            document.getElementById('uploadModal').classList.add('show');
        }

        function showCreateDirectoryModal() {
            document.getElementById('createDirModal').classList.add('show');
        }

        function closeModal(modalId) {
            document.getElementById(modalId).classList.remove('show');
        }

        function refreshFiles() {
            loadFiles(currentPath);
            loadStats();
        }

        function displayError(message) {
            const tbody = document.getElementById('fileListBody');
            tbody.innerHTML = `<tr><td colspan="4" class="loading" style="color: red;">${message}</td></tr>`;
        }

        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            setupUpload();
            loadFiles();
            loadStats();
        });

        // Close modals when clicking outside
        window.addEventListener('click', function(event) {
            const modals = document.querySelectorAll('.modal');
            modals.forEach(modal => {
                if (event.target === modal) {
                    modal.classList.remove('show');
                }
            });
        });
    </script>
</body>
</html>
        """
