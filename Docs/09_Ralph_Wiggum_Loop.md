# Ralph Wiggum Loop (Persistence Pattern)

Claude Code runs in interactive mode — after processing a prompt, it waits for more input. To keep your AI Employee working autonomously until a task is complete, use the **Ralph Wiggum pattern**: a Stop hook that intercepts Claude's exit and feeds the prompt back.

## How It Works

1. Orchestrator creates state file with prompt
2. Claude works on task
3. Claude tries to exit
4. Stop hook checks: Is task file in `/Done`?
5. **YES** → Allow exit (complete)
6. **NO** → Block exit, re-inject prompt, and allow Claude to see its own previous failed output (loop continues)
7. Repeat until complete or max iterations

## Usage

```bash
# Start a Ralph loop
/ralph-loop "Process all files in /Needs_Action, move to /Done when complete" \
  --completion-promise "TASK_COMPLETE" \
  --max-iterations 10
```

## Two Completion Strategies

### 1. Promise-based (simple)
Claude outputs `<promise>TASK_COMPLETE</promise>`

### 2. File movement (advanced — Gold tier)
Stop hook detects when task file moves to `/Done`
- More reliable (completion is natural part of workflow)
- Orchestrator creates state file programmatically
- See reference implementation for details

## Reference

https://github.com/anthropics/claude-code/tree/main/.claude/plugins/ralph-wiggum
