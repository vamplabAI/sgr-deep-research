# Tool Display Components

This directory contains specialized display components for different tool types used in the chat interface.

## Architecture

The `ChatMessageStep.vue` acts as a **router component** that delegates rendering to specialized tool components based on the tool type.

## Components

### Core Components

- **`ChatMessageStep.vue`** (134 lines) - Router component that determines which tool display to use
- **`StreamingContentDisplay.vue`** (27 lines) - Shows streaming content with loading indicator
- **`StringContentDisplay.vue`** (91 lines) - Displays string results with link formatting and collapsible extracted content

### Tool-Specific Components

- **`ReasoningToolDisplay.vue`** (94 lines) - Agent's analysis and planning steps
- **`ClarificationToolDisplay.vue`** (88 lines) - Questions, unclear terms, and assumptions
- **`WebSearchToolDisplay.vue`** (99 lines) - Search queries and results
- **`ExtractPageContentToolDisplay.vue`** (61 lines) - URLs being extracted
- **`FinalAnswerToolDisplay.vue`** (75 lines) - Final answer with completed steps
- **`GenericToolDisplay.vue`** (50 lines) - Fallback for other tool types

## Benefits

✅ **Maintainability**: Each component is 27-99 lines (vs 1094 lines monolith)
✅ **Clarity**: One component = one responsibility
✅ **Testability**: Easy to test individual tool displays
✅ **Extensibility**: Add new tools by creating new components
✅ **Performance**: Only load components that are actually used

## Adding New Tools

1. Create new component in `tools/` directory (e.g., `MyNewToolDisplay.vue`)
2. Import in `ChatMessageStep.vue`
3. Add type guard computed property (e.g., `isMyNewTool`)
4. Add conditional rendering in template

Example:

```vue
<!-- In ChatMessageStep.vue -->
<MyNewToolDisplay
  v-else-if="isMyNewTool"
  :data="getToolData(step)"
/>
```

## Migration

The old monolithic `ChatMessageStep.vue` has been backed up as `ChatMessageStep.vue.old` (1094 lines).
