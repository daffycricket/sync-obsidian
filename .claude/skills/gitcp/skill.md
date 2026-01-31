---
name: gitcp
description: Describes the rules to follow for git commit and git push actions. Use when user asks to commit or/and push modifications.
allowed-tools: git
---

# When committing:
Follow Conventional Commits conventions  
https://www.conventionalcommits.org/en/v1.0.0/

<type>[optional scope]: <description>
[optional body]
[optional footer(s)]

- 0. Add all modified files (`git add .`) or only those relevant for the commit (`git add file1.txt file2.js file3.html`)
- 1. Set commit type, one of: `fix`, `feat`, `docs`, `refactor`, `perf`, `test`, `chore`, `ci`
- 2. Scope must be one of the predefined values for this repository. Do not invent new scopes without user confirmation.
- 3. Write a one-line description.  
     If a ticket identifier is explicitly present in the user request or in the context, it must be included.  
     Otherwise, do not invent one.
- 4. Use the commit body to list unit tasks or detailed changes, one per line when possible.
- 5. If the changes introduce a breaking change, describe it in the footer using `BREAKING CHANGE:`.
- 6. Create the commit using multiple `-m` options to provide both description, body and footer.

# When pushing to remote:
- 0. Try to push to the same remote branch (`git push`)
- 1. If push fails, analyze the problem:
    - a. If push is rejected because the remote branch is ahead of the local one:  
         perform a rebase, resolve potential conflicts, then attempt to push again.  
         If conflict resolution is uncertain, stop and ask the user.
    - b. If push fails for reasons other than divergence (permissions, protected branch, missing upstream):  
         stop and explain the error to the user.

# Commit examples

## Feature with breaking change (ticket f23)
feat(plugin+api): f23 - updated date of birth format to timestamp

BREAKING CHANGE: `dateOfBirth` API field now uses a timestamp format

## Backend feature
feat(api): f12 - improved GET /emails performance

## Refactoring on Obsidian plugin (ticket t42)
refactor(plugin): t42 - split main.py into smaller modules

- split main.py into main.py, auth.py and sync.py
- added unit tests
- updated documentation

## Docs update on both plugin and backend, no ticket
docs(plugin+api): improved README

- fixed spelling in CHANGELOG
