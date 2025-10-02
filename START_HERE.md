# 🚀 START HERE — New Chat Prompt

Copy-paste this into a new chat to restore full context instantly:

---

## Context Restoration Prompt

```
I'm continuing work on the MIA4 AI assistant project. Please read these files to restore context:

1. **SPRINT.md** — Current sprint goals, active tasks, and implementation plan
2. **AGENTS.md** — Architecture overview and quick reference
3. **.instructions.md** — Core principles and working rules

After reading, confirm you understand:
- Current sprint goal
- What we're implementing (which variant/approach)
- What the next immediate task is
- Any blockers or risks

Then, let's continue from where we left off.
```

---

## Alternative: Minimal Prompt (if files attached)

```
I'm continuing MIA4 development. Files attached: SPRINT.md, AGENTS.md, .instructions.md

Quick summary:
- We're implementing adapter streaming integration (Variant A)
- Goal: Fix channel isolation so reasoning never leaks into session history
- Next task: [check SPRINT.md "Next Steps"]

Ready to continue?
```

---

## Alternative: Ultra-Short (for quick pickup)

```
Continuing MIA4. Read SPRINT.md. What's our next task?
```

---

## What to Attach to New Chat

### **Minimum (always):**
- ✅ `SPRINT.md` — Current context

### **Recommended:**
- ✅ `SPRINT.md`
- ✅ `AGENTS.md` — If agent hasn't seen architecture before
- ✅ `.instructions.md` — If discussing principles/decisions

### **Only if needed:**
- 📄 Specific ADR from `docs/ADR/` if discussing design decisions
- 📄 Changelog from `docs/changelog/` if referencing past changes
- 📄 Test files if debugging specific tests

---

## Testing This Workflow

**Scenario 1: Simple continuation**
```
Attach: SPRINT.md
Prompt: "Continuing MIA4. Read SPRINT.md. What's next?"
Expected: Agent reads sprint, identifies next task, asks for confirmation
```

**Scenario 2: New agent onboarding**
```
Attach: SPRINT.md, AGENTS.md, .instructions.md
Prompt: [Full context restoration prompt above]
Expected: Agent understands architecture, current sprint, and working style
```

**Scenario 3: Deep debugging**
```
Attach: SPRINT.md, relevant ADR, specific test file
Prompt: "We're stuck on [specific issue]. See SPRINT.md context, ADR-XXXX for design rationale, and test_file.py for current behavior."
Expected: Agent has full context for problem-solving
```

---

## Recovery Checklist for Agent

When starting a new chat, I should confirm I understand:

- [ ] **Sprint Goal** (from SPRINT.md header)
- [ ] **Current Phase** (Planning / Implementation / Testing / Blocked)
- [ ] **Root Cause** (if fixing a bug)
- [ ] **Active Task** (what I should work on NOW)
- [ ] **Success Criteria** (how to know when done)
- [ ] **Risks** (what could go wrong)
- [ ] **Next Steps** (immediate actions)

If ANY of these are unclear after reading SPRINT.md → ASK FOR CLARIFICATION before coding!

---

## Example: Good Context Restoration Response

```
✅ Context restored!

Sprint Goal: Fix Harmony channel isolation by integrating adapter streaming
Current Phase: Implementation (Variant A)
Active Task: Task 1.1 - Create adapter instance before streaming loop

Root Cause Understood:
- Route doesn't use adapter.process_chunk() during streaming
- All tokens (reasoning + final) go to fragments unfiltered
- Reasoning leaks into session history

Next Step:
Modify generate.py lines ~365-380 to create adapter before streaming loop.

Files to change:
- src/mia4/api/routes/generate.py (primary)
- tests/api/test_generate_stream.py (validation)

Risks acknowledged:
- Breaking streaming loop (mitigation: comprehensive tests)
- Performance regression (mitigation: benchmark before/after)

Ready to start Task 1.1. Should I proceed? 🚀
```

---

## Tips for Smooth Context Handoff

### **For User:**
1. **Always attach SPRINT.md** — it's your single source of truth
2. **Update SPRINT.md before switching chats** — mark what's done, what's next
3. **If mid-task** — add notes to SPRINT.md "Notes & Observations" section
4. **If blocked** — document blocker in SPRINT.md "Risks" section

### **For Agent (me):**
1. **Read SPRINT.md first** — everything else is reference
2. **Confirm understanding** — don't assume, verify with user
3. **Check "Next Steps"** — that's the priority queue
4. **Update SPRINT.md as I work** — keep it current for next handoff

---

## Common Handoff Scenarios

### Scenario A: "We just committed, starting fresh"
```
User: "Read SPRINT.md. Last commit was [hash]. What's next?"
Agent: [Reads sprint] → "I see we completed Task X. Next is Task Y. Ready?"
```

### Scenario B: "We're mid-implementation, had to stop"
```
User: "Read SPRINT.md. I added notes about where we stopped."
Agent: [Reads sprint + notes] → "I see we're halfway through Task X. Continue from line Y?"
```

### Scenario C: "We hit a blocker"
```
User: "Read SPRINT.md. Check 'Risks' section, we're blocked."
Agent: [Reads sprint + risks] → "I see blocker Z. Let's try approach A or B?"
```

### Scenario D: "Sprint completed, starting new one"
```
User: "Read SPRINT.md. Update it for new sprint: [new goal]"
Agent: [Updates sprint] → "New SPRINT.md ready. Goal: [new goal]. First task: ___"
```

---

## Anti-Patterns (What NOT to do)

❌ **Don't:** Start coding without reading SPRINT.md
✅ **Do:** Read SPRINT.md, confirm understanding, then code

❌ **Don't:** Assume context from conversation summary
✅ **Do:** Trust SPRINT.md as source of truth

❌ **Don't:** Ask user to repeat everything
✅ **Do:** Read files, ask ONLY about unclear points

❌ **Don't:** Implement without checking "Next Steps"
✅ **Do:** Follow SPRINT.md priority order

---

## Meta: Improving This Process

If this handoff process doesn't work well, update this file!

**Feedback loop:**
1. Try new chat handoff
2. Note what was unclear
3. Update START_HERE.md or SPRINT.md template
4. Commit improvements
5. Repeat

**Goal:** Zero-friction context restoration in <30 seconds.

---

**Last Updated:** 2025-10-02 (Initial version after documentation restructure)
**Next Review:** After first real handoff test
