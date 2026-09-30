import { app } from "../../scripts/app.js";

const NODE_ID = "MiniMaxH3EasyLocalPromptOptimizer";

console.log("[Easy-T8Enhancer] Script loaded from server!");

function addRunButton(node) {
    if (!node) return;
    const hasBtn = (node.widgets || []).some((w) => w.type === "button" && w.name === "▶ 运行提示词优化");
    if (hasBtn) return;

    console.log("[Easy-T8Enhancer] Adding run button to node:", node.id);
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

    async setup() {
        console.log("[Easy-T8Enhancer] Extension setup hook invoked!");
        const scanNodes = () => {
            for (const n of app.graph?._nodes || []) {
                if (n.type === NODE_ID || n.comfyClass === NODE_ID) {
                    addRunButton(n);
                }
            }
        };
        setTimeout(scanNodes, 300);
        setTimeout(scanNodes, 1000);
        setTimeout(scanNodes, 2000);
    },

    async nodeCreated(node) {
        if (node.type === NODE_ID || node.comfyClass === NODE_ID) {
            console.log("[Easy-T8Enhancer] nodeCreated hook invoked for node:", node.id);
            addRunButton(node);
        }
    },

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_ID) return;

        console.log("[Easy-T8Enhancer] beforeRegisterNodeDef matched:", NODE_ID);
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
            setTimeout(() => {
                addRunButton(this);
            }, 100);
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
