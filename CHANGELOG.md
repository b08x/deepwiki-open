## [unreleased]

### 🚀 Features

- Add themes toggle to switch dark mode
- Adding support for Ollama client
- Fix bug and add Local Ollama toggle to FE
- Completed support for both local ollama and openAI/Gemini
- Add Bitbucket support
- Fix a bug
- Add local folder support
- Fix bug
- Provide user custom configuration (#74)
- Fix Ollama client (#101)
- AWS Bedrock Initial Commit (#99)
- *(embedder)* Make embedder support openai compatible model like qwen (#169)
- Now with delete (#177)
- *(ci)* Enable multi-arch Docker image builds and conditional login (#160)
- Commonizing logging into one spot (#180)
- Implement authorization mode for wiki generation (#185)
- Add language configuration and API validation (#186)
- Lang config loaded by file name (#187)
- Add Portuguese Brazilian (pt-BR) language support  (#197)
- Add friendly tips for auth code validation (#201)
- Integrate Azure OpenAI support (#221)
- Add model existence check for Ollama integration (#227)
- Update github api with Enterprise endpoint support (#239)
- Save wiki section structure to server cache (#257)
- Cache repository configurations in frontend (#254)
- Optimize clone speed with `clone --depth=1 --single-branch` (#307)
- *(wiki)* Implement AST-based chunking and enhanced processing pipeline
- Update AI prompt instructions to enforce denotative, precise, and critical analysis.
- *(api)* Implement multi-provider support and comprehensive validation system
- *(provider)* Integrate validation and refresh APIs with UI updates

### 🐛 Bug Fixes

- UI changes
- Customized API port
- Add git to docker Image to fix git clone errors
- Repo_url is empty when ask but failed (#128)
- Default model is missing in asking (#149)
- Support token re-input when refreshing wiki for private repositories (#167)
- Corrected non-default port extraction for self-hosted gitlab (#209)
- *(repo_name)* Fix generate error for the same repo name but different owner name (#203)
- Prevent infinite logging loop caused by file changes triggering log writes (#210)
- Add API routes for auth/validate and auth/status to fix 404 errors (#199)
- Compatible for old version wiki cache #215 (#218)
- Select force utf-8 in japanese enviroment (#242)
- Move log file to parent directory to avoid infinite logging loop (#250)
- Add IgnoreLogChangeDetectedFilter for logging to ignore changes (#253)
- *(repo-page)* Pass 'include' params to API (#268)
- Detection of repository type for self hosted instances (#381)
- Update citation format in documentation for source references
- *(rag)* Robustify RAG and embedding pipeline for Ollama limits and AdalFlow data structures

### 💼 Other

- GA pipeline error.
- Added Gitlab Support
- Private Repository Support.
- Support Sequence Diagram
- Docker Compose env fix, improved diagram visual.
- Add better Github example.
- GA, env quirks
- Readme update.
- Update Example.
- Support Markdown/JSON Wiki Export.
- Explicit Port Specification.
- Improve codeblocks and remove Mermaid Diagram errors.
- Improve Diagram, Fix Page Styling
- EdgeLabel color
- Introduce DeepResearch and Ask Functionality
- Lint Error
- Dynamic Route Handling.
- Temp
- Add Star History.
- Language Support.
- OpenRouter Support V1.
- Make package public when merged to main branch.
- Revert GA build.
- Ollama Setup Instruction.
- Wiki Caching.
- More robust XML parsing.
- Add custom OpenAI provider and simplified/intuitive model selection.
- Remove redundant generation in RAG, improve context.
- Support self-hosted gitlab instance (#91)
- Lint
- Exclude unnecessary files/directories for local embedding to work.
- Add tip.md
- WSS. (#118)
- Update .gitignore to exclude virtual environment files (#158)
- Resolve overlapping "Ask" button and improve input field text visibility (#165)
- Ensure multi-arch Docker images by manually merging manifests (#184)
- Grab Default Branch instead of main/master.
- Rag memleak with weakref (#294)

### 🚜 Refactor

- Remove unused models

### 📚 Documentation

- Change valid heading size
- Add env instructions for Ollama if not local (#141)

### ⚙️ Miscellaneous Tasks

- Missing aiohttp in python requirements
- Change SERVER_BASE_URL
- Removing calls to curl, replacing with requests parity (#179)
- *(infra)* Add Podman support and update Docker configuration
