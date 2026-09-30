import { app } from "../../scripts/app.js";

const NODE_CLASS = "MiniMaxH3EasyLocalPromptOptimizer";

app.registerExtension({
    name: "ComfyUI.MiniMaxH3EasyT8Enhancer",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_CLASS) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

            const promptWidget = this.widgets?.find((w) => w.name === "prompt");
            const optimizedTextWidget = this.widgets?.find((w) => w.name === "optimized_text");

            // Add Run Button like T8 Prompt Enhancer
            let running = false;
            const runBtn = this.addWidget(
                "button",
                "▶ 单独运行/优化提示词 (Run Prompt Optimizer)",
                "仅运行此节点生成提示词，不启动整个工作流",
                async () => {
                    if (running) return;
                    running = true;
                    runBtn.name = "⏳ 正在生成优化提示词...";
                    this.setDirtyCanvas(true, true);
                    try {
                        // Queue only this node using ComfyUI queuePrompt partial execution
                        await app.queuePrompt(0, 1, [String(this.id)]);
                    } catch (err) {
                        console.error("[Easy-T8Enhancer] Run failed:", err);
                    } finally {
                        running = false;
                        runBtn.name = "▶ 单独运行/优化提示词 (Run Prompt Optimizer)";
                        this.setDirtyCanvas(true, true);
                    }
                },
                { serialize: false }
            );
            runBtn.serializeValue = () => undefined;

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
                    this.setDirtyCanvas(true, true);
                }
            }
        };
    },
});
