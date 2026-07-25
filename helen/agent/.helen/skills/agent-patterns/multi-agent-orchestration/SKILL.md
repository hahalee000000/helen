---
name: multi-agent-orchestration
description: Pattern for orchestrating multiple agents with distinct personas in sequential rounds with shared history accumulation
tags: agent, orchestration, multi-agent, round-based, discussion, debate, history, persona
version: 1.1.0
---

# Multi-Agent Orchestration Pattern

## When to Use

Use this pattern when you need:
- Multiple agents with distinct perspectives/personas analyzing the same topic
- Sequential agent calls where each agent sees previous responses
- Round-based discussions (e.g., debates, code reviews, decision-making)
- A final synthesis agent that summarizes all viewpoints

## Core Pattern

### 1. Define Expert Agents with Distinct Personas

```helen
agent OptimistAgent(topic: str, round_num: int, history: str) {
    description "Optimist — focuses on opportunities"
    prompt """
    You are an optimist expert. Analyze the topic positively.
    Topic: {{topic}}
    Round: {{round_num}} of 3
    Previous discussion:
    {{history}}
    Respond in 3-5 sentences, start with [Optimist].
    """
    temperature 0.8  // Higher creativity for diverse viewpoints
    main { return llm act }
}

agent PessimistAgent(topic: str, round_num: int, history: str) {
    description "Pessimist — focuses on risks"
    prompt """..."""
    temperature 0.8
    main { return llm act }
}

agent PragmatistAgent(topic: str, round_num: int, history: str) {
    description "Pragmatist — focuses on feasibility"
    prompt """..."""
    temperature 0.7  // Slightly lower for balanced analysis
    main { return llm act }
}
```

### 2. History Accumulation Function

```helen
fn accumulate_log(log: str, round_num: int, expert: str, view: str): str {
    let label = get_expert_label(expert)
    let entry = "\n[Round " + str(round_num) + "-" + label + "]\n" + view + "\n"
    return log + entry
}
```

### 3. Round-Based Orchestration

```helen
fn run_discussion_session(topic: str): str {
    let discussion_log = ""
    
    // Multiple rounds
    for round_num in [1, 2, 3] {
        print(format_round_header(round_num))
        
        // Each expert responds in sequence
        let optimist_view = OptimistAgent(topic, round_num, discussion_log)
        discussion_log = accumulate_log(discussion_log, round_num, "optimist", optimist_view)
        
        let pessimist_view = PessimistAgent(topic, round_num, discussion_log)
        discussion_log = accumulate_log(discussion_log, round_num, "pessimist", pessimist_view)
        
        let pragmatist_view = PragmatistAgent(topic, round_num, discussion_log)
        discussion_log = accumulate_log(discussion_log, round_num, "pragmatist", pragmatist_view)
    }
    
    // Final synthesis
    let conclusion = SummaryAgent(topic, discussion_log)
    return conclusion
}
```

### 4. Summary Agent

```helen
agent SummaryAgent(topic: str, discussion_log: str) {
    description "Synthesizes all viewpoints into final conclusion"
    prompt """
    Three experts discussed: {{topic}}
    Full discussion:
    {{discussion_log}}
    
    Provide final conclusion:
    1. Topic overview
    2. Key opportunities (optimist view)
    3. Key risks (pessimist view)
    4. Practical recommendations (pragmatist view)
    5. Final judgment
    """
    temperature 0.5  // Lower for balanced synthesis
    main { return llm act }
}
```

## Key Design Decisions

### Temperature Settings
- **Diverse perspectives (0.7-0.8)**: Higher temperature for creative, varied viewpoints
- **Synthesis (0.5)**: Lower temperature for balanced, analytical summary

### History Passing
- Each agent receives full discussion history
- Enables agents to respond to previous viewpoints
- Creates genuine dialogue, not isolated opinions

### Sequential vs Parallel
- **Sequential**: Agents see previous responses (enables dialogue)
- **Parallel**: Agents respond independently (faster but no interaction)
- Choose based on whether you want agents to build on each other's ideas

## Common Pitfalls

### ❌ Pitfall 1: Forgetting to Pass History
```helen
// Wrong: Agent doesn't see previous discussion
let view = ExpertAgent(topic, round_num)

// Correct: Pass accumulated history
let view = ExpertAgent(topic, round_num, discussion_log)
```

### ❌ Pitfall 2: Not Accumulating Log
```helen
// Wrong: History stays empty
let view = ExpertAgent(topic, round_num, "")

// Correct: Accumulate each response
discussion_log = accumulate_log(discussion_log, round_num, expert, view)
```

### ❌ Pitfall 3: Using Same Temperature for All Agents
```helen
// Wrong: All agents think the same way
temperature 0.7  // for all agents

// Correct: Adjust based on role
// Optimist/Pessimist: 0.8 (creative, diverse)
// Pragmatist: 0.7 (balanced)
// Summary: 0.5 (analytical, synthesis)
```

## Variations

### Debate Pattern (2 Agents)
```helen
for round in [1, 2, 3] {
    let pro_view = ProAgent(topic, round, history)
    history = accumulate(history, "pro", pro_view)
    
    let con_view = ConAgent(topic, round, history)
    history = accumulate(history, "con", con_view)
}
```

### Code Review Pattern (Multiple Reviewers)
```helen
let security_review = SecurityReviewer(code, history)
let performance_review = PerformanceReviewer(code, history)
let readability_review = ReadabilityReviewer(code, history)
```

### Decision-Making Pattern (Stakeholders)
```helen
for stakeholder in ["customer", "engineer", "manager"] {
    let view = StakeholderAgent(topic, stakeholder, round, history)
    history = accumulate(history, stakeholder, view)
}
```

## Testing Strategy

Test helper functions separately from agent calls:
```helen
fn test_accumulate_log() {
    let log = accumulate_log("", 1, "optimist", "Great idea!")
    assert_contains(log, "optimist")
    assert_contains(log, "Great idea!")
}

fn test_round_header_format() {
    let header = format_round_header(1)
    assert_contains(header, "Round 1")
}
```

## Related Patterns
- Agent collaboration (shared state between agents)
- Sequential agent pipelines
- History management in multi-turn conversations
