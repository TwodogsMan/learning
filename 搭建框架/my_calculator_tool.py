import ast
import operator
import math
from hello_agents import ToolRegistry


def my_calculate(expression: str) -> str:
    """增强型数学计算函数，支持复杂运算"""
    if not expression.strip():
        return "计算表达式不能为空"

    # 支持的二元运算符
    operators = {
        ast.Add:      operator.add,       # +
        ast.Sub:      operator.sub,       # -
        ast.Mult:     operator.mul,       # *
        ast.Div:      operator.truediv,   # /
        ast.FloorDiv: operator.floordiv,  # //
        ast.Mod:      operator.mod,       # %
        ast.Pow:      operator.pow,       # **
        ast.LShift:   operator.lshift,    # <<
        ast.RShift:   operator.rshift,    # >>
        ast.BitOr:    operator.or_,       # |
        ast.BitXor:   operator.xor,       # ^
        ast.BitAnd:   operator.and_,      # &
    }

    # 支持的一元运算符
    unary_operators = {
        ast.UAdd: operator.pos,   # +x
        ast.USub: operator.neg,   # -x
        ast.Invert: operator.inv, # ~x
    }

    # 支持的数学函数（一元）
    functions = {
        # 基础函数
        'sqrt':     math.sqrt,
        'abs':      abs,
        'exp':      math.exp,
        # 对数函数
        'log':      math.log,       # ln(x)
        'log10':    math.log10,
        'log2':     math.log2,
        # 三角函数
        'sin':      math.sin,
        'cos':      math.cos,
        'tan':      math.tan,
        'asin':     math.asin,
        'acos':     math.acos,
        'atan':     math.atan,
        # 双曲函数
        'sinh':     math.sinh,
        'cosh':     math.cosh,
        'tanh':     math.tanh,
        # 角度转换
        'radians':  math.radians,
        'degrees':  math.degrees,
        # 取整函数
        'ceil':     math.ceil,
        'floor':    math.floor,
        'trunc':    math.trunc,
        # 阶乘
        'factorial': math.factorial,
    }

    # 支持的二元函数（如 pow、gcd 等）
    binary_functions = {
        'pow':  pow,
        'gcd':  math.gcd,
        'lcm':  math.lcm,
        'atan2': math.atan2,
        'hypot': math.hypot,
        'log':   math.log,       # log(x, base)
        'comb':  math.comb,
        'perm':  math.perm,
        'copysign': math.copysign,
    }

    # 支持的数学常量
    constants = {
        'pi':  math.pi,
        'e':   math.e,
        'tau': math.tau,
        'inf': math.inf,
        'nan': math.nan,
    }

    try:
        node = ast.parse(expression, mode='eval')
        result = _eval_node(node.body, operators, unary_operators,
                            functions, binary_functions, constants)
        return _format_result(result)
    except ZeroDivisionError:
        return "数学错误：不能除以零"
    except ValueError as e:
        return f"数值错误：{e}"
    except OverflowError:
        return "数值错误：计算结果溢出"
    except Exception as e:
        return f"计算失败：{e}"


