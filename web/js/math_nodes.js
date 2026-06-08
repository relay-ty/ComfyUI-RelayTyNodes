/**
 * =============================================================================
 * ComfyUI-RelayTyNodes - 数学表达式节点前端扩展
 * =============================================================================
 *
 * 模块说明:
 *   为 RT_MathExpression 节点提供前端动态端口管理功能。
 *
 * 前后端配合节点:
 *   - RT_MathExpression (nodes/math_nodes.py): 后端提供数学表达式计算逻辑，
 *     定义 inputcount 参数和 a, b 初始端口，前端通过 "Update inputs" 按钮动态调整端口数量。
 *
 * 扩展功能:
 *   - 动态输入端口管理：根据 inputcount widget 的值动态调整 a, b, c... 输入端口数量
 *   - 节点创建时自动初始化默认数量的输入端口
 *   - 支持 * 类型输入端口（可接收任意类型数据）
 *   - 端口名对应字母表：a, b, c, ..., z（最多26个）
 *
 * =============================================================================
 */

const { app } = window.comfyAPI.app;

// 表达式验证正则：只允许字母变量、数字、运算符、括号和内置函数
const VALID_EXPRESSION_REGEX = /^[a-zA-Z0-9+\-*/%^&|~<>!=()\s,.]*$/;
const BUILTIN_FUNCTIONS = ['abs', 'sqrt', 'log', 'log10', 'sin', 'cos', 'tan', 
                           'floor', 'ceil', 'round', 'pow', 'max', 'min', 'random', 'randint'];

function validateExpression(expression) {
    if (!expression || expression.trim() === '') {
        return { valid: false, message: '表达式不能为空' };
    }
    
    // 基础字符验证
    if (!VALID_EXPRESSION_REGEX.test(expression.toLowerCase())) {
        return { valid: false, message: '表达式包含非法字符' };
    }
    
    // 检查未闭合的括号
    let parenCount = 0;
    for (const char of expression) {
        if (char === '(') parenCount++;
        if (char === ')') parenCount--;
        if (parenCount < 0) {
            return { valid: false, message: '括号不匹配' };
        }
    }
    if (parenCount !== 0) {
        return { valid: false, message: '括号未闭合' };
    }
    
    // 检查函数调用格式（简化检查）
    for (const func of BUILTIN_FUNCTIONS) {
        const regex = new RegExp(`${func}\\s*\\(`, 'gi');
        const matches = expression.match(regex);
        if (matches && matches.length > 0) {
            // 简单检查函数是否有闭合括号
            const funcRegex = new RegExp(`${func}\\s*\\([^)]*\\)`, 'gi');
            const validCalls = expression.match(funcRegex);
            if (!validCalls || validCalls.length < matches.length) {
                return { valid: false, message: `函数 ${func} 调用格式不正确` };
            }
        }
    }
    
    return { valid: true, message: '表达式有效' };
}

app.registerExtension({
	name: "RelayTyNodes.MathNodes",
	async beforeRegisterNodeDef(nodeType, nodeData, app) {
		if(!nodeData?.category?.startsWith("RelayTyNodes")) {
			return;
		}
		
		switch (nodeData.name) {
			case "RT_MathExpression":
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
						const expression_widget = self.widgets.find(w => w.name === "expression");
						
						// 验证表达式
						if (expression_widget) {
							const validation = validateExpression(expression_widget.value);
							if (!validation.valid) {
								alert(`表达式错误: ${validation.message}`);
								return;
							}
						}
						
						// 统计当前的字母输入端口数量（排除 button 类型的 widget）
						const num_inputs = self.inputs.filter(input => input.name && /^[a-z]$/.test(input.name)).length;
						if(target_number_of_inputs === num_inputs) return;

						if(target_number_of_inputs < num_inputs){
							const inputs_to_remove = num_inputs - target_number_of_inputs;
							for(let i = 0; i < inputs_to_remove; i++) {
								self.removeInput(self.inputs.length - 1);
							}
						}
						else{
							for(let i = num_inputs; i < target_number_of_inputs; ++i) {
								// 使用 addInput 添加支持连线的输入端口，使用字母作为端口名
								const portName = String.fromCharCode(97 + i); // 97 = 'a'
								self.addInput(portName, "*", {shape: 7});
							}
						}
						// 更新节点尺寸以显示新端口
						self.setSize(self.computeSize());
					});
				}, 0);
					
				// 节点创建时根据 inputcount 默认值添加输入端口
				const inputcount_widget = this.widgets.find(w => w.name === "inputcount");
				if (inputcount_widget) {
					const default_count = inputcount_widget.value;
					const current_count = self.inputs.filter(input => input.name && /^[a-z]$/.test(input.name)).length;
					for (let i = current_count; i < default_count; i++) {
						const portName = String.fromCharCode(97 + i); // 97 = 'a'
						this.addInput(portName, "*", {shape: 7});
					}
				}
				}
				break;
		}
	}
});