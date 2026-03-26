# Prompting Guide

## For Effective Prompting
1. **Be Specific**: Clearly state what you want to accomplish and which phase it relates to.
2. **Provide Context**: Reference relevant files using exact relative or absolute paths.
3. **Break Down Complex Tasks**: Delegate explicitly to specialist roles as defined in `.agentrules` (e.g. `@Coder`, `@UI-Designer`).
4. **Enforce Core Principles**: When asking for features, mandate "Functional simplicity first" and "Sequential logic".

## Constraint Stuffing
To ensure robust code generation without truncation, use constraints like:
- "Ensure the code is complete and implements all necessary error handling."
- "Adhere strictly to `.agentrules` and fail fast."
- "Write the complete implementation, do not use placeholders."
