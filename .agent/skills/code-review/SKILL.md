---
name: Code Review
description: comprehensive guide for performing high-quality code reviews, focusing on correctness, security, performance, and maintainability.
---

# Code Review Skill

This skill defines the standard for performing code reviews. Follow these guidelines to ensure code quality, security, and maintainability.

## Objective
To catch bugs, ensure architectural consistency, improve performance, verify security, and maintain code readability *before* code is merged or considered "complete".

## Core Guidelines
1.  **Be Constructive**: Frame feedback as "we" (e.g., "We should handle this error") rather than "you".
2.  **Explain Why**: Don't just say "change this"; explain the risk or better alternative (e.g., "This O(n^2) loop might cause latency with large datasets").
3.  **Prioritize**: Distinguish between critical issues (bugs, security) and nits (formatting, variable names). Use labels like `[BLOCKER]`, `[IMPORTANT]`, and `[NIT]`.
4.  **Verify Context**: Ensure you understand *what* the code is supposed to do. If the requirements are unclear, ask before reviewing.

## Review Checklist

### 1. Correctness & Logic
- [ ] **Boundary Conditions**: Are edge cases (empty lists, null values, 0, negative numbers) handled?
- [ ] **Concurrency**: Are there race conditions? Is shared state protected? (Locks, atomic operations).
- [ ] **Error Handling**: Are errors caught and handled gracefully? Are error messages informative? avoiding bare `except:` or `catch (Exception e) {}`.
- [ ] **Logic Flaws**: Does the code actually implement the desired requirement?

### 2. Security (Critical)
- [ ] **Input Validation**: Is all external input validated and sanitized?
- [ ] **Injection**: potential SQL injection, Command injection, or XSS?
- [ ] **Secrets**: Are API keys, passwords, or tokens hardcoded? (They should be in env vars).
- [ ] **Auth**: Is authorization checked properly for sensitive actions?

### 3. Performance
- [ ] **Complexity**: Are there accidental O(n^2) or O(n^3) loops?
- [ ] **Database**: Are there N+1 queries? Are indexes being used?
- [ ] **Resources**: Are file handles, connections, and streams closed properly (e.g., `defer`, `with`, `try-finally`)?
- [ ] **Memory**: Are there potential memory leaks or large unnecessary allocations?

### 4. Style & Readability
- [ ] **Naming**: do variable/function names reveal intent? (e.g., `is_valid` vs `v`).
- [ ] **Comments**: Do comments explain *why*, not just *what*?
- [ ] **Structure**: Are functions too long? strict "One Responsibility Rule".
- [ ] **Hardcoding**: Are magic numbers or string literals used instead of constants?

### 5. Testing
- [ ] **Coverage**: Do unit tests cover the new logic?
- [ ] **Edge Cases**: Do tests check failure modes, not just the happy path?

## Output Format

When providing a code review, structure your response as follows:

### Summary
A brief high-level overview of the health of the code (e.g., "Looks good, just a few minor nits" or "Major logic issues found, needs rework").

### Critical Issues (Blockers)
*   `[BLOCKER]` File:Line - Description of the bug or security hole.

### Improvements & Suggestions
*   `[IMPORTANT]` File:Line - Performance improvements or handling edge cases.
*   `[NIT]` File:Line - Style, naming, or documentation improvements.

### Code Snippets
If suggesting a complex fix, provide a code block showing the corrected approach.
