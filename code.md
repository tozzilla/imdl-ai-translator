## Writing code / version control / testing / debugging

1. ⁠first, think through the problem, read the codebase for relevant file, and write a plan to tasks/todo.md
2. ⁠the plan should have a listi of todo items that you can check off as you complete them.
3. ⁠before you begin working, check with me and I will verify the plan.
4. ⁠then, begin working on the todo items, marking them as complete as you go.
5. YOU MUST make the SMALLEST reasonable changes to achieve the desired outcome.
6. We STRONGLY prefer simple, clean, maintainable solutions over clever or complex ones. Readability and maintainability are PRIMARY CONCERNS, even at the cost of conciseness or performance.
7. YOU MUST NEVER make code changes unrelated to your current task. If you notice something that should be fixed but is unrelated, document it in your journal rather than fixing it immediately.
8. YOU MUST get explicit approval before implementing ANY backward compatibility.
9. YOU MUST MATCH the style and formatting of surrounding code, even if it differs from standard style guides. Consistency within a file trumps external standards.
10. ⁠finally, add a review section to the todo.md file with a summary of the changes you made and any other relevant information.
11. important: periodically make sure to commit when it makes sense
12. If the project isn't in a git repo, YOU MUST STOP and ask permission to initialize one.
13. Tests MUST comprehensively cover ALL functionality.
14. FOR EVERY NEW FEATURE OR BUGFIX, YOU MUST follow TDD:
	1. Write a failing test that correctly validates the desired functionality
	2. Run the test to confirm it fails as expected
	3. Write ONLY enough code to make the failing test pass
	4. Run the test to confirm success
	5. Refactor if needed while keeping tests green
15. YOU MUST ALWAYS find the root cause of any issue you are debugging YOU MUST NEVER fix a symptom or add a workaround instead of finding a root cause, even if it is faster or I seem like I'm in a hurry.
16. YOU MUST follow this debugging framework for ANY technical issue
	1.  Root Cause Investigation (BEFORE attempting fixes)
		1. Read Error Messages Carefully: Don't skip past errors or warnings - they often contain the exact solution
		2. Reproduce Consistently: Ensure you can reliably reproduce the issue before investigating
		3. Check Recent Changes: What changed that could have caused this? Git diff, recent commits, etc.
	2. Pattern Analysis
		1. Find Working Examples: Locate similar working code in the same codebase
		2. Compare Against References: If implementing a pattern, read the reference implementation completely
		3. Identify Differences: What's different between working and broken code?
		4. Understand Dependencies: What other components/settings does this pattern require?
	3. Hypothesis and Testing
		1. Form Single Hypothesis: What do you think is the root cause? State it clearly
		2. Test Minimally: Make the smallest possible change to test your hypothesis
		3. Verify Before Continuing: Did your test work? If not, form new hypothesis - don't add more fixes
		4. When You Don't Know: Say "I don't understand X" rather than pretending to know
	4. Implementation Rules
		1. ALWAYS have the simplest possible failing test case. If there's no test framework, it's ok to write a one-off test script.
		2. NEVER add multiple fixes at once
		3. NEVER claim to implement a pattern without reading it completely first
		4. ALWAYS test after each change
		5. IF your first fix doesn't work, STOP and re-analyze rather than adding more fixes
17. YOU MUST use the journal tool frequently to capture technical insights, failed approaches, and user preferences
18. Before starting complex tasks, search the journal for relevant past experiences and lessons learned
19. When you are using /compact, please focus on our conversation, your most recent (and most significant) learnings, and what you need to do next. If we've tackled multiple tasks, aggressively summarize the older ones, leaving more context for the more recent ones.
