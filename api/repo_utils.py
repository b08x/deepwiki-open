import os
import logging
import fnmatch
from collections import defaultdict
from typing import List, Dict, Any
from api.config import load_repo_config

logger = logging.getLogger(__name__)

# ============================================================================
# INTELLIGENT FILE CHUNKING SYSTEM (Moved from api.py)
# ============================================================================


def should_exclude_dir(dir_name: str, excluded_patterns: List[str]) -> bool:
    """Check if directory should be excluded based on patterns."""
    # Always exclude hidden directories and common build/cache dirs
    if dir_name.startswith('.'):
        return True
    if dir_name in ['__pycache__', 'node_modules', '.venv', 'venv', 'env',
                    'image-cache', 'dist', 'build', 'target', 'out']:
        return True

    # Check against user-defined patterns
    for pattern in excluded_patterns:
        pattern_clean = pattern.strip('./').rstrip('/')
        if fnmatch.fnmatch(dir_name, pattern_clean):
            return True
    return False


def should_exclude_file(file_name: str, excluded_patterns: List[str]) -> bool:
    """Check if file should be excluded based on patterns."""
    # Always exclude hidden files and common files
    if file_name.startswith('.') or file_name == '__init__.py' or file_name == '.DS_Store':
        return True

    # Check against user-defined patterns
    for pattern in excluded_patterns:
        if fnmatch.fnmatch(file_name, pattern):
            return True
    return False


def collect_all_files(path: str, config: Dict) -> tuple[List[str], str]:
    """
    Collect ALL files from repository respecting include/exclude patterns.
    Also finds and reads README.md during the same walk.
    """
    all_files = []
    readme_content = ""
    excluded_dirs = config.get('excluded_dirs', [])
    excluded_files = config.get('excluded_files', [])

    logger.info(f"Collecting files from {path}")
    logger.info(f"Excluded dirs: {len(excluded_dirs)} patterns")
    logger.info(f"Excluded files: {len(excluded_files)} patterns")

    for root, dirs, files in os.walk(path):
        # Filter directories in-place
        dirs[:] = [d for d in dirs if not should_exclude_dir(d, excluded_dirs)]

        for file in files:
            if not should_exclude_file(file, excluded_files):
                rel_dir = os.path.relpath(root, path)
                rel_file = os.path.join(
                    rel_dir, file) if rel_dir != '.' else file
                all_files.append(rel_file)

                # Find README.md (case-insensitive) during the same walk
                if file.lower() == 'readme.md' and not readme_content:
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            readme_content = f.read()
                            logger.info(f"Found README.md at: {rel_file}")
                    except Exception as e:
                        logger.warning(
                            f"Could not read README.md at {rel_file}: {str(e)}")

    logger.info(f"Collected {len(all_files)} files after filtering")
    return all_files, readme_content


def group_files_by_directory(files: List[str]) -> Dict[str, List[str]]:
    """Group files by their parent directory."""
    by_dir = defaultdict(list)

    for file_path in files:
        dir_name = os.path.dirname(file_path)
        if not dir_name:
            dir_name = "root"
        by_dir[dir_name].append(file_path)

    return dict(by_dir)


