## [0.1.25] - 2025-12-07

### Changes
- Release v0.1.24
- Update community install to build from source instead of registry (#49)
- Fix model editing UI and OpenAI tool calling issues (#48)
- Improve agent execution UI - compact intermediate steps (#46)
- Add automated upgrade system for community edition (#45)
- Review codebase and architecture (#44)
- PRD-110: Consolidate Linear MCP documentation
- PRD-103: Implement Linear Agent Workflow with fire-and-forget webhook execution
- PRD-102: Enhance Linear webhook trigger for agent session events
- PRD-101: Create Linear analyst agent definition
- PRD-111: Align Linear MCP with backend refactoring style standards
- PRD-100: Implement Linear MCP Server (#38)
- PRD-106: Fix incomplete dependency injection and config path resolution (#37)
- PRD-98: Implement token tracking and cost calculation (#36)
- PRD-97: Playground History UI/UX Enhancements (#35)
- PRD-88: Implement backend cancellation for agent executions (#32)
- PRD-96: Improve Linear webhook trigger security and reliability
- PRD-89: Show full agent reasoning and messages in playground UI (#33)
- PRD-87: Add stop button to cancel running agent executions (#31)
- PRD-87: OpenAI Integration & Improved Messaging UX (#30)
- PRD-86: Production-ready model config & code quality fixes (#29)
- PRD-85: Fix MCP schema parsing and externalize agent config (#28)
- PRD-75: Fix license headers in new files
- PRD-75: Simplify workflow UI - remove examples, move execute to header
- PRD-75: Add Python unit tests for workflow endpoints
- PRD-75: Add unit tests for workflow save/load functionality
- PRD-75: Implement workflow save/load with backend persistence
- PRD-75: Implement enhanced execution visualization with tests
- PRD-75: Add unit tests for NodeConfigModal
- PRD-75: Implement inline parameter editing with NodeConfigModal
- PRD-75: Add unit tests for drag-and-drop functionality
- PRD-75: Implement drag-and-drop node creation
- PRD-75: Complete Shadcn/Tailwind migration for workflow UI
- feat: Transform playground console logs to conversational agent status UI
- Add token usage and iteration details to progress log
- Add real-time progress logging to Playground page
- Add -nuke option to clean-restart.sh for forced rebuild
- chore: Add missing copyright headers [skip ci]
- PRD-71: Apply black formatting and add unit tests
- PRD-71: Implement SSE streaming for real-time team execution progress
- PRD-74: Add comprehensive planning documentation for PRD-61
- PRD-73: Add UI mockup design iterations for ADCL Control Center (#24)
- PRD-70: Fix deprecated Claude model IDs across platform (#22)
- PRD-45: Cleanup Memory UI - Remove sidebar, add navigation submenu (#21)
- PRD-62: Implement workflow backend and fix critical platform bugs (#20)
- PRD-35: Implement complete trigger system for workflow and team automation
- Feature/bugfix (#18)
- chore: Add missing copyright headers [skip ci]
- PRD-42 cleanup and tech debt fun just basic cleaning of base repo and scrubbing through leftover hardcodes; move the crufty stuff out of base. 1.  Create a centralized config system - Add a configs/services.yaml file for all service configurations 2.  Update .env - Add all missing environment variables 3.  Fix the code - Update all identified files to use configuration instead of hardcodes Will have to deal with CORS at some-point; will leave out for now.
- PRD-26: Add copyright headers to all source files (#16)
- added in history to chat; extensive backend/frontend changes for initial (#15)
- Feature/cleanup (#14)
- mostly clean up in mcp; re-organized to make them truly modular (#13)
- quick spec writeup based on core arch; (#12)

## [0.1.24] - 2025-12-07

### Changes
- Update community install to build from source instead of registry (#49)
- Fix model editing UI and OpenAI tool calling issues (#48)
- Improve agent execution UI - compact intermediate steps (#46)
- Add automated upgrade system for community edition (#45)
- Review codebase and architecture (#44)
- PRD-110: Consolidate Linear MCP documentation
- PRD-103: Implement Linear Agent Workflow with fire-and-forget webhook execution
- PRD-102: Enhance Linear webhook trigger for agent session events
- PRD-101: Create Linear analyst agent definition
- PRD-111: Align Linear MCP with backend refactoring style standards
- PRD-100: Implement Linear MCP Server (#38)
- PRD-106: Fix incomplete dependency injection and config path resolution (#37)
- PRD-98: Implement token tracking and cost calculation (#36)
- PRD-97: Playground History UI/UX Enhancements (#35)
- PRD-88: Implement backend cancellation for agent executions (#32)
- PRD-96: Improve Linear webhook trigger security and reliability
- PRD-89: Show full agent reasoning and messages in playground UI (#33)
- PRD-87: Add stop button to cancel running agent executions (#31)
- PRD-87: OpenAI Integration & Improved Messaging UX (#30)
- PRD-86: Production-ready model config & code quality fixes (#29)
- PRD-85: Fix MCP schema parsing and externalize agent config (#28)
- PRD-75: Fix license headers in new files
- PRD-75: Simplify workflow UI - remove examples, move execute to header
- PRD-75: Add Python unit tests for workflow endpoints
- PRD-75: Add unit tests for workflow save/load functionality
- PRD-75: Implement workflow save/load with backend persistence
- PRD-75: Implement enhanced execution visualization with tests
- PRD-75: Add unit tests for NodeConfigModal
- PRD-75: Implement inline parameter editing with NodeConfigModal
- PRD-75: Add unit tests for drag-and-drop functionality
- PRD-75: Implement drag-and-drop node creation
- PRD-75: Complete Shadcn/Tailwind migration for workflow UI
- feat: Transform playground console logs to conversational agent status UI
- Add token usage and iteration details to progress log
- Add real-time progress logging to Playground page
- Add -nuke option to clean-restart.sh for forced rebuild
- chore: Add missing copyright headers [skip ci]
- PRD-71: Apply black formatting and add unit tests
- PRD-71: Implement SSE streaming for real-time team execution progress
- PRD-74: Add comprehensive planning documentation for PRD-61
- PRD-73: Add UI mockup design iterations for ADCL Control Center (#24)
- PRD-70: Fix deprecated Claude model IDs across platform (#22)
- PRD-45: Cleanup Memory UI - Remove sidebar, add navigation submenu (#21)
- PRD-62: Implement workflow backend and fix critical platform bugs (#20)
- PRD-35: Implement complete trigger system for workflow and team automation
- Feature/bugfix (#18)
- chore: Add missing copyright headers [skip ci]
- PRD-42 cleanup and tech debt fun just basic cleaning of base repo and scrubbing through leftover hardcodes; move the crufty stuff out of base. 1.  Create a centralized config system - Add a configs/services.yaml file for all service configurations 2.  Update .env - Add all missing environment variables 3.  Fix the code - Update all identified files to use configuration instead of hardcodes Will have to deal with CORS at some-point; will leave out for now.
- PRD-26: Add copyright headers to all source files (#16)
- added in history to chat; extensive backend/frontend changes for initial (#15)
- Feature/cleanup (#14)
- mostly clean up in mcp; re-organized to make them truly modular (#13)
- quick spec writeup based on core arch; (#12)

## [0.1.23] - 2025-12-05

### Changes
- Copy registries.conf to public repo
- Add registries.conf volume mount to orchestrator

## [0.1.22] - 2025-12-05

### Changes
- Fix MCP names - use underscores not hyphens

## [0.1.21] - 2025-12-05

### Changes
- Complete .env.example based on DEV environment

## [0.1.20] - 2025-12-05

### Changes
- Fix .env.example and registry health check
- Complete .env.example with all required variables

## [0.1.19] - 2025-12-05

### Changes


## [0.1.18] - 2025-12-05

### Changes
- Add configs volume mount to orchestrator

## [0.1.17] - 2025-12-05

### Changes
- Fix orchestrator startup - copy configs directory
- Simplify community install - no hidden dirs, include all scripts

## [0.1.16] - 2025-12-05

### Changes
- Fix community release - add orchestrator and MCP support

## [0.1.15] - 2025-12-05

### Changes


## [0.1.14] - 2025-12-05

### Changes


## [0.1.13] - 2025-12-05

### Changes


## [0.1.12] - 2025-12-05

### Changes


## [0.1.11] - 2025-12-05

### Changes


## [0.1.10] - 2025-12-05

### Changes


## [0.1.9] - 2025-12-05

### Changes


## [0.1.8] - 2025-12-05

### Changes


## [0.1.7] - 2025-12-04

### Changes


## [0.1.6] - 2025-12-04

### Changes


## [0.1.5] - 2025-12-04

### Changes
- PRD-107: Add smart versioning with auto-increment
- PRD-107: Simplify to S3-only distribution (remove GHCR)
- PRD-107: Add comprehensive packaging and distribution strategy
- PRD-107: Add S3 release infrastructure and publishing scripts
- PRD-107: Implement easy upgrades and deployment system
- PRD-110: Consolidate Linear MCP documentation
- PRD-103: Implement Linear Agent Workflow with fire-and-forget webhook execution
- PRD-102: Enhance Linear webhook trigger for agent session events
- PRD-101: Create Linear analyst agent definition
- PRD-111: Align Linear MCP with backend refactoring style standards
- PRD-100: Implement Linear MCP Server (#38)
- PRD-106: Fix incomplete dependency injection and config path resolution (#37)
- PRD-98: Implement token tracking and cost calculation (#36)
- PRD-97: Playground History UI/UX Enhancements (#35)
- PRD-88: Implement backend cancellation for agent executions (#32)
- PRD-96: Improve Linear webhook trigger security and reliability
- PRD-89: Show full agent reasoning and messages in playground UI (#33)
- PRD-87: Add stop button to cancel running agent executions (#31)
- PRD-87: OpenAI Integration & Improved Messaging UX (#30)
- PRD-86: Production-ready model config & code quality fixes (#29)
- PRD-85: Fix MCP schema parsing and externalize agent config (#28)
- PRD-75: Fix license headers in new files
- PRD-75: Simplify workflow UI - remove examples, move execute to header
- PRD-75: Add Python unit tests for workflow endpoints
- PRD-75: Add unit tests for workflow save/load functionality
- PRD-75: Implement workflow save/load with backend persistence
- PRD-75: Implement enhanced execution visualization with tests
- PRD-75: Add unit tests for NodeConfigModal
- PRD-75: Implement inline parameter editing with NodeConfigModal
- PRD-75: Add unit tests for drag-and-drop functionality
- PRD-75: Implement drag-and-drop node creation
- PRD-75: Complete Shadcn/Tailwind migration for workflow UI
- feat: Transform playground console logs to conversational agent status UI
- Add token usage and iteration details to progress log
- Add real-time progress logging to Playground page
- Add -nuke option to clean-restart.sh for forced rebuild
- chore: Add missing copyright headers [skip ci]
- PRD-71: Apply black formatting and add unit tests
- PRD-71: Implement SSE streaming for real-time team execution progress
- PRD-74: Add comprehensive planning documentation for PRD-61
- PRD-73: Add UI mockup design iterations for ADCL Control Center (#24)
- PRD-70: Fix deprecated Claude model IDs across platform (#22)
- PRD-45: Cleanup Memory UI - Remove sidebar, add navigation submenu (#21)
- PRD-62: Implement workflow backend and fix critical platform bugs (#20)
- PRD-35: Implement complete trigger system for workflow and team automation
- Feature/bugfix (#18)
- chore: Add missing copyright headers [skip ci]
- PRD-42 cleanup and tech debt fun just basic cleaning of base repo and scrubbing through leftover hardcodes; move the crufty stuff out of base. 1.  Create a centralized config system - Add a configs/services.yaml file for all service configurations 2.  Update .env - Add all missing environment variables 3.  Fix the code - Update all identified files to use configuration instead of hardcodes Will have to deal with CORS at some-point; will leave out for now.
- PRD-26: Add copyright headers to all source files (#16)
- added in history to chat; extensive backend/frontend changes for initial (#15)
- Feature/cleanup (#14)
- mostly clean up in mcp; re-organized to make them truly modular (#13)
- quick spec writeup based on core arch; (#12)

## [0.1.4] - 2025-12-04

### Changes
- PRD-107: Add smart versioning with auto-increment
- PRD-107: Simplify to S3-only distribution (remove GHCR)
- PRD-107: Add comprehensive packaging and distribution strategy
- PRD-107: Add S3 release infrastructure and publishing scripts
- PRD-107: Implement easy upgrades and deployment system
- PRD-110: Consolidate Linear MCP documentation
- PRD-103: Implement Linear Agent Workflow with fire-and-forget webhook execution
- PRD-102: Enhance Linear webhook trigger for agent session events
- PRD-101: Create Linear analyst agent definition
- PRD-111: Align Linear MCP with backend refactoring style standards
- PRD-100: Implement Linear MCP Server (#38)
- PRD-106: Fix incomplete dependency injection and config path resolution (#37)
- PRD-98: Implement token tracking and cost calculation (#36)
- PRD-97: Playground History UI/UX Enhancements (#35)
- PRD-88: Implement backend cancellation for agent executions (#32)
- PRD-96: Improve Linear webhook trigger security and reliability
- PRD-89: Show full agent reasoning and messages in playground UI (#33)
- PRD-87: Add stop button to cancel running agent executions (#31)
- PRD-87: OpenAI Integration & Improved Messaging UX (#30)
- PRD-86: Production-ready model config & code quality fixes (#29)
- PRD-85: Fix MCP schema parsing and externalize agent config (#28)
- PRD-75: Fix license headers in new files
- PRD-75: Simplify workflow UI - remove examples, move execute to header
- PRD-75: Add Python unit tests for workflow endpoints
- PRD-75: Add unit tests for workflow save/load functionality
- PRD-75: Implement workflow save/load with backend persistence
- PRD-75: Implement enhanced execution visualization with tests
- PRD-75: Add unit tests for NodeConfigModal
- PRD-75: Implement inline parameter editing with NodeConfigModal
- PRD-75: Add unit tests for drag-and-drop functionality
- PRD-75: Implement drag-and-drop node creation
- PRD-75: Complete Shadcn/Tailwind migration for workflow UI
- feat: Transform playground console logs to conversational agent status UI
- Add token usage and iteration details to progress log
- Add real-time progress logging to Playground page
- Add -nuke option to clean-restart.sh for forced rebuild
- chore: Add missing copyright headers [skip ci]
- PRD-71: Apply black formatting and add unit tests
- PRD-71: Implement SSE streaming for real-time team execution progress
- PRD-74: Add comprehensive planning documentation for PRD-61
- PRD-73: Add UI mockup design iterations for ADCL Control Center (#24)
- PRD-70: Fix deprecated Claude model IDs across platform (#22)
- PRD-45: Cleanup Memory UI - Remove sidebar, add navigation submenu (#21)
- PRD-62: Implement workflow backend and fix critical platform bugs (#20)
- PRD-35: Implement complete trigger system for workflow and team automation
- Feature/bugfix (#18)
- chore: Add missing copyright headers [skip ci]
- PRD-42 cleanup and tech debt fun just basic cleaning of base repo and scrubbing through leftover hardcodes; move the crufty stuff out of base. 1.  Create a centralized config system - Add a configs/services.yaml file for all service configurations 2.  Update .env - Add all missing environment variables 3.  Fix the code - Update all identified files to use configuration instead of hardcodes Will have to deal with CORS at some-point; will leave out for now.
- PRD-26: Add copyright headers to all source files (#16)
- added in history to chat; extensive backend/frontend changes for initial (#15)
- Feature/cleanup (#14)
- mostly clean up in mcp; re-organized to make them truly modular (#13)
- quick spec writeup based on core arch; (#12)

## [0.1.3] - 2025-12-04

### Changes
- PRD-107: Add smart versioning with auto-increment
- PRD-107: Simplify to S3-only distribution (remove GHCR)
- PRD-107: Add comprehensive packaging and distribution strategy
- PRD-107: Add S3 release infrastructure and publishing scripts
- PRD-107: Implement easy upgrades and deployment system
- PRD-110: Consolidate Linear MCP documentation
- PRD-103: Implement Linear Agent Workflow with fire-and-forget webhook execution
- PRD-102: Enhance Linear webhook trigger for agent session events
- PRD-101: Create Linear analyst agent definition
- PRD-111: Align Linear MCP with backend refactoring style standards
- PRD-100: Implement Linear MCP Server (#38)
- PRD-106: Fix incomplete dependency injection and config path resolution (#37)
- PRD-98: Implement token tracking and cost calculation (#36)
- PRD-97: Playground History UI/UX Enhancements (#35)
- PRD-88: Implement backend cancellation for agent executions (#32)
- PRD-96: Improve Linear webhook trigger security and reliability
- PRD-89: Show full agent reasoning and messages in playground UI (#33)
- PRD-87: Add stop button to cancel running agent executions (#31)
- PRD-87: OpenAI Integration & Improved Messaging UX (#30)
- PRD-86: Production-ready model config & code quality fixes (#29)
- PRD-85: Fix MCP schema parsing and externalize agent config (#28)
- PRD-75: Fix license headers in new files
- PRD-75: Simplify workflow UI - remove examples, move execute to header
- PRD-75: Add Python unit tests for workflow endpoints
- PRD-75: Add unit tests for workflow save/load functionality
- PRD-75: Implement workflow save/load with backend persistence
- PRD-75: Implement enhanced execution visualization with tests
- PRD-75: Add unit tests for NodeConfigModal
- PRD-75: Implement inline parameter editing with NodeConfigModal
- PRD-75: Add unit tests for drag-and-drop functionality
- PRD-75: Implement drag-and-drop node creation
- PRD-75: Complete Shadcn/Tailwind migration for workflow UI
- feat: Transform playground console logs to conversational agent status UI
- Add token usage and iteration details to progress log
- Add real-time progress logging to Playground page
- Add -nuke option to clean-restart.sh for forced rebuild
- chore: Add missing copyright headers [skip ci]
- PRD-71: Apply black formatting and add unit tests
- PRD-71: Implement SSE streaming for real-time team execution progress
- PRD-74: Add comprehensive planning documentation for PRD-61
- PRD-73: Add UI mockup design iterations for ADCL Control Center (#24)
- PRD-70: Fix deprecated Claude model IDs across platform (#22)
- PRD-45: Cleanup Memory UI - Remove sidebar, add navigation submenu (#21)
- PRD-62: Implement workflow backend and fix critical platform bugs (#20)
- PRD-35: Implement complete trigger system for workflow and team automation
- Feature/bugfix (#18)
- chore: Add missing copyright headers [skip ci]
- PRD-42 cleanup and tech debt fun just basic cleaning of base repo and scrubbing through leftover hardcodes; move the crufty stuff out of base. 1.  Create a centralized config system - Add a configs/services.yaml file for all service configurations 2.  Update .env - Add all missing environment variables 3.  Fix the code - Update all identified files to use configuration instead of hardcodes Will have to deal with CORS at some-point; will leave out for now.
- PRD-26: Add copyright headers to all source files (#16)
- added in history to chat; extensive backend/frontend changes for initial (#15)
- Feature/cleanup (#14)
- mostly clean up in mcp; re-organized to make them truly modular (#13)
- quick spec writeup based on core arch; (#12)

# Changelog

All notable changes to the ADCL platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Upgrade system with version checking and one-command updates
- UI upgrade button in navigation showing version status
- Automatic backup before upgrades
- Rollback capability for failed upgrades
- Version tracking via VERSION file in repo root

## [0.1.0] - 2025-11-24

### Added
- Initial ADCL platform release
- Orchestrator service with MCP server management
- Frontend playground for agent workflows
- Registry server for package distribution
- Docker Compose orchestration
- WebSocket support for real-time updates
- Health check endpoints for all services

[Unreleased]: https://github.com/adcl-io/demo-sandbox/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/adcl-io/demo-sandbox/releases/tag/v0.1.0
