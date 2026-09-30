import { app } from "../../scripts/app.js";

const NODE_CLASS = "MiniMaxH3EasyLocalPromptOptimizer";

function createOrFindButton(node) {
    if (!node || !node.widgets) return;
    let btn = node.widgets.find((w) => w.name === "run_prompt_opt_btn");
    if (btn) return btn;

    let running = false;
    btn = node.addWidget(
        "button",
        "▶ 单独运行/优化提示词 (Run Prompt Optimizer)",
        null,
        async () => {
            if (running) return;
            running = true;
            btn.name = "⏳ 正在生成优化提示词...";
            node.setDirtyCanvas?.(true, true);
            try {
                await app.queuePrompt(0, 1, [String(node.id)]);
            } catch (err) {
                console.error("[Easy-T8Enhancer] Run failed:", err);
            } finally {
                running = false;
                btn.name = "▶ 单独运行/优化提示词 (Run Prompt Optimizer)";
                node.setDirtyCanvas?.(true, true);
            }
        },
        { serialize: false }
    );
    btn.name = "run_prompt_opt_btn";
    btn.serializeValue = () => undefined;
    return btn;
}

app.registerExtension({
    name: "ComfyUI.MiniMaxH3EasyT8Enhancer",
    async setup() {
        // Scan already rendered nodes on canvas
        const checkExisting = () => {
            for (const node of app.graph?._nodes || []) {
                if (node.type === NODE_CLASS || node.comfyClass === NODE_CLASS) {
                    createOrFindButton(node);
                    node.setDirtyCanvas?.(true, true);
                }
            }
        };
        setTimeout(checkExisting, 500);
        setTimeout(checkExisting, 1500);
    },
    async nodeCreated(node) {
        if (node.type === NODE_CLASS || node.comfyClass === NODE_CLASS) {
            createOrFindButton(node);
        }
    },
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_CLASS) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
            createOrFindButton(this);
            return r;
        };

        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            const r = onConfigure ? onConfigure.apply(this, arguments) : undefined;
            createOrFindButton(this);
            return r;
        };

        const onExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (message) {
            if (onExecuted) onExecuted.apply(this, arguments);

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