def create_file_chunks(files: List[str], max_files_per_chunk: int = 500) -> List[Dict[str, Any]]:
    """
    Create intelligent chunks of files grouped by directory.
    Ensures no chunk exceeds max_files_per_chunk by splitting large directories.
    """
    # Group by directory
    by_dir = group_files_by_directory(files)

    chunks = []
    current_chunk_files = []
    current_chunk_dirs = []

    for dir_name, dir_files in sorted(by_dir.items()):
        # Handle large directories that exceed max_files_per_chunk on their own
        if len(dir_files) > max_files_per_chunk:
            # First, save current chunk if it has files
            if current_chunk_files:
                chunks.append({
                    'files': current_chunk_files[:],
                    'directories': current_chunk_dirs[:],
                    'file_count': len(current_chunk_files)
                })
                current_chunk_files = []
                current_chunk_dirs = []

            # Split large directory across multiple chunks
            logger.warning(
                f"Directory '{dir_name}' has {len(dir_files)} files, splitting across multiple chunks")
            for i in range(0, len(dir_files), max_files_per_chunk):
                chunk_slice = dir_files[i:i + max_files_per_chunk]
                chunks.append({
                    'files': chunk_slice,
                    'directories': [f"{dir_name} (part {i//max_files_per_chunk + 1})"],
                    'file_count': len(chunk_slice)
                })
        else:
            # Normal case: check if adding this directory would exceed limit
            if current_chunk_files and len(current_chunk_files) + len(dir_files) > max_files_per_chunk:
                # Save current chunk and start new one
                chunks.append({
                    'files': current_chunk_files[:],
                    'directories': current_chunk_dirs[:],
                    'file_count': len(current_chunk_files)
                })
                current_chunk_files = []
                current_chunk_dirs = []

            # Add directory to current chunk
            current_chunk_files.extend(dir_files)
            current_chunk_dirs.append(dir_name)

    # Add final chunk if it has files
    if current_chunk_files:
        chunks.append({
            'files': current_chunk_files,
            'directories': current_chunk_dirs,
            'file_count': len(current_chunk_files)
        })

    logger.info(f"Created {len(chunks)} chunks from {len(files)} files")
    for i, chunk in enumerate(chunks):
        logger.info(
            f"  Chunk {i+1}: {chunk['file_count']} files across {len(chunk['directories'])} directories")

    return chunks


def format_chunk_as_tree(chunk: Dict[str, Any]) -> str:
    """Format a chunk of files as a tree string."""
    files = chunk['files']
    tree_lines = sorted(files)

    # Add chunk metadata
    chunk_info = f"# Chunk contains {len(files)} files from {len(chunk['directories'])} directories\n"
    chunk_info += f"# Directories: {', '.join(chunk['directories'][:5])}"
    if len(chunk['directories']) > 5:
        chunk_info += f" ... and {len(chunk['directories']) - 5} more"
    chunk_info += "\n\n"

    return chunk_info + '\n'.join(tree_lines)


async def analyze_local_repository(path: str, chunk_size: int = 500, return_chunks: bool = False) -> Dict[str, Any]:
    """
    Shared logic to analyze a local repository. 
    Returns a dictionary with structure data or raises Exception.
    """
    if not path:
        raise ValueError("No path provided")

    if not os.path.isdir(path):
        raise ValueError(f"Directory not found: {path}")

    logger.info(
        f"Processing local repository at: {path} (chunk_size={chunk_size}, return_chunks={return_chunks})")

    # Load configuration from repo.json
    config_data = load_repo_config()
    file_filters = config_data.get('file_filters', {})

    # Collect ALL files respecting patterns and find README in one pass
    all_files, readme_content = collect_all_files(path, file_filters)

    # Decide whether to chunk based on repository size
    total_files = len(all_files)
    logger.info(f"Total files collected: {total_files}")

    if return_chunks or total_files > chunk_size:
        # Create intelligent chunks
        chunks = create_file_chunks(all_files, max_files_per_chunk=chunk_size)

        return {
            "chunked": True,
            "total_files": total_files,
            "chunk_count": len(chunks),
            "chunks": [
                {
                    "chunk_id": i,
                    "file_count": chunk['file_count'],
                    "directories": chunk['directories'],
                    "file_tree": format_chunk_as_tree(chunk)
                }
                for i, chunk in enumerate(chunks)
            ],
            "readme": readme_content
        }
    else:
        # Small repo, return as single tree
        file_tree_str = '\n'.join(sorted(all_files))
        return {
            "chunked": False,
            "total_files": total_files,
            "file_tree": file_tree_str,
            "readme": readme_content
        }
