import { app } from "/scripts/app.js";

const NODE_ID = "MiniMaxH3EasyLocalPromptOptimizer";
const BUTTON_NAME = "▶ 运行提示词优化";
const BUTTON_TOOLTIP = "只提交本节点；不会运行下游视频生成";
const BUSY_LABEL = "⏳ 正在优化提示词（只跑本节点）…";
const MENU_LABEL = "▶ 只运行提示词优化（不跑下游视频）";

function fitNode(node) {
    const size = node.computeSize?.();
    if (size) {
        node.size[0] = Math.max(node.size[0], size[0]);
        node.size[1] = Math.max(node.size[1], size[1]);
    }
}

function isOptimizer(node) {
    return node && (node.type === NODE_ID || node.comfyClass === NODE_ID);
}

function syncDownstreamEasyNode(optimizerNode, optimizedPrompt) {
    if (!app.graph?._nodes || !optimizerNode.outputs) return;

    // Find link ID for output 0 (optimized_prompt)
    const outSlot = optimizerNode.outputs[0];
    if (!outSlot || !outSlot.links || outSlot.links.length === 0) return;

    for (const linkId of outSlot.links) {
        const link = app.graph.links?.[linkId];
        if (!link) continue;
        const targetNode = app.graph.getNodeById(link.target_id);
        if (!targetNode) continue;

        // If downstream is MiniMaxH3Easy
        if (targetNode.type === "MiniMaxH3Easy" || targetNode.comfyClass === "MiniMaxH3Easy") {
            const promptWidget = targetNode.widgets?.find((w) => w.name === "prompt");
            if (promptWidget) {
                promptWidget.value = optimizedPrompt;
                if (promptWidget._state) promptWidget._state.value = optimizedPrompt;
            }

            // Sync with Easy's custom rich editor if present
            if (targetNode.__h3Editor) {
                targetNode.__h3Editor.innerText = optimizedPrompt;
            }
            if (targetNode.properties) {
                targetNode.properties.minimax_h3_prompt_reference_doc = {
                    version: 1,
                    text: optimizedPrompt,
                    parts: [{ type: "text", text: optimizedPrompt }]
                };
            }

            targetNode.setDirtyCanvas?.(true, true);
        }
    }
}

/**
 * Submit the graph with an explicit `partial_execution_targets` list.
 *
 * The ComfyUI server only executes the OUTPUT nodes named in that list, so
 * passing this node's id makes it the sole output of the run: the media loader
 * and the optimizer execute, everything downstream is pruned.
 *
 * We post the prompt ourselves instead of going through `app.queuePrompt(...)`
 * because the third argument of that helper has changed shape across frontend
 * versions (`queueNodeIds` array -> options object), and when it is not
 * understood the call silently degrades to a full-workflow run.
 */
