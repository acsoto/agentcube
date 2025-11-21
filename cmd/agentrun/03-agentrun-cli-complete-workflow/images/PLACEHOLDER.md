# Architecture Diagrams

This directory should contain architecture diagrams for the tutorial.

## Required Diagrams

1. **architecture.png** - Overall architecture diagram showing the complete AgentRun CLI workflow
   - Should include: Agent development → Pack → Build → Publish → Invoke flow
   - Show integration with AgentCube platform
   - Illustrate local vs cloud build options

## Creating Diagrams

You can create these diagrams using tools like:
- Draw.io / diagrams.net
- Lucidchart
- Microsoft Visio
- PlantUML
- Mermaid

## Example Architecture Flow

```
┌─────────────────┐
│  Agent Code     │
│  (Python)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ agentrun pack   │  ← Validate & Generate Metadata
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ agentrun build  │  ← Build Container Image
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│agentrun publish │  ← Push to Registry & Register
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   AgentCube     │  ← Deployed Agent
│   Platform      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│agentrun invoke  │  ← Test & Use Agent
└─────────────────┘
```
