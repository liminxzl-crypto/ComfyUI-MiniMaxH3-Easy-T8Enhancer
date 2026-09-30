import { app } from "../../scripts/app.js";

const NODE_ID = "MiniMaxH3EasyLocalPromptOptimizer";

function addRunButton(node) {
    if (!node) return;
    const hasBtn = (node.widgets || []).some((w) => w.type === "button" && w.name === "▶ 运行提示词优化");
    if (hasBtn) return;

    let queuing = false;
    const runWidget = node.addWidget(
        "button",
        "▶ 运行提示词优化",
        "提交当前工作流",
        async () => {
            if (queuing) return;
            queuing = true;
            try {
                await app.queuePrompt(0, 1, [String(node.id)]);
            } catch (err) {
                console.error("[Easy-T8Enhancer] Queue prompt failed:", err);
            } finally {
                queuing = false;
            }
        },
        { serialize: false }
    );
    runWidget.serializeValue = () => undefined;
    node.setDirtyCanvas?.(true, true);
}

app.registerExtension({
    name: "ComfyUI.MiniMaxH3EasyT8Enhancer",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_ID) return;

        const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
        const originalOnConfigure = nodeType.prototype.onConfigure;
        const originalOnExecuted = nodeType.prototype.onExecuted;

        nodeType.prototype.onNodeCreated = function () {
            originalOnNodeCreated?.apply(this, arguments);
            addRunButton(this);
        };

        nodeType.prototype.onConfigure = function () {
            originalOnConfigure?.apply(this, arguments);
            requestAnimationFrame(() => {
                addRunButton(this);
            });
        };

        nodeType.prototype.onExecuted = function (message) {
            originalOnExecuted?.apply(this, arguments);

            if (message?.optimized_prompt && Array.isArray(message.optimized_prompt)) {
                const text = message.optimized_prompt[0];
                const optimizedTextWidget = this.widgets?.find((w) => w.name === "optimized_text");
                if (optimizedTextWidget && text) {
                    optimizedTextWidget.value = text;
                    this.setDirtyCanvas?.(true, true);
                }
            }
        };
    },
});