async function submitOptimizerOnly(node) {
    const built = await app.graphToPrompt();
    const graph = built?.output ?? built?.prompt ?? built;
    if (!graph || typeof graph !== "object" || Object.keys(graph).length === 0) {
        throw new Error("拿不到可提交的图（graphToPrompt 返回空）");
    }

    const clientId = app.api?.clientId ?? app.clientId ?? "";
    const payload = {
        client_id: clientId,
        prompt: graph,
        partial_execution_targets: [String(node.id)],
    };
    if (built?.workflow) {
        payload.extra_data = { extra_pnginfo: { workflow: built.workflow } };
    }

    const response = await fetch("/prompt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    const text = await response.text();
    if (!response.ok) {
        let detail = text;
        try {
            const parsed = JSON.parse(text);
            detail = parsed?.error?.message || parsed?.error?.details || text;
        } catch (_) { /* keep raw text */ }
        throw new Error(detail);
    }
    try {
        return JSON.parse(text);
    } catch (_) {
        return {};
    }
}

async function runOptimizerOnly(node, runWidget) {
    const optimizedTextWidget = node.widgets?.find((w) => w.name === "optimized_text");
    const previousText = optimizedTextWidget?.value;
    // The node reuses `optimized_text` verbatim when it is non-empty, so clear
    // it first to force a real model call.
    if (optimizedTextWidget) optimizedTextWidget.value = "";

    const previousLabel = runWidget?.label;
    if (runWidget) runWidget.label = BUSY_LABEL;
    node.setDirtyCanvas?.(true, true);

    try {
        const info = await submitOptimizerOnly(node);
        console.log(
            "[Easy-T8Enhancer] submitted partial execution",
            { nodeId: String(node.id), partial_execution_targets: [String(node.id)], prompt_id: info?.prompt_id },
        );
    } catch (error) {
        if (optimizedTextWidget && !optimizedTextWidget.value) {
            optimizedTextWidget.value = previousText;
        }
        console.error("[Easy-T8Enhancer] prompt optimization failed:", error);
        alert("只运行提示词优化失败：\n" + (error?.message ?? error));
    } finally {
        if (runWidget) runWidget.label = previousLabel ?? BUTTON_NAME;
        node.setDirtyCanvas?.(true, true);
    }
}

function addRunButton(node) {
    if (!isOptimizer(node) || !node.widgets) return;
    const existing = node.widgets.find((w) => w.type === "button" && w.name === BUTTON_NAME);
    if (existing) {
        // Workflows saved by older builds serialized the tooltip as the button's
        // value, which then overrides the label on load. Pin it back.
        existing.value = BUTTON_NAME;
        existing.label = BUTTON_NAME;
        return;
    }

    let queuing = false;
    const runWidget = node.addWidget(
        "button",
        BUTTON_NAME,
        BUTTON_NAME,
        async () => {
            if (queuing) return;
            queuing = true;
            try {
                await runOptimizerOnly(node, runWidget);
            } finally {
                queuing = false;
            }
        },
        { serialize: false },
    );
    runWidget.label = BUTTON_NAME;
    runWidget.tooltip = BUTTON_TOOLTIP;
    runWidget.serializeValue = () => undefined;
    fitNode(node);
    node.setDirtyCanvas?.(true, true);
}

/** Second entry point: right-click the node -> menu item. */
function patchContextMenu() {
    if (patchContextMenu.done) return;
    const proto = globalThis.LiteGraph?.LGraphNode?.prototype;
    if (!proto) return;
    patchContextMenu.done = true;

    const original = proto.getExtraMenuOptions;
    proto.getExtraMenuOptions = function (canvas, options) {
        original?.apply(this, arguments);
        if (!isOptimizer(this)) return;
        options.push({
            content: MENU_LABEL,
            callback: async () => {
                const runWidget = this.widgets?.find((w) => w.name === BUTTON_NAME);
                await runOptimizerOnly(this, runWidget);
            },
        });
    };
}

function scan() {
    patchContextMenu();
    for (const node of app.graph?._nodes || []) addRunButton(node);
}

app.registerExtension({
    name: "ComfyUI.MiniMaxH3EasyT8Enhancer",

    async setup() {
        setTimeout(scan, 300);
        setTimeout(scan, 1000);
        setTimeout(scan, 2500);
    },

    async nodeCreated(node) {
        if (!isOptimizer(node)) return;
        setTimeout(() => addRunButton(node), 300);
        setTimeout(() => addRunButton(node), 1000);
    },

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_ID) return;

        const originalConfigure = nodeType.prototype.onConfigure;
        const originalExecuted = nodeType.prototype.onExecuted;

        nodeType.prototype.onConfigure = function () {
            originalConfigure?.apply(this, arguments);
            setTimeout(() => addRunButton(this), 300);
            setTimeout(() => addRunButton(this), 1000);
        };

        nodeType.prototype.onExecuted = function (message) {
            originalExecuted?.apply(this, arguments);

            const optimizedPrompt = message?.optimized_prompt?.[0];
            const optimizedTextWidget = this.widgets?.find((w) => w.name === "optimized_text");
            if (optimizedPrompt && optimizedTextWidget) {
                optimizedTextWidget.value = optimizedPrompt;
                fitNode(this);
                this.setDirtyCanvas?.(true, true);

                // Auto-sync into downstream Easy node's prompt widget/editor
                syncDownstreamEasyNode(this, optimizedPrompt);
                app.graph?.setDirtyCanvas?.(true, true);
            }
        };
    },
});
