import { app } from "../../scripts/app.js";

const NODE_ID = "MiniMaxH3EasyLocalPromptOptimizer";

app.registerExtension({
    name: "ComfyUI.MiniMaxH3EasyT8Enhancer",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_ID) return;

        const origNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = origNodeCreated ? origNodeCreated.apply(this, arguments) : undefined;

            let running = false;
            const runWidget = this.addWidget(
                "button",
                "▶ 运行提示词优化",
                "提交当前工作流",
                async () => {
                    if (running) return;
                    running = true;
                    try {
                        await app.queuePrompt(0, 1, [String(this.id)]);
                    } catch (err) {
                        console.error("[Easy-T8Enhancer] Run failed:", err);
                    } finally {
                        running = false;
                    }
                },
                { serialize: false }
            );
            runWidget.serializeValue = () => undefined;

            return r;
        };

        const origConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            const r = origConfigure ? origConfigure.apply(this, arguments) : undefined;

            // Ensure the button exists after loading workflow
            const hasBtn = this.widgets?.some((w) => w.type === "button" && w.name === "▶ 运行提示词优化");
            if (!hasBtn) {
                let running = false;
                const runWidget = this.addWidget(
                    "button",
                    "▶ 运行提示词优化",
                    "提交当前工作流",
                    async () => {
                        if (running) return;
                        running = true;
                        try {
                            await app.queuePrompt(0, 1, [String(this.id)]);
                        } catch (err) {
                            console.error("[Easy-T8Enhancer] Run failed:", err);
                        } finally {
                            running = false;
                        }
                    },
                    { serialize: false }
                );
                runWidget.serializeValue = () => undefined;
            }

            return r;
        };

        const origExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (message) {
            if (origExecuted) origExecuted.apply(this, arguments);

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