def _eval_node(node, operators, unary_operators,
               functions, binary_functions, constants):
    """递归求值 AST 节点"""

    # 字面常量：整数、浮点数、字符串等
    if isinstance(node, ast.Constant):
        return node.value

    # 二元运算：left OP right
    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, operators, unary_operators,
                          functions, binary_functions, constants)
        right = _eval_node(node.right, operators, unary_operators,
                           functions, binary_functions, constants)
        op_type = type(node.op)
        if op_type in operators:
            return operators[op_type](left, right)
        raise ValueError(f"不支持的运算符: {type(node.op).__name__}")

    # 一元运算：OP x（如 -x、+x、~x）
    if isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand, operators, unary_operators,
                             functions, binary_functions, constants)
        op_type = type(node.op)
        if op_type in unary_operators:
            return unary_operators[op_type](operand)
        raise ValueError(f"不支持的一元运算符: {type(node.op).__name__}")

    # 函数调用：func(args)
    if isinstance(node, ast.Call):
        # 处理 func(args) 形式
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            args = [_eval_node(arg, operators, unary_operators,
                               functions, binary_functions, constants)
                    for arg in node.args]
            # 优先查找二元函数（支持多参数）
            if func_name in binary_functions:
                return binary_functions[func_name](*args)
            # 再查找一元函数
            if func_name in functions:
                if len(args) != 1:
                    raise ValueError(
                        f"函数 {func_name} 需要1个参数，但提供了 {len(args)} 个"
                    )
                return functions[func_name](args[0])
            raise ValueError(f"不支持的函数: {func_name}")
        # 处理 obj.method(args) 形式（暂不支持）
        raise ValueError("不支持的方法调用")

    # 变量名/常量：pi、e 等
    if isinstance(node, ast.Name):
        if node.id in constants:
            return constants[node.id]
        raise ValueError(f"未识别的变量或常量: {node.id}")

    # 比较运算（支持连续比较如 1 < x < 10）
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, operators, unary_operators,
                          functions, binary_functions, constants)
        result = True
        current = left
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval_node(comparator, operators, unary_operators,
                               functions, binary_functions, constants)
            op_map = {
                ast.Eq:    operator.eq,
                ast.NotEq: operator.ne,
                ast.Lt:    operator.lt,
                ast.LtE:   operator.le,
                ast.Gt:    operator.gt,
                ast.GtE:   operator.ge,
                ast.Is:    operator.is_,
                ast.IsNot: operator.is_not,
                ast.In:    lambda a, b: a in b,
                ast.NotIn: lambda a, b: a not in b,
            }
            if type(op) not in op_map:
                raise ValueError(f"不支持的比较运算符: {type(op).__name__}")
            if not op_map[type(op)](current, right):
                result = False
                break
            current = right
        return result

    # 布尔运算：and、or
    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            for value in node.values:
                if not _eval_node(value, operators, unary_operators,
                                  functions, binary_functions, constants):
                    return False
            return True
        elif isinstance(node.op, ast.Or):
            for value in node.values:
                if _eval_node(value, operators, unary_operators,
                              functions, binary_functions, constants):
                    return True
            return False

    # 条件表达式：x if cond else y
    if isinstance(node, ast.IfExp):
        cond = _eval_node(node.test, operators, unary_operators,
                          functions, binary_functions, constants)
        if cond:
            return _eval_node(node.body, operators, unary_operators,
                              functions, binary_functions, constants)
        else:
            return _eval_node(node.orelse, operators, unary_operators,
                              functions, binary_functions, constants)

    raise ValueError(f"不支持的表达式类型: {type(node).__name__}")


def _format_result(value) -> str:
    """格式化计算结果"""
    if isinstance(value, float):
        # 处理特殊浮点值
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "∞" if value > 0 else "-∞"
        # 如果接近整数，显示为整数
        if abs(value - round(value)) < 1e-12:
            return str(round(value))
        return f"{value:.10g}"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, complex):
        return str(value)
    return str(value)


def create_calculator_registry():
    """创建包含计算器的工具注册表"""
    registry = ToolRegistry()

    # 注册计算器函数
    registry.register_function(
        name="my_calculator",
        description=(
            "增强型数学计算工具\n"
            "【运算符】+ - * / // % ** << >> & | ^ ~\n"
            "【比较运算】== != < <= > >=\n"
            "【逻辑运算】and or not\n"
            "【一元函数】sqrt abs exp log log10 log2 "
            "sin cos tan asin acos atan "
            "sinh cosh tanh radians degrees ceil floor trunc factorial\n"
            "【二元函数】pow gcd lcm atan2 hypot log(x,base) comb perm copysign\n"
            "【常量】pi e tau inf nan\n"
            "【条件】x if cond else y\n"
            "示例: sqrt(16) + sin(pi/2) * 2^3, gcd(48,18), 5 > 3 and 2 < 1"
        ),
        func=my_calculate
    )

    return registry
