"""
AST-based chunking for code files using LlamaIndex-inspired approach.
This provides semantic chunking that respects code structure.
"""

import ast
import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass

# Use a simple token counter if tiktoken is not available
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class CodeChunk:
    """Represents a semantically meaningful chunk of code."""
    content: str
    chunk_type: str  # 'function', 'class', 'module', 'import_block', 'comment_block'
    name: Optional[str] = None  # function/class name
    start_line: int = 0
    end_line: int = 0
    file_path: str = ""
    # imported modules/functions this chunk depends on
    dependencies: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class ASTChunker:
    """AST-based code chunker that creates semantically meaningful chunks."""

    def __init__(self,
                 max_chunk_size: int = 2000,
                 min_chunk_size: int = 100,
                 overlap_lines: int = 5,
                 preserve_structure: bool = True):
        """
        Initialize AST chunker.

        Args:
            max_chunk_size: Maximum tokens per chunk
            min_chunk_size: Minimum tokens per chunk  
            overlap_lines: Lines of overlap between chunks
            preserve_structure: Whether to keep related code together
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap_lines = overlap_lines
        self.preserve_structure = preserve_structure

        # Initialize token encoder with fallback
        if TIKTOKEN_AVAILABLE:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        else:
            # Simple fallback: approximate 4 chars per token
            self.encoding = None

    def chunk_file(self, file_path: str, content: str) -> List[CodeChunk]:
        """Chunk a single file based on its type and structure."""
        file_ext = Path(file_path).suffix.lower()

        # Route to appropriate chunker based on file type
        if file_ext == '.py':
            return self._chunk_python(file_path, content)
        elif file_ext in ['.js', '.ts', '.jsx', '.tsx']:
            return self._chunk_javascript(file_path, content)
        elif file_ext in ['.java', '.kt']:
            return self._chunk_java_kotlin(file_path, content)
        elif file_ext in ['.cpp', '.cc', '.cxx', '.c', '.h', '.hpp']:
            return self._chunk_cpp(file_path, content)
        elif file_ext in ['.rs']:
            return self._chunk_rust(file_path, content)
        elif file_ext in ['.go']:
            return self._chunk_go(file_path, content)
        elif file_ext in ['.md', '.rst', '.txt']:
            return self._chunk_markdown(file_path, content)
        elif file_ext in ['.json', '.yaml', '.yml', '.toml']:
            return self._chunk_config(file_path, content)
        else:
            # Fall back to text-based chunking
            return self._chunk_text(file_path, content)

    def _chunk_python(self, file_path: str, content: str) -> List[CodeChunk]:
        """Chunk Python code using AST analysis."""
        chunks = []

        try:
            tree = ast.parse(content)
            lines = content.split('\n')

            # Group imports at the top
            imports = []
            other_nodes = []

            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    imports.append(node)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    other_nodes.append(node)

            # Create import chunk if imports exist
            if imports:
                import_lines = []
                for imp in imports:
                    if hasattr(imp, 'lineno'):
                        import_lines.extend(range(imp.lineno - 1,
                                                  getattr(imp, 'end_lineno', imp.lineno)))

                if import_lines:
                    import_content = '\n'.join(
                        lines[min(import_lines):max(import_lines)+1])
                    chunks.append(CodeChunk(
                        content=import_content,
                        chunk_type='import_block',
                        start_line=min(import_lines) + 1,
                        end_line=max(import_lines) + 1,
                        file_path=file_path
                    ))

            # Process classes and functions
            for node in other_nodes:
                if isinstance(node, ast.ClassDef):
                    chunk = self._extract_class_chunk(node, lines, file_path)
                    if chunk:
                        chunks.append(chunk)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    chunk = self._extract_function_chunk(
                        node, lines, file_path)
                    if chunk:
                        chunks.append(chunk)

            # Handle module-level code
            module_code = self._extract_module_level_code(
                tree, lines, file_path)
            if module_code:
                chunks.extend(module_code)

        except SyntaxError as e:
            logger.warning(f"Could not parse Python file {file_path}: {e}")
            # Fall back to text chunking
            return self._chunk_text(file_path, content)

        return self._optimize_chunks(chunks)

    def _extract_class_chunk(self, node: ast.ClassDef,
                             lines: List[str], file_path: str) -> Optional[CodeChunk]:
        """Extract a class and its methods as a chunk."""
        start_line = node.lineno - 1
        end_line = getattr(node, 'end_lineno', node.lineno) - 1

        class_content = '\n'.join(lines[start_line:end_line + 1])

        # Check if chunk is too large, split methods if needed
        token_count = self._count_tokens(class_content)

        if token_count > self.max_chunk_size:
            # Split into method chunks
            method_chunks = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_chunk = self._extract_function_chunk(
                        item, lines, file_path)
                    if method_chunk:
                        method_chunks.append(method_chunk)
            return method_chunks if method_chunks else None

        # Extract dependencies (imports used in class)
        dependencies = self._extract_dependencies(node)

        return CodeChunk(
            content=class_content,
            chunk_type='class',
            name=node.name,
            start_line=start_line + 1,
            end_line=end_line + 1,
            file_path=file_path,
            dependencies=dependencies
        )

    def _extract_function_chunk(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
                                lines: List[str], file_path: str) -> Optional[CodeChunk]:
        """Extract a function as a chunk."""
        start_line = node.lineno - 1
        end_line = getattr(node, 'end_lineno', node.lineno) - 1

        function_content = '\n'.join(lines[start_line:end_line + 1])

        # Extract dependencies
        dependencies = self._extract_dependencies(node)

        return CodeChunk(
            content=function_content,
            chunk_type='function',
            name=node.name,
            start_line=start_line + 1,
            end_line=end_line + 1,
            file_path=file_path,
            dependencies=dependencies
        )

    def _extract_dependencies(self, node) -> List[str]:
        """Extract dependencies (imported names) used in this node."""
        dependencies = []

        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                dependencies.append(child.id)
            elif isinstance(child, ast.Attribute):
                # Handle module.function calls
                if isinstance(child.value, ast.Name):
                    dependencies.append(f"{child.value.id}.{child.attr}")

        return list(set(dependencies))  # Remove duplicates

    def _extract_module_level_code(self, tree: ast.AST,
                                   lines: List[str], file_path: str) -> List[CodeChunk]:
        """Extract module-level code that's not in classes or functions."""
        chunks = []

        # Find lines not covered by classes/functions
        covered_lines = set()

        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.Import, ast.ImportFrom)):
                start = node.lineno - 1
                end = getattr(node, 'end_lineno', node.lineno) - 1
                covered_lines.update(range(start, end + 1))

        # Group uncovered lines into chunks
        uncovered_lines = []
        for i, line in enumerate(lines):
            if i not in covered_lines and line.strip():
                uncovered_lines.append((i, line))

        if uncovered_lines:
            # Group consecutive lines
            current_chunk_lines = []
            current_start = None

            for line_num, line in uncovered_lines:
                if current_start is None:
                    current_start = line_num
                    current_chunk_lines = [line]
                elif line_num == current_start + len(current_chunk_lines):
                    current_chunk_lines.append(line)
                else:
                    # Gap found, save current chunk and start new one
                    if current_chunk_lines:
                        chunk_content = '\n'.join(current_chunk_lines)
                        if self._count_tokens(chunk_content) > self.min_chunk_size:
                            chunks.append(CodeChunk(
                                content=chunk_content,
                                chunk_type='module',
                                start_line=current_start + 1,
                                end_line=current_start +
                                len(current_chunk_lines),
                                file_path=file_path
                            ))

                    current_start = line_num
                    current_chunk_lines = [line]

            # Add final chunk
            if current_chunk_lines:
                chunk_content = '\n'.join(current_chunk_lines)
                if self._count_tokens(chunk_content) > self.min_chunk_size:
                    chunks.append(CodeChunk(
                        content=chunk_content,
                        chunk_type='module',
                        start_line=current_start + 1,
                        end_line=current_start + len(current_chunk_lines),
                        file_path=file_path
                    ))

        return chunks

    def _chunk_javascript(self, file_path: str, content: str) -> List[CodeChunk]:
        """Chunk JavaScript/TypeScript using regex patterns (simplified AST)."""
        # This is a simplified implementation
        # For production, you'd want to use a proper JS/TS parser like babel or esprima
        chunks = []
        lines = content.split('\n')

        # Find function and class boundaries using regex
        import re

        function_pattern = r'^(export\s+)?(async\s+)?function\s+(\w+)|^(export\s+)?const\s+(\w+)\s*=\s*(async\s+)?\('
        class_pattern = r'^(export\s+)?class\s+(\w+)'

        current_chunk = []
        current_type = 'module'
        current_name = None
        brace_count = 0
        in_function = False

        for i, line in enumerate(lines):
            if re.match(function_pattern, line.strip()):
                # Start of function
                if current_chunk:
                    chunks.append(self._create_js_chunk(
                        current_chunk, current_type, current_name, file_path
                    ))
                current_chunk = [line]
                current_type = 'function'
                match = re.match(function_pattern, line.strip())
                current_name = match.group(3) or match.group(5)
                brace_count = line.count('{') - line.count('}')
                in_function = True
            elif re.match(class_pattern, line.strip()):
                # Start of class
                if current_chunk:
                    chunks.append(self._create_js_chunk(
                        current_chunk, current_type, current_name, file_path
                    ))
                current_chunk = [line]
                current_type = 'class'
                match = re.match(class_pattern, line.strip())
                current_name = match.group(2)
                brace_count = line.count('{') - line.count('}')
                in_function = True
            else:
                current_chunk.append(line)
                if in_function:
                    brace_count += line.count('{') - line.count('}')
                    if brace_count <= 0:
                        # End of function/class
                        chunks.append(self._create_js_chunk(
                            current_chunk, current_type, current_name, file_path
                        ))
                        current_chunk = []
                        current_type = 'module'
                        current_name = None
                        in_function = False

        # Add remaining content
        if current_chunk:
            chunks.append(self._create_js_chunk(
                current_chunk, current_type, current_name, file_path
            ))

        return self._optimize_chunks(chunks)

    def _create_js_chunk(self, lines: List[str], chunk_type: str,
                         name: Optional[str], file_path: str) -> CodeChunk:
        """Create a JavaScript chunk from lines."""
        content = '\n'.join(lines)
        return CodeChunk(
            content=content,
            chunk_type=chunk_type,
            name=name,
            file_path=file_path
        )

    def _chunk_markdown(self, file_path: str, content: str) -> List[CodeChunk]:
        """Chunk Markdown by headers and sections."""
        chunks = []
        lines = content.split('\n')

        current_chunk = []
        current_header = None
        header_level = 0

        for line in lines:
            if line.startswith('#'):
                # Header found
                if current_chunk:
                    chunks.append(CodeChunk(
                        content='\n'.join(current_chunk),
                        chunk_type='section',
                        name=current_header,
                        file_path=file_path
                    ))

                current_header = line.strip('#').strip()
                header_level = len(line) - len(line.lstrip('#'))
                current_chunk = [line]
            else:
                current_chunk.append(line)

        # Add final chunk
        if current_chunk:
            chunks.append(CodeChunk(
                content='\n'.join(current_chunk),
                chunk_type='section',
                name=current_header,
                file_path=file_path
            ))

        return chunks

    def _chunk_config(self, file_path: str, content: str) -> List[CodeChunk]:
        """Chunk configuration files as single units (they're usually coherent)."""
        return [CodeChunk(
            content=content,
            chunk_type='config',
            name=Path(file_path).name,
            file_path=file_path
        )]

    def _chunk_text(self, file_path: str, content: str) -> List[CodeChunk]:
        """Fall back to simple text chunking."""
        chunks = []
        lines = content.split('\n')

        current_chunk = []
        current_tokens = 0

        for line in lines:
            line_tokens = self._count_tokens(line)

            if current_tokens + line_tokens > self.max_chunk_size and current_chunk:
                chunks.append(CodeChunk(
                    content='\n'.join(current_chunk),
                    chunk_type='text',
                    file_path=file_path
                ))
                current_chunk = []
                current_tokens = 0

            current_chunk.append(line)
            current_tokens += line_tokens

        if current_chunk:
            chunks.append(CodeChunk(
                content='\n'.join(current_chunk),
                chunk_type='text',
                file_path=file_path
            ))

        return chunks

    def _optimize_chunks(self, chunks: List[CodeChunk]) -> List[CodeChunk]:
        """Optimize chunks by merging small ones and splitting large ones."""
        optimized = []

        for chunk in chunks:
            token_count = self._count_tokens(chunk.content)

            if token_count > self.max_chunk_size:
                # Split large chunk
                split_chunks = self._split_large_chunk(chunk)
                optimized.extend(split_chunks)
            elif token_count < self.min_chunk_size and optimized:
                # Merge with previous chunk if it won't exceed max size
                prev_chunk = optimized[-1]
                prev_tokens = self._count_tokens(prev_chunk.content)

                if prev_tokens + token_count <= self.max_chunk_size:
                    # Merge chunks
                    merged_content = f"{prev_chunk.content}\n\n{chunk.content}"
                    optimized[-1] = CodeChunk(
                        content=merged_content,
                        chunk_type='merged',
                        file_path=chunk.file_path,
                        start_line=prev_chunk.start_line or chunk.start_line,
                        end_line=chunk.end_line or prev_chunk.end_line,
                        dependencies=list(
                            set(prev_chunk.dependencies + chunk.dependencies))
                    )
                else:
                    optimized.append(chunk)
            else:
                optimized.append(chunk)

        return optimized

    def _split_large_chunk(self, chunk: CodeChunk) -> List[CodeChunk]:
        """Split a chunk that's too large."""
        lines = chunk.content.split('\n')
        split_chunks = []

        current_lines = []
        current_tokens = 0

        for line in lines:
            line_tokens = self._count_tokens(line)

            if current_tokens + line_tokens > self.max_chunk_size and current_lines:
                split_chunks.append(CodeChunk(
                    content='\n'.join(current_lines),
                    chunk_type=f"{chunk.chunk_type}_split",
                    name=f"{chunk.name}_part_{len(split_chunks) + 1}" if chunk.name else None,
                    file_path=chunk.file_path,
                    dependencies=chunk.dependencies
                ))
                current_lines = []
                current_tokens = 0

            current_lines.append(line)
            current_tokens += line_tokens

        if current_lines:
            split_chunks.append(CodeChunk(
                content='\n'.join(current_lines),
                chunk_type=f"{chunk.chunk_type}_split",
                name=f"{chunk.name}_part_{len(split_chunks) + 1}" if chunk.name else None,
                file_path=chunk.file_path,
                dependencies=chunk.dependencies
            ))

        return split_chunks

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text with fallback for when tiktoken is not available."""
        if TIKTOKEN_AVAILABLE and self.encoding:
            return len(self.encoding.encode(text))
        else:
            # Simple approximation: 4 characters per token
            return len(text) // 4

    # Placeholder methods for other languages
    def _chunk_java_kotlin(self, file_path: str, content: str) -> List[CodeChunk]:
        """Chunk Java/Kotlin code."""
        # Simplified implementation - in production, use proper parsers
        return self._chunk_text(file_path, content)

    def _chunk_cpp(self, file_path: str, content: str) -> List[CodeChunk]:
        """Chunk C++ code."""
        return self._chunk_text(file_path, content)

    def _chunk_rust(self, file_path: str, content: str) -> List[CodeChunk]:
        """Chunk Rust code."""
        return self._chunk_text(file_path, content)

    def _chunk_go(self, file_path: str, content: str) -> List[CodeChunk]:
        """Chunk Go code."""
        return self._chunk_text(file_path, content)

# ============================================================================
# ADALFLOW INTEGRATION
# ============================================================================

import adalflow as adal
from adalflow import Document


class ASTTextSplitter(adal.Component):
    """
    AdalFlow component that splits documents using AST-based chunking.
    This component acts as a bridge between the ASTChunker and AdalFlow pipelines.
    """

    def __init__(self,
                 split_by: str = "ast",
                 chunk_size: int = 2000,
                 chunk_overlap: int = 200,
                 min_chunk_size: int = 100,
                 **kwargs):
        """
        Initialize the AST text splitter.

        Args:
            split_by: Must be "ast" to use this splitter
            chunk_size: Maximum tokens per chunk
            chunk_overlap: Number of tokens to overlap (approximated via lines in ASTChunker)
            min_chunk_size: Minimum tokens per chunk
            **kwargs: Additional arguments for ASTChunker
        """
        super().__init__()
        self.split_by = split_by
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

        # Initialize the underlying ASTChunker
        # Note: ASTChunker uses lines for overlap, so we convert overlap tokens to lines (approx)
        overlap_lines = chunk_overlap // 10  # Very rough approximation
        self.chunker = ASTChunker(
            max_chunk_size=chunk_size,
            min_chunk_size=min_chunk_size,
            overlap_lines=overlap_lines,
            **kwargs
        )

    def call(self, documents: List[Document]) -> List[Document]:
        """
        Split a list of documents into chunks.

        Args:
            documents: List of Document objects to be split

        Returns:
            List of new Document objects representing the chunks
        """
        all_chunks = []

        for doc in documents:
            file_path = doc.meta_data.get('file_path', 'unknown')
            content = doc.text

            # Split the file using ASTChunker
            try:
                code_chunks = self.chunker.chunk_file(file_path, content)

                for i, chunk in enumerate(code_chunks):
                    # Create a new Document for each chunk
                    chunk_doc = Document(
                        text=chunk.content,
                        id=f"{doc.id}_chunk_{i}",
                        meta_data={
                            **doc.meta_data,
                            'chunk_id': i,
                            'chunk_type': chunk.chunk_type,
                            'chunk_name': chunk.name,
                            'start_line': chunk.start_line,
                            'end_line': chunk.end_line,
                            'dependencies': chunk.dependencies,
                            'parent_doc_id': doc.id
                        }
                    )
                    all_chunks.append(chunk_doc)
            except Exception as e:
                logger.error(f"Error splitting document {file_path}: {e}")
                # Fallback: if AST chunking fails, keep the original document
                all_chunks.append(doc)

        return all_chunks


class EnhancedRAGRetriever(adal.Component):
    """
    Enhanced retriever that can leverage AST-specific metadata for better retrieval.
    Currently acts as a pass-through to the base retriever but provides
    a foundation for structural code search.
    """

    def __init__(self, base_retriever: adal.Component):
        """
        Initialize the enhanced retriever.

        Args:
            base_retriever: The underlying FAISSRetriever or similar
        """
        super().__init__()
        self.base_retriever = base_retriever

    def call(self, query: str, **kwargs) -> List[Any]:
        """
        Retrieve relevant document chunks for a query.

        Args:
            query: The user query
            **kwargs: Additional retrieval arguments

        Returns:
            List of retrieved chunks
        """
        # For now, just pass through to the base retriever
        # In the future, this can be expanded with logic to:
        # 1. Boost results from implementation files
        # 2. Re-rank based on dependency graphs
        # 3. Filter by chunk type (e.g. only return functions)
        return self.base_retriever.call(query, **kwargs)
