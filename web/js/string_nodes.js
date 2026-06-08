/**
 * =============================================================================
 * ComfyUI-RelayTyNodes - 字符串节点前端扩展
 * =============================================================================
 *
 * 模块说明:
 *   为 RT_JoinStringMulti 节点提供前端动态端口管理功能。
 *
 * 前后端配合节点:
 *   - RT_JoinStringMulti (nodes/string_nodes.py): 后端提供字符串连接逻辑；
 *     本前端扩展提供"Update inputs"按钮，根据 inputcount 参数动态添加/移除输入端口。
 *
 * 扩展功能:
 *   - 动态输入端口管理：根据 inputcount widget 的值动态调整 string_* 输入端口数量
 *   - 节点创建时自动初始化默认数量的输入端口
 *
 * =============================================================================
 */

const { app } = window.comfyAPI.app;

app.registerExtension({
	name: "RelayTyNodes.StringNodes",
	async beforeRegisterNodeDef(nodeType, nodeData, app) {
		if(!nodeData?.category?.startsWith("RelayTyNodes")) {
			return;
		}
		
		switch (nodeData.name) {
			case "RT_JoinStringMulti":
				// 保存原始的 onNodeCreated
				const originalOnNodeCreated = nodeType.prototype.onNodeCreated || function() {};
				
				nodeType.prototype.onNodeCreated = function () {
					// 调用原始方法
					originalOnNodeCreated.apply(this, arguments);
					
					// 在最后添加按钮（这样按钮会在所有 inputs 和 widgets 之后）
					const self = this;
					setTimeout(() => {
						self.addWidget("button", "Update inputs", null, () => {
							if (!self.inputs) {
								self.inputs = [];
							}
							const target_number_of_inputs = self.widgets.find(w => w.name === "inputcount")["value"];
							// 统计当前的 string_* 输入端口数量
							const num_inputs = self.inputs.filter(input => input.name && input.name.startsWith("string_")).length;
							if(target_number_of_inputs === num_inputs) return;

							if(target_number_of_inputs < num_inputs){
								const inputs_to_remove = num_inputs - target_number_of_inputs;
								for(let i = 0; i < inputs_to_remove; i++) {
									self.removeInput(self.inputs.length - 1);
								}
							}
							else{
								for(let i = num_inputs + 1; i <= target_number_of_inputs; ++i) {
									// 使用 addInput 添加支持连线的输入端口
									self.addInput(`string_${i}`, "STRING", {shape: 7});
								}
							}
						});
					}, 0);
					
					// 节点创建时根据 inputcount 默认值添加输入端口
					const inputcount_widget = this.widgets.find(w => w.name === "inputcount");
					if (inputcount_widget) {
						const default_count = inputcount_widget.value;
						const current_count = this.inputs.filter(input => input.name && input.name.startsWith("string_")).length;
						for (let i = current_count + 1; i <= default_count; i++) {
							this.addInput(`string_${i}`, "STRING", {shape: 7});
						}
					}
				}
				break;
		}
	}
});