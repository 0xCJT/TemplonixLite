# Templonix Lite Workflows

## 🎯 **What Are Workflows?**

Workflows are **meta-prompts** that transform Claude into specialized AI assistants for specific business processes. Each workflow is simply a prompt file that guides Claude's behavior and expertise.

## 📁 **Structure**

```
workflows/
├── sales_negotiator/
│   └── prompt.txt          # Sales negotiation expertise
├── project_manager/
│   └── prompt.txt          # Project management guidance  
└── business_analyst/
    └── prompt.txt          # Business analysis workflows
```

## 🔧 **How It Works**

1. **Claude calls**: `workflow.get(workflow_name="sales_negotiator")`
2. **Templonix Lite returns**: The meta-prompt text
3. **Claude ingests**: The prompt and becomes a sales negotiator
4. **Claude uses**: Other MCP tools (email, calendar, memory) within that role

## 🚀 **Using Workflows**

### **Load a Workflow**
```
workflow.get(workflow_name="sales_negotiator")
```

### **List Available Workflows**  
```
workflow.list()
```

## ✨ **Creating New Workflows**

### **Simple Structure**
1. Create folder: `workflows/my_workflow/`
2. Add file: `prompt.txt` with your meta-prompt
3. Done! Instantly available via MCP

### **Example Meta-Prompt Structure**
```markdown
# My Workflow Name

You are now operating in **My Workflow Mode**. This workflow transforms you into...

## Core Competencies
- Skill 1
- Skill 2

## Workflow Process
### Phase 1: Analysis
### Phase 2: Strategy  
### Phase 3: Execution

## Key Tools & Techniques
- Specific methods
- Best practices

## Success Metrics
- How to measure success

---
*Remember: Focus on [key principle for this workflow]*
```

## 📦 **Pip Install Pattern (Future)**

Workflows will be installable as simple packages:

```bash
pip install templonix-workflow-sales
pip install templonix-workflow-pm
```

Each package just drops a prompt file into the workflows directory.

## 🎪 **Philosophy**

**Workflows ≠ Code**  
**Workflows = Smart Prompts**

The power is in the prompt engineering, not Python complexity. Claude does the reasoning - workflows just guide the expertise domain.

---

## 📋 **Available Workflows**

### **Sales Negotiator** 
Expert sales negotiation guidance with strategic thinking and tactical precision.

*Add more workflows by creating new folders with prompt.txt files!*





