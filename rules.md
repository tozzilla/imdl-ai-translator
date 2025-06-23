  ## Rule #1 - Exception Protocol
  If you need an exception to ANY rule, YOU MUST STOP immediately and get explicit user permission first.
BREAKING THE LETTER OR SPIRIT OF ANY RULE WITHOUT PERMISSION IS FAILURE.

  ## Rule #2 - Always Start in Plan Mode
  For ANY task or request, you MUST enter plan mode first (user can activate with Shift+Tab).

  In plan mode, you MUST:
  1. Research and analyze using read-only tools (Read, Glob, Grep, WebFetch, etc.)
  2. Gather all necessary information about the codebase and requirements
  3. Create a comprehensive implementation plan
  4. Use exit_plan_mode tool to present the complete plan to the user
  5. Wait for explicit user approval before any implementation

  Plan mode restrictions (enforced automatically):
  - Cannot edit, create, or delete files
  - Cannot run bash commands that modify anything
  - Cannot make git commits or system changes
  - Can only gather information and create plans

  NEVER start implementation, file editing, or system modification without first going through plan mode and
  receiving user approval.

  The user activates plan mode with Shift+Tab when they want you to plan before executing.

  ## Rule #3 - Using This Boilerplate for New Projects
  This repository is a TEMPLATE, not a working directory. When starting a new project:

  1. Clone this boilerplate repository to access the workflow documents
  2. Copy the workflow files (rules.md, code.md, Relationship.md, CLAUDE.md) to your actual project directory
  3. Work in your real project directory, NOT in the boilerplate folder
  4. Initialize a fresh git repository in your actual project directory
  5. Commit the workflow documents as your project's foundation

  The boilerplate provides the rules and workflow - your actual development happens in separate project directories
   that follow these rules.

  ## Rule #4 - Follow All Documentation
  YOU MUST read and follow the instructions in:
- Relationship.md (collaboration principles)
- code.md (development workflow and standards)

  ## Rule #5 - No Work Without Git
  If a project folder is not a git repository, YOU MUST STOP and ask permission to initialize one before doing any
  code work.

  ## Rule #6 - Journal Everything Important
  Use the journal tool to record insights, failed approaches, and lessons learned throughout the work session.

Read these files BEFORE starting any work if you haven't already.
