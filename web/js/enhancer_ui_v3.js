import { app } from "/scripts/app.js";

const NODE_ID = "MiniMaxH3EasyLocalPromptOptimizer";
const BUTTON_NAME = "▶ 运行提示词优化";

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

function addRunButton(node) {
    if (!isOptimizer(node) || !node.widgets) return;
    if (node.widgets.some((w) => w.type === "button" && w.name === BUTTON_NAME)) return;

    let queuing = false;
    const runWidget = node.addWidget(
        "button",
        BUTTON_NAME,
        "仅优化当前节点的提示词，不运行后续视频生成",
        async () => {
            if (queuing) return;
            queuing = true;

            const optimizedTextWidget = node.widgets.find((w) => w.name === "optimized_text");
            const previousText = optimizedTextWidget?.value;
            if (optimizedTextWidget) optimizedTextWidget.value = "";
            node.setDirtyCanvas?.(true, true);

            try {
                await app.queuePrompt(0, 1, [String(node.id)]);
            } catch (error) {
                if (optimizedTextWidget) optimizedTextWidget.value = previousText;
                console.error("[Easy-T8Enhancer] Prompt optimization failed:", error);
            } finally {
                queuing = false;
                node.setDirtyCanvas?.(true, true);
            }
        },
        { serialize: false },
    );
    runWidget.serializeValue = () => undefined;
    fitNode(node);
    node.setDirtyCanvas?.(true, true);
}

function scan() {
    for (const node of app.graph?._nodes || []) addRunButton(node);
}

app.registerExtension({
    name: "ComfyUI.MiniMaxH3EasyT8Enhancer",

    async setup() {
        // Deferred only: standard widgets are built by the framework after node
        // creation, so append the button later to avoid shifting widget order.
        setTimeout(scan, 300);
        setTimeout(scan, 1000);
        setTimeout(scan, 2500);
    },

    async nodeCreated(node) {
        if (!isOptimizer(node)) return;
        // Do NOT add synchronously; wait for framework-generated widgets.
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
            }
        };
    },
});
