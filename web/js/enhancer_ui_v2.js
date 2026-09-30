import { app } from "/scripts/app.js";

const NODE_ID = "MiniMaxH3EasyLocalPromptOptimizer";
const BUTTON_NAME = "▶ 运行提示词优化";

function addRunButton(node) {
    if (!node?.widgets) return;
    if (node.widgets.some((widget) => widget.type === "button" && widget.name === BUTTON_NAME)) return;

    let queuing = false;
    const runWidget = node.addWidget(
        "button",
        BUTTON_NAME,
        "仅优化当前节点的提示词，不运行后续视频生成",
        async () => {
            if (queuing) return;
            queuing = true;

            const optimizedTextWidget = node.widgets.find((widget) => widget.name === "optimized_text");
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
    node.widgets.splice(node.widgets.indexOf(runWidget), 1);
    node.widgets.splice(2, 0, runWidget);
    node.size[1] = Math.max(node.size[1], 760);
    node.setDirtyCanvas?.(true, true);
}

app.registerExtension({
    name: "ComfyUI.MiniMaxH3EasyT8Enhancer",

    async setup() {
        const scan = () => {
            for (const node of app.graph?._nodes || []) {
                if (node.type === NODE_ID || node.comfyClass === NODE_ID) addRunButton(node);
            }
        };
        setTimeout(scan, 300);
        setTimeout(scan, 1000);
        setTimeout(scan, 2500);
    },

    async nodeCreated(node) {
        if (node.type === NODE_ID || node.comfyClass === NODE_ID) addRunButton(node);
    },

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_ID) return;

        const originalNodeCreated = nodeType.prototype.onNodeCreated;
        const originalConfigure = nodeType.prototype.onConfigure;
        const originalExecuted = nodeType.prototype.onExecuted;

        nodeType.prototype.onNodeCreated = function () {
            originalNodeCreated?.apply(this, arguments);
            addRunButton(this);
        };

        nodeType.prototype.onConfigure = function () {
            originalConfigure?.apply(this, arguments);
            requestAnimationFrame(() => addRunButton(this));
            setTimeout(() => addRunButton(this), 100);
        };

        nodeType.prototype.onExecuted = function (message) {
            originalExecuted?.apply(this, arguments);

            const optimizedPrompt = message?.optimized_prompt?.[0];
            const optimizedTextWidget = this.widgets?.find((widget) => widget.name === "optimized_text");
            if (optimizedPrompt && optimizedTextWidget) {
                optimizedTextWidget.value = optimizedPrompt;
                this.setDirtyCanvas?.(true, true);
            }
        };
    },
});
