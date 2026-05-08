# Skill: Adding JSXGraph Diagrams to Topic Pages

## When to Use
When adding mathematical diagrams to worked examples where a visual aids understanding (geometry, graphs, mechanics free-body diagrams, etc.)

## Prerequisites
- JSXGraph CDN must be in `<head>`:
```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/jsxgraph@1.8.0/distrib/jsxgraph.css">
<script src="https://cdn.jsdelivr.net/npm/jsxgraph@1.8.0/distrib/jsxgraphcore.js"></script>
```

## Implementation Pattern

### 1. Add container div
Place AFTER the question text, BEFORE the first step-reveal:
```html
<div class="diagram-container">
    <div id="unique-diagram-id" style="width:100%; max-width:520px; height:450px; margin:0 auto;"></div>
</div>
```

### 2. Lazy initialization (CRITICAL for tabbed panels)
If the diagram is inside a hidden tab/panel, it MUST be initialized after the panel becomes visible. JSXGraph cannot measure a `display:none` container.

```javascript
var diagramInit = false;
// Hook into the tab-switching function:
// Inside selectExample() or equivalent:
if (panelId === 'target-panel' && !diagramInit) {
    diagramInit = true;
    setTimeout(initDiagramFunction, 50);
}
```

### 3. Board setup
```javascript
function initDiagramFunction() {
    var board = JXG.JSXGraph.initBoard('unique-diagram-id', {
        boundingbox: [xmin, ymax, xmax, ymin],  // NOTE: [left, top, right, bottom]
        axis: true,
        grid: true,
        showCopyright: false,
        showNavigation: false,
        defaultAxes: {
            x: { ticks: { minorTicks: 0 } },
            y: { ticks: { minorTicks: 0 } }
        }
    });
    // ... create elements
}
```

### 4. Colour scheme
- Primary curves/shapes: `#2563eb` (blue)
- Secondary/construction lines: `#e11d48` (red/pink)
- Key points: `#16a34a` (green)
- Dashed construction: `strokeColor: '#666', dash: 3`
- Fill: `rgba(37,99,235,0.05)` (very light blue)

### 5. CSS (add once per page)
```css
.diagram-container { margin: 1.5rem 0; text-align: center; }
.diagram-container svg { max-width: 100%; height: auto; border: 1px solid var(--border); border-radius: 8px; background: #fff; }
```

## Common Elements

### Circle
```javascript
var centre = board.create('point', [5, 4], {
    name: '(5, 4)', size: 3, fixed: true, color: '#2563eb',
    label: { offset: [10, 5], color: '#2563eb', fontSize: 13 }
});
board.create('circle', [centre, 3], {
    strokeColor: '#2563eb', strokeWidth: 2,
    fillColor: 'rgba(37,99,235,0.05)', fixed: true
});
```

### Line from equation ax + by + c = 0
```javascript
// JSXGraph format: [c, a, b]
var line = board.create('line', [c, a, b], {
    strokeColor: '#e11d48', strokeWidth: 2, fixed: true
});
```

### Perpendicular + foot
```javascript
var perp = board.create('perpendicular', [line, point], {
    strokeColor: '#666', strokeWidth: 1.5, dash: 3,
    point: { visible: false }
});
var foot = board.create('intersection', [line, perp, 0], {
    name: 'N', size: 3, color: '#16a34a',
    label: { offset: [10, -15], color: '#16a34a', fontSize: 12 }
});
```

### Right angle marker
```javascript
board.create('angle', [pointA, vertex, pointB], {
    type: 'square', orthoType: 'square', radius: 0.4,
    strokeColor: '#666', fillColor: 'transparent'
});
```

## Pitfalls
1. **Hidden container** — NEVER init JSXGraph in a hidden panel. Always lazy-init.
2. **Bounding box** — format is `[xmin, ymax, xmax, ymin]` (upper-left to lower-right)
3. **Aspect ratio** — if `keepAspectRatio: true`, JSXGraph expands bounds to match container. Set container aspect ratio to match your data range, or omit the option.
4. **Points are draggable by default** — add `fixed: true` for static diagrams.
5. **Text labels** — use `board.create('text', [x, y, 'label'], {...})` for positioned labels.

## Pages with JSXGraph Already
- `output-as/topics/coordinate-geometry-circles.html` — reference implementation (lazy-init pattern)
- `output/topics/calculus-optimisation.html` — original PoC (always-visible, no lazy init needed)
